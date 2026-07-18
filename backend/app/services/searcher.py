"""
搜索协调器
负责协调多个搜索源，并发搜索，聚合结果
"""
import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any

import yaml

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.sources import SearchResult, CLOUD_DOMAIN_MAP
from app.sources.baidu import BaiduSearchSource
from app.sources.bing import BingSearchSource
from app.sources.sogou import SogouSearchSource
from app.sources.so360 import So360SearchSource
from app.sources.pansou import PanSouSearchSource
from app.sources.api_source import APISearchSource
from app.models.cache import SearchCache
from app.models.history import SearchHistory
from app.services.aggregator import ResultAggregator
from app.services.link_validator import link_validator

logger = logging.getLogger(__name__)
CACHE_VERSION = "v6-strict-verified"


class SearchOrchestrator:
    """搜索协调器：管理搜索源、执行搜索、缓存管理"""

    def __init__(self):
        self._sources: List[Any] = []
        self._init_default_sources()

    def _init_default_sources(self):
        """从 YAML 初始化搜索源，配置不可用时回退到内置源。"""
        factories = {
            "百度搜索": BaiduSearchSource,
            "必应搜索": BingSearchSource,
            "搜狗搜索": SogouSearchSource,
            "360搜索": So360SearchSource,
            "baidu": BaiduSearchSource,
            "bing": BingSearchSource,
            "sogou": SogouSearchSource,
            "360": So360SearchSource,
        }

        specs = self._load_source_specs()
        for spec in specs:
            name = str(spec.get("name", "")).strip()
            source_type = str(spec.get("type", "search_engine")).lower()
            enabled = bool(spec.get("enabled", True))

            if source_type == "pansou":
                endpoint = str(
                    spec.get("endpoint", "https://so.252035.xyz/api/search")
                ).strip()
                source = PanSouSearchSource(
                    endpoint=endpoint,
                    timeout=int(spec.get("timeout", min(settings.SEARCH_TIMEOUT, 8))),
                )
                source.enabled = enabled
                self._sources.append(source)
                continue

            if source_type == "api":
                endpoint = str(spec.get("endpoint", "")).strip()
                if not name or not endpoint:
                    logger.warning("忽略缺少 name/endpoint 的 API 搜索源配置")
                    continue
                source = APISearchSource(
                    name=name,
                    endpoint=endpoint,
                    method=spec.get("method", "GET"),
                    timeout=settings.SEARCH_TIMEOUT,
                    headers=spec.get("headers"),
                    params_template=spec.get("params_template"),
                    response_path=spec.get("response_path", "data.items"),
                    field_map=spec.get("field_map"),
                )
                source.enabled = enabled
                self._sources.append(source)
                continue

            factory = factories.get(name) or factories.get(name.lower())
            if not factory:
                logger.warning("忽略未知搜索源: %s", name)
                continue
            source = factory(timeout=settings.SEARCH_TIMEOUT)
            source.enabled = enabled
            self._sources.append(source)

        if not self._sources:
            logger.warning("搜索源配置为空，回退到内置 Bing/搜狗源")
            self._sources.extend([
                BingSearchSource(timeout=settings.SEARCH_TIMEOUT),
                SogouSearchSource(timeout=settings.SEARCH_TIMEOUT),
            ])

    def _load_source_specs(self) -> List[dict]:
        """读取 sources.yaml，格式错误时返回空列表。"""
        path = Path(settings.SOURCES_CONFIG)
        if not path.exists():
            logger.warning("搜索源配置文件不存在: %s", path)
            return []
        try:
            with path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            specs = data.get("sources", [])
            return specs if isinstance(specs, list) else []
        except Exception as e:
            logger.warning("读取搜索源配置失败，将使用内置源: %s", e)
            return []

    def get_sources(self) -> List[dict]:
        """获取所有搜索源列表"""
        return [s.to_dict() if hasattr(s, 'to_dict') else {
            "name": s.name,
            "type": s.source_type,
            "enabled": s.enabled,
        } for s in self._sources]

    def _get_enabled_sources(self) -> list:
        """获取所有已启用的搜索源"""
        return [s for s in self._sources if s.enabled]

    async def search(
        self,
        db: AsyncSession,
        keyword: str,
        cloud_types: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "relevance",
        skip_cache: bool = False,
    ) -> dict:
        """执行搜索

        Args:
            db: 数据库会话
            keyword: 搜索关键字
            cloud_types: 网盘类型列表
            page: 页码
            page_size: 每页数量
            sort_by: 排序方式
            skip_cache: 是否跳过缓存
        """
        keyword = keyword.strip()
        if not keyword:
            return {"items": [], "total": 0, "page": 1, "page_size": page_size, "total_pages": 0}

        # 解析和相关性规则升级后，旧缓存可能包含污染标题，使用版本前缀自动隔离。
        types_key = f"{CACHE_VERSION}:" + (",".join(sorted(cloud_types)) if cloud_types else "")

        # 检查缓存
        if not skip_cache:
            cached = await self._get_from_cache(db, keyword, types_key)
            if cached is not None:
                logger.info(f"缓存命中: '{keyword}'")
                # 从缓存恢复SearchResult对象
                items = [SearchResult(**item) for item in cached]
                items = ResultAggregator.filter_by_keyword(items, keyword)
                # 搜索结果可缓存，但链接有效性不能永久缓存。两分钟检测缓存
                # 到期后会重新向网盘确认，已失效链接会在缓存命中时被剔除。
                items = await link_validator.validate_many(items)
                if items:
                    sorted_items = ResultAggregator.sort(items, sort_by, keyword)
                    # 缓存命中也代表用户完成了一次搜索，应更新历史统计。
                    await self._save_history(db, keyword)
                    paginated = ResultAggregator.paginate(sorted_items, page, page_size)
                    return {
                        **paginated,
                        "from_cache": True,
                        "search_time_ms": 0,
                    }
                logger.info("缓存中的链接已全部失效，重新执行实时搜索: '%s'", keyword)

        # 并发请求所有搜索源
        enabled_sources = self._get_enabled_sources()
        if not enabled_sources:
            return {"items": [], "total": 0, "page": 1, "page_size": page_size, "total_pages": 0}

        tasks = []
        for source in enabled_sources:
            tasks.append(source.search(keyword, cloud_types))

        start_time = time.time()
        source_results = await asyncio.gather(*tasks, return_exceptions=True)
        # 收集所有结果
        all_results: List[SearchResult] = []
        for i, result in enumerate(source_results):
            if isinstance(result, Exception):
                logger.warning(f"搜索源 '{enabled_sources[i].name}' 异常: {result}")
                continue
            if isinstance(result, list):
                all_results.extend(result)

        # 去重和排序
        deduped = ResultAggregator.deduplicate(all_results)
        deduped = ResultAggregator.filter_by_keyword(deduped, keyword)
        # 严格模式只展示存在稳定公开检测接口的网盘。单纯页面能打开并不能
        # 证明分享文件仍存在，因此不把 unsupported 结果冒充为“有效”。
        deduped = [
            item
            for item in deduped
            if link_validator.supports_strict_check(item.cloud_type)
        ]
        deduped = ResultAggregator.sort(deduped, "relevance", keyword)
        deduped = ResultAggregator.limit_diverse(
            deduped, settings.MAX_LINKS_TO_VALIDATE
        )
        before_validation = len(deduped)
        deduped = await link_validator.validate_many(deduped)
        elapsed = time.time() - start_time
        logger.info(
            "搜索完成: '%s', %d个源, %d/%d条通过有效性检测, 耗时%.2fs",
            keyword,
            len(enabled_sources),
            len(deduped),
            before_validation,
            elapsed,
        )

        # 上游聚合节点或搜索引擎偶发超时时，不用空结果覆盖此前的有效缓存。
        # 旧缓存会重新经过网盘检测，只有当前仍有效的链接才会返回。
        if not deduped:
            stale = await self._get_latest_nonempty_cache(db, keyword, types_key)
            if stale:
                stale_items = [SearchResult(**item) for item in stale]
                stale_items = ResultAggregator.filter_by_keyword(stale_items, keyword)
                stale_items = await link_validator.validate_many(stale_items)
                if stale_items:
                    await self._save_history(db, keyword)
                    stale_items = ResultAggregator.sort(stale_items, sort_by, keyword)
                    paginated = ResultAggregator.paginate(
                        stale_items, page, page_size
                    )
                    return {
                        **paginated,
                        "from_cache": True,
                        "stale_fallback": True,
                        "search_time_ms": round(elapsed * 1000),
                    }

        # 缓存未排序结果，命中缓存后可以按当前 sort 参数重新排序。
        cache_items = [
            {
                "title": r.title,
                "cloud_type": r.cloud_type,
                "cloud_name": r.cloud_name,
                "share_url": r.share_url,
                "share_code": r.share_code,
                "description": r.description,
                "file_size": r.file_size,
                "source_name": r.source_name,
                "validation_status": r.validation_status,
                "validation_message": r.validation_message,
                "verified_title": r.verified_title,
            }
            for r in deduped
        ]
        if cache_items:
            await self._save_to_cache(db, keyword, types_key, cache_items)

        # 记录搜索历史
        await self._save_history(db, keyword)

        sorted_results = ResultAggregator.sort(deduped, sort_by, keyword)

        # 分页
        paginated = ResultAggregator.paginate(sorted_results, page, page_size)

        return {
            **paginated,
            "from_cache": False,
            "search_time_ms": round(elapsed * 1000),
        }

    async def _get_from_cache(
        self, db: AsyncSession, keyword: str, cloud_types: str
    ) -> Optional[List[dict]]:
        """从缓存获取搜索结果"""
        # 使用 utcnow 以匹配数据库中的 UTC 时间
        expire_time = datetime.utcnow() - timedelta(seconds=settings.CACHE_TTL)

        stmt = (
            select(SearchCache)
            .where(
                SearchCache.keyword == keyword,
                SearchCache.cloud_types == cloud_types,
                SearchCache.created_at > expire_time,
            )
            .order_by(SearchCache.created_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        cache = result.scalar_one_or_none()

        if cache:
            try:
                return json.loads(cache.results_json)
            except json.JSONDecodeError:
                return None
        return None

    async def _save_to_cache(
        self, db: AsyncSession, keyword: str, cloud_types: str, results: List[dict]
    ):
        """保存搜索结果到缓存"""
        # 保留历史有效快照：当外部搜索节点临时不可用时，可重新检测旧快照
        # 后降级返回。空结果不会调用本方法，因此不会覆盖有效数据。
        cache = SearchCache(
            keyword=keyword,
            cloud_types=cloud_types,
            results_json=json.dumps(results, ensure_ascii=False),
        )
        db.add(cache)
        await db.commit()

    async def _get_latest_nonempty_cache(
        self, db: AsyncSession, keyword: str, cloud_types: str
    ) -> Optional[List[dict]]:
        stmt = (
            select(SearchCache)
            .where(
                SearchCache.keyword == keyword,
                SearchCache.cloud_types == cloud_types,
            )
            .order_by(SearchCache.created_at.desc())
            .limit(10)
        )
        result = await db.execute(stmt)
        for cache in result.scalars():
            try:
                items = json.loads(cache.results_json)
            except json.JSONDecodeError:
                continue
            if isinstance(items, list) and items:
                return items
        return None

    async def _save_history(self, db: AsyncSession, keyword: str):
        """保存搜索历史"""
        history = SearchHistory(keyword=keyword)
        db.add(history)
        await db.commit()

    async def get_hot_keywords(self, db: AsyncSession, limit: int = 10) -> List[dict]:
        """获取热门搜索关键字（近7天搜索频率统计）"""
        from sqlalchemy import func as sql_func

        seven_days_ago = datetime.now() - timedelta(days=7)

        stmt = (
            select(
                SearchHistory.keyword,
                sql_func.count(SearchHistory.id).label("count"),
            )
            .where(SearchHistory.created_at > seven_days_ago)
            .group_by(SearchHistory.keyword)
            .order_by(sql_func.count(SearchHistory.id).desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        rows = result.all()

        return [{"keyword": row.keyword, "count": row.count} for row in rows]

    async def get_history(self, db: AsyncSession, limit: int = 20) -> List[dict]:
        """获取搜索历史"""
        from sqlalchemy import func as sql_func

        stmt = (
            select(
                SearchHistory.keyword,
                sql_func.max(SearchHistory.created_at).label("last_searched_at"),
            )
            .group_by(SearchHistory.keyword)
            .order_by(sql_func.max(SearchHistory.created_at).desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return [{"keyword": row.keyword} for row in result.all()]

    async def clear_history(self, db: AsyncSession):
        """清空搜索历史"""
        await db.execute(delete(SearchHistory))
        await db.commit()


# 全局搜索协调器实例
orchestrator = SearchOrchestrator()
