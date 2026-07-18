"""PanSou 聚合搜索源。

PanSou 使用 Telegram 频道与站点插件作为索引，每个链接都携带独立的
``note``（作品标题），比从普通搜索引擎摘要中猜测“标题-链接”关系可靠。
"""
import logging
import asyncio
from typing import List, Optional
from urllib.parse import urlparse

import httpx

from app.sources import SearchResult, CLOUD_DOMAIN_MAP, CLOUD_TYPE_MAP

logger = logging.getLogger(__name__)


class PanSouSearchSource:
    name = "PanSou聚合"
    source_type = "pansou"
    enabled = True

    def __init__(
        self,
        endpoint: str = "https://so.252035.xyz/api/search",
        timeout: int = 15,
    ):
        self.endpoint = endpoint
        self.timeout = timeout

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.source_type,
            "enabled": self.enabled,
        }

    async def search(
        self, keyword: str, cloud_types: Optional[List[str]] = None
    ) -> List[SearchResult]:
        params: dict = {"kw": keyword, "res": "merge"}
        if cloud_types:
            # PanSou 将移动云盘称为 mobile，本项目内部使用 yidong。
            # POST 接口要求 JSON 数组；此前传逗号字符串会导致接口返回空结果。
            params["cloud_types"] = [
                "mobile" if item == "yidong" else item for item in cloud_types
            ]

        headers = {
            "Accept": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36"
            ),
        }
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                trust_env=False,
            ) as client:
                # 官方接口同时支持 GET/POST。POST 在公共节点上不会经历较慢的
                # 查询串缓存链路，实测响应明显更快、更稳定。
                payload = await self._request_payload(client, params, headers, attempts=2)
                if payload is None and cloud_types:
                    # 公共节点偶尔对带 cloud_types 的请求返回 400/502。
                    # 回退为全量请求后在本地过滤，确保指定网盘不会被上游偶发
                    # 错误直接变成空结果。
                    fallback_params = {"kw": keyword, "res": "merge"}
                    payload = await self._request_payload(
                        client, fallback_params, headers, attempts=1
                    )
        except Exception as exc:
            logger.warning("PanSou聚合搜索失败: %s", exc)
            return []

        if payload is None:
            return []

        return self._parse_payload(payload, cloud_types)

    async def _request_payload(
        self,
        client: httpx.AsyncClient,
        params: dict,
        headers: dict,
        attempts: int = 1,
    ) -> Optional[dict]:
        last_error: Optional[Exception] = None
        for attempt in range(attempts):
            try:
                response = await client.post(self.endpoint, json=params, headers=headers)
                response.raise_for_status()
                payload = response.json()
                return payload if isinstance(payload, dict) else None
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt + 1 < attempts:
                    await asyncio.sleep(0.25)
        if last_error:
            logger.warning("PanSou请求失败（%s）: %s", params.get("cloud_types", "全部"), last_error)
        return None

    def _parse_payload(
        self, payload: object, cloud_types: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """把 PanSou 的 merged_by_type 响应映射为项目统一结果。"""
        data = payload.get("data", payload) if isinstance(payload, dict) else {}
        merged = data.get("merged_by_type", {}) if isinstance(data, dict) else {}
        if not isinstance(merged, dict):
            return []

        results: List[SearchResult] = []
        seen: set[str] = set()
        for raw_type, links in merged.items():
            cloud_type = "yidong" if raw_type == "mobile" else str(raw_type)
            if cloud_type not in CLOUD_TYPE_MAP or not isinstance(links, list):
                continue
            if cloud_types and cloud_type not in cloud_types:
                continue

            for item in links:
                if not isinstance(item, dict):
                    continue
                url = str(item.get("url", "")).strip()
                title = str(item.get("note", "")).strip()
                password = str(item.get("password", "")).strip()
                origin = str(item.get("source", "")).strip()
                if not url or not title or url in seen:
                    continue
                if not self._url_matches_type(url, cloud_type):
                    continue
                seen.add(url)
                results.append(
                    SearchResult(
                        title=title[:160],
                        cloud_type=cloud_type,
                        cloud_name=CLOUD_TYPE_MAP[cloud_type],
                        share_url=url,
                        share_code=password,
                        description="来自结构化资源索引，返回前已进行网盘有效性检测",
                        source_name=f"{self.name}·{origin}" if origin else self.name,
                    )
                )
        return results

    def _url_matches_type(self, url: str, cloud_type: str) -> bool:
        try:
            hostname = (urlparse(url).hostname or "").lower()
        except ValueError:
            return False
        return any(
            hostname == domain or hostname.endswith(f".{domain}")
            for domain in CLOUD_DOMAIN_MAP.get(cloud_type, [])
        )
