"""360 搜索备用源。

360 的搜索结果页结构相对简单，作为搜狗/Bing 被临时反爬时的补充来源。
"""
import logging
import re
from html import unescape
from typing import List, Optional

import httpx
from bs4 import BeautifulSoup

from app.sources import SearchResult, CLOUD_DOMAIN_MAP, CLOUD_TYPE_MAP

logger = logging.getLogger(__name__)


class So360SearchSource:
    name = "360搜索"
    source_type = "search_engine"
    enabled = True
    BASE_URL = "https://www.so.com/s"

    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    def _domains(self, cloud_types: Optional[List[str]]) -> List[str]:
        if cloud_types:
            return [CLOUD_DOMAIN_MAP[ct][0] for ct in cloud_types if ct in CLOUD_DOMAIN_MAP]
        return [domains[0] for domains in CLOUD_DOMAIN_MAP.values()]

    async def search(
        self, keyword: str, cloud_types: Optional[List[str]] = None
    ) -> List[SearchResult]:
        results: List[SearchResult] = []
        seen: set[str] = set()
        domains = self._domains(cloud_types)
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                trust_env=False,
            ) as client:
                response = await client.get(
                    self.BASE_URL,
                    params={"q": f"site:{domains[0]}/s/ {keyword}" if domains else keyword},
                    headers=headers,
                )
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "lxml")

                # 只解析真实自然搜索结果卡片。旧实现遍历全页 a 标签，会把导航、
                # 推荐词和脚本里的链接套到同一个标题上，造成严重的张冠李戴。
                cards = soup.select("li.res-list, li.result-item, .res-item")
                for card in cards:
                    title_elem = card.select_one("h3 a, h2 a")
                    title = self._clean_title(
                        title_elem.get_text(" ", strip=True) if title_elem else ""
                    )
                    full_text = card.get_text(" ", strip=True)
                    searchable = unescape(f"{card} {full_text}")
                    pairs = self._extract_urls(searchable, domains)
                    # 一个结果卡片出现多个不同链接时，无法证明标题属于哪一个链接，
                    # 严格模式直接丢弃，宁缺毋滥。
                    unique_pairs = list(dict.fromkeys(pairs))
                    if len(unique_pairs) != 1 or not title:
                        continue
                    url, domain = unique_pairs[0]
                    if url in seen:
                        continue
                    seen.add(url)
                    cloud_type = self._identify_cloud_type(domain)
                    if cloud_type:
                        results.append(
                            SearchResult(
                                title=title,
                                cloud_type=cloud_type,
                                cloud_name=CLOUD_TYPE_MAP.get(cloud_type, ""),
                                share_url=url,
                                description=self._clean_description(full_text, url, title),
                                source_name=self.name,
                            )
                        )
        except Exception as e:
            logger.debug("360搜索异常: %s", e)

        return results

    def _extract_urls(self, text: str, domains: List[str]) -> List[tuple[str, str]]:
        found = []
        for domain in domains:
            pattern = rf"https?://(?:www\.)?{re.escape(domain)}/s/[a-zA-Z0-9_-]+(?:\?pwd=[a-zA-Z0-9]+)?"
            for match in re.finditer(pattern, text, re.IGNORECASE):
                found.append((match.group(), domain))
        return found

    def _clean_title(self, title: str) -> str:
        if not title or title.startswith("http"):
            return ""
        title = re.sub(r"\s+", " ", title).strip()
        return title[:100]

    def _clean_description(self, text: str, url: str, title: str) -> str:
        cleaned = text.replace(url, "").replace(title, "")
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned[:200] + "..." if len(cleaned) > 200 else cleaned

    def _identify_cloud_type(self, domain: str) -> Optional[str]:
        for cloud_type, domains in CLOUD_DOMAIN_MAP.items():
            if domain in domains:
                return cloud_type
        return None
