"""
百度搜索引擎聚合源
通过搜索 URL 模式来发现网盘分享链接
注意：百度现在有严格的反爬 CAPTCHA 验证，本源已默认禁用
"""
import re
import logging
from typing import List, Optional
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup

from app.sources import SearchSource, SearchResult, CLOUD_DOMAIN_MAP, CLOUD_TYPE_MAP

logger = logging.getLogger(__name__)


class BaiduSearchSource(SearchSource):
    """百度搜索引擎（已禁用：反爬 CAPTCHA 验证）"""

    name = "百度搜索"
    source_type = "search_engine"
    enabled = False  # 百度搜索已完全被 CAPTCHA 拦截，默认禁用

    BASE_URL = "https://www.baidu.com/s"
    MOBILE_URL = "https://m.baidu.com/s"

    CODE_PATTERN = re.compile(r'提取码[：:]\s*([a-zA-Z0-9]{4,6})')
    PWD_PATTERN = re.compile(r'[?&]pwd=([a-zA-Z0-9]{4,6})')

    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    async def search(
        self, keyword: str, cloud_types: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """
        通过百度搜索网盘资源
        注意：百度现在有严格的 CAPTCHA 验证，大部分请求会被拦截
        此方法保留但已默认禁用，返回空列表
        """
        if not self.enabled:
            return []

        results = []
        seen_urls = set()

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

        # 构建 URL 模式搜索查询
        domains = self._get_domains(cloud_types)
        queries = []
        for domain in domains[:3]:  # 限制查询数量
            queries.append(f"{domain}/s/ {keyword}")

        for query in queries:
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    follow_redirects=True,
                    trust_env=False,
                ) as client:
                    response = await client.get(
                        self.BASE_URL,
                        params={"wd": query, "rn": "20"},
                        headers=headers,
                    )

                    # 检查是否被 CAPTCHA 拦截
                    if "captcha" in str(response.url).lower() or len(response.text) < 2000:
                        logger.debug(f"百度搜索被 CAPTCHA 拦截 (query: {query})")
                        continue

                    soup = BeautifulSoup(response.text, "lxml")

                    for item in soup.select(".result, .c-container"):
                        try:
                            full_text = item.get_text()
                            url_infos = self._extract_urls(full_text, domains)
                            for info in url_infos:
                                url = info["url"]
                                if url in seen_urls:
                                    continue
                                seen_urls.add(url)
                                result = self._build_result(
                                    url=url, full_text=full_text
                                )
                                if result:
                                    results.append(result)
                        except Exception as e:
                            logger.debug(f"解析百度搜索结果项失败: {e}")
                            continue

            except httpx.TimeoutException:
                logger.debug(f"百度搜索超时 (query: {query})")
                continue
            except Exception as e:
                logger.debug(f"百度搜索异常: {e}")
                continue

        return results

    def _get_domains(self, cloud_types: Optional[List[str]] = None) -> List[str]:
        """获取要搜索的云盘域名"""
        domains = []
        if cloud_types:
            for ct in cloud_types:
                if ct in CLOUD_DOMAIN_MAP:
                    domains.extend(CLOUD_DOMAIN_MAP[ct])
        else:
            for ct_domains in CLOUD_DOMAIN_MAP.values():
                domains.extend(ct_domains)
        return domains

    def _extract_urls(self, text: str, domains: List[str]) -> List[dict]:
        """从文本中提取云盘分享链接"""
        found = []
        for domain in domains:
            domain_escaped = re.escape(domain)
            patterns = [
                rf'https?://{domain_escaped}/s/[a-zA-Z0-9]+',
                rf'https?:{domain_escaped}/s/[a-zA-Z0-9]+',
            ]
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    url = match.group()
                    if url.startswith("https:") and "//" not in url[6:8]:
                        url = url.replace("https:", "https://", 1)
                    found.append({"url": url, "domain": domain})
        return found

    def _build_result(self, url: str, full_text: str) -> Optional[SearchResult]:
        """构建搜索结果"""
        cloud_type = self._identify_cloud_type(url)
        if not cloud_type:
            return None

        title = self._extract_title(full_text, url)
        share_code = self._extract_code(full_text, url)
        file_size = self._extract_file_size(full_text)
        description = self._extract_description(full_text, url, title)

        return SearchResult(
            title=title or url,
            cloud_type=cloud_type,
            cloud_name=CLOUD_TYPE_MAP.get(cloud_type, ""),
            share_url=url,
            share_code=share_code,
            description=description,
            file_size=file_size,
            source_name=self.name,
        )

    def _extract_title(self, text: str, url: str) -> str:
        url_escaped = re.escape(url)
        match = re.search(r'([^。，！？\n]{4,60})' + url_escaped[:30], text)
        if match:
            title = match.group(1).strip()
            if len(title) > 4:
                return title
        cleaned = re.sub(r'\s+', ' ', text).strip()
        return cleaned[:80] + "..." if len(cleaned) > 80 else cleaned[:80]

    def _extract_code(self, text: str, url: str) -> str:
        pwd_match = self.PWD_PATTERN.search(url)
        if pwd_match:
            return pwd_match.group(1)
        code_match = self.CODE_PATTERN.search(text)
        return code_match.group(1) if code_match else ""

    def _extract_file_size(self, text: str) -> str:
        size_match = re.search(r'(\d+(?:\.\d+)?\s*(?:GB|MB|TB|KB))', text, re.IGNORECASE)
        return size_match.group(1).upper() if size_match else ""

    def _extract_description(self, text: str, url: str, title: str) -> str:
        cleaned = text.replace(url, "").replace(title, "")
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned[:200] + "..." if len(cleaned) > 200 else cleaned

    def _identify_cloud_type(self, url: str) -> Optional[str]:
        url_lower = url.lower()
        for ct, domains in CLOUD_DOMAIN_MAP.items():
            for domain in domains:
                if domain in url_lower:
                    return ct
        return None
