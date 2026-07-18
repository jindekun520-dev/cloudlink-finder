"""
搜索结果聚合去重和排序服务
"""
import hashlib
import logging
import re
from typing import List, Dict, Optional

from app.sources import SearchResult

logger = logging.getLogger(__name__)


class ResultAggregator:
    """结果聚合器：去重、排序、分页"""

    @staticmethod
    def _keyword_matches(text: str, keyword: str) -> bool:
        normalized_text = "".join(text.casefold().split())
        normalized_keyword = "".join(keyword.casefold().split())
        if not normalized_keyword:
            return True
        if normalized_keyword in normalized_text:
            return True
        # 中文搜索词常被摘要插入描述词，例如“电影分享”→“电影资源分享”。
        # 字符必须保持原顺序，避免只因几个字零散出现在长摘要里就误判相关。
        if all("\u4e00" <= char <= "\u9fff" for char in normalized_keyword):
            pattern = ".*".join(re.escape(char) for char in normalized_keyword)
            return re.search(pattern, normalized_text) is not None
        return False

    @staticmethod
    def filter_by_keyword(results: List[SearchResult], keyword: str) -> List[SearchResult]:
        """优先保留标题或描述命中关键词的结果，降低搜索引擎噪声。"""
        normalized_keyword = "".join(keyword.casefold().split())
        if not normalized_keyword:
            return results

        quality_results = []
        spam_markers = ("网赚", "拉新", "单日收益", "一单", "兼职赚钱", "www.")
        for result in results:
            title = result.title.strip()
            compact_title = "".join(title.casefold().split())
            empty_brackets = re.search(r'[《「【]\s*[：:、\-]*[》」】]', title)
            meaningful = re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]', '', title)
            if empty_brackets or title.lower().startswith(('http://', 'https://')):
                continue
            if re.match(r'^来自.+搜索的【?.+】?资源$', title):
                continue
            if any(marker in title.casefold() for marker in spam_markers):
                continue
            if len(meaningful) < 4:
                continue
            quality_results.append(result)

        title_matches = [
            result
            for result in quality_results
            if ResultAggregator._keyword_matches(result.title, keyword)
        ]
        if title_matches:
            return title_matches

        description_matches = [
            result
            for result in quality_results
            if ResultAggregator._keyword_matches(result.description, keyword)
        ]

        # 无关结果比空结果更误导：没有命中时明确返回空列表。
        return description_matches

    @staticmethod
    def limit_diverse(results: List[SearchResult], limit: int) -> List[SearchResult]:
        """按网盘类型轮询截取候选，避免校验名额被单一网盘占满。"""
        if limit <= 0 or len(results) <= limit:
            return results
        buckets: Dict[str, List[SearchResult]] = {}
        for result in results:
            buckets.setdefault(result.cloud_type, []).append(result)
        selected: List[SearchResult] = []
        index = 0
        while len(selected) < limit:
            added = False
            for bucket in buckets.values():
                if index < len(bucket):
                    selected.append(bucket[index])
                    added = True
                    if len(selected) >= limit:
                        break
            if not added:
                break
            index += 1
        return selected

    @staticmethod
    def deduplicate(results: List[SearchResult]) -> List[SearchResult]:
        """按URL去重，保留首次出现的结果"""
        seen: Dict[str, SearchResult] = {}
        for r in results:
            key = r.unique_key
            if key not in seen:
                seen[key] = r
            else:
                # 如果新结果有提取码而旧结果没有，则合并
                existing = seen[key]
                if r.share_code and not existing.share_code:
                    existing.share_code = r.share_code
                if r.description and not existing.description:
                    existing.description = r.description
                if r.file_size and not existing.file_size:
                    existing.file_size = r.file_size

        return list(seen.values())

    @staticmethod
    def sort(
        results: List[SearchResult],
        sort_by: str = "relevance",
        keyword: str = "",
    ) -> List[SearchResult]:
        """对结果排序

        Args:
            results: 结果列表
            sort_by: 排序方式 'relevance'（综合） 或 'recent'（最新）
        """
        if sort_by == "recent":
            return results  # 搜索引擎结果本身已按时间排序

        # 综合排序：优先有提取码的、有描述的结果
        normalized_keyword = "".join(keyword.casefold().split())

        def score(r: SearchResult) -> float:
            s = 0.0
            searchable = "".join(
                f"{r.title} {r.description}".casefold().split()
            )
            if normalized_keyword:
                # 关键词命中比“字段是否为空”更重要，避免无关页面挤到前面。
                if ResultAggregator._keyword_matches(r.title, keyword):
                    s += 5.0
                elif ResultAggregator._keyword_matches(r.description, keyword):
                    s += 2.5
            if r.share_code:
                s += 2.0
            if r.description:
                s += 1.0
            if r.file_size:
                s += 0.5
            if r.validation_status == "valid":
                s += 4.0
            if r.verified_title:
                s += 1.0
            return s

        return sorted(results, key=score, reverse=True)

    @staticmethod
    def paginate(
        results: List[SearchResult],
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """分页

        Returns:
            {"items": [...], "total": int, "page": int, "page_size": int, "total_pages": int}
        """
        total = len(results)
        total_pages = (total + page_size - 1) // page_size if total else 0
        start = (page - 1) * page_size
        end = start + page_size
        items = results[start:end]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }
