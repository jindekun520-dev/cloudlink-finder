"""
必应搜索引擎聚合源
通过搜索 URL 模式（如 pan.baidu.com/s/）来发现网盘分享链接
"""
import asyncio
import re
import logging
from typing import List, Optional
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup

from app.sources import SearchResult, CLOUD_TYPE_MAP, CLOUD_DOMAIN_MAP

logger = logging.getLogger(__name__)


class BingSearchSource:
    """必应搜索引擎（国内版 cn.bing.com）"""

    name = "必应搜索"
    source_type = "search_engine"
    enabled = True

    BASE_URL = "https://cn.bing.com/search"

    # 提取码正则
    CODE_PATTERN = re.compile(r'提取码[：:]\s*([a-zA-Z0-9]{4,6})')
    PWD_PATTERN = re.compile(r'[?&]pwd=([a-zA-Z0-9]{4,6})')

    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    def _get_cloud_patterns(self, cloud_types: Optional[List[str]] = None) -> List[str]:
        """获取要搜索的云盘域名模式列表"""
        domains = []
        if cloud_types:
            for ct in cloud_types:
                if ct in CLOUD_DOMAIN_MAP:
                    domains.append(CLOUD_DOMAIN_MAP[ct][0])
        else:
            for ct_domains in CLOUD_DOMAIN_MAP.values():
                domains.append(ct_domains[0])
        return domains

    async def search(
        self, keyword: str, cloud_types: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """通过必应搜索网盘资源

        使用 URL 模式搜索策略：搜索包含云盘分享链接模式（如 pan.baidu.com/s/）的页面，
        然后从搜索结果文本中提取实际的分享链接。
        """
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

        # 当指定网盘类型时，只搜索对应域名
        # 当未指定时，搜索所有主流云盘
        queries = self._build_queries(keyword, cloud_types)
        all_results = []
        seen_urls = set()

        # 同一个客户端复用连接，避免每个网盘查询都重新建立 TLS 连接。
        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            trust_env=False,
        ) as client:
            tasks = [
                self._execute_query(
                    client, query, self._get_domain_from_query(query), headers, seen_urls
                )
                for query in queries
            ]
            batches = await asyncio.gather(*tasks, return_exceptions=True)
            for query, result_batch in zip(queries, batches):
                if isinstance(result_batch, Exception):
                    logger.debug(f"Bing搜索子查询异常 ({query}): {result_batch}")
                    continue
                all_results.extend(result_batch)

        return all_results

    def _get_domain_from_query(self, query: str) -> str:
        """从搜索查询字符串中提取域名"""
        # 查询格式: "pan.quark.cn/s/ keyword"
        parts = query.split("/")[0]
        if parts.startswith("http"):
            parts = parts.split("//")[-1]
        return parts

    async def _execute_query(
        self, client: httpx.AsyncClient, query: str, domain: str, headers: dict, seen_urls: set
    ) -> List[SearchResult]:
        """执行单个搜索查询并提取结果"""
        results = []

        response = await client.get(
            self.BASE_URL,
            params={"q": query, "count": "20"},
            headers=headers,
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        for item in soup.select("li.b_algo"):
            try:
                # 有些搜索引擎把实际分享链接放在 href 中而不是可见文本中。
                full_text = item.get_text(" ", strip=True)
                searchable = f"{str(item)} {full_text}"
                url_infos = self._extract_cloud_urls(
                    searchable, [domain], ""
                )
                unique_infos = {info["url"]: info for info in url_infos}
                # 同一卡片出现多个链接时无法可靠判断标题归属，宁可不返回。
                if len(unique_infos) != 1:
                    continue
                title_elem = item.select_one("h2 a")
                title = title_elem.get_text(" ", strip=True) if title_elem else ""
                if not title:
                    continue
                for info in unique_infos.values():
                    url = info["url"]
                    if url not in seen_urls:
                        seen_urls.add(url)
                        result = self._build_result(
                            url=url,
                            full_text=full_text,
                            domain=domain,
                            title=title,
                        )
                        if result:
                            results.append(result)
            except Exception as e:
                logger.debug(f"解析必应搜索结果项失败: {e}")
                continue

        return results

    def _build_queries(self, keyword: str, cloud_types: Optional[List[str]] = None) -> List[str]:
        """构造多个搜索查询以覆盖更多的网盘类型"""
        domains = self._get_cloud_patterns(cloud_types)

        # 对每个域名构造一个独立查询
        queries = []
        for domain in domains:
            queries.append(f"{domain}/s/ {keyword}")
        return queries

    def _extract_cloud_urls(
        self, text: str, domains: List[str], keyword: str
    ) -> List[dict]:
        """从文本中提取云盘分享链接"""
        found = []
        text_lower = text.lower()

        for domain in domains:
            # 构建各种可能的 URL 格式正则
            # 标准格式: https://pan.quark.cn/s/xxxx
            # 非标准: https:pan.quark.cn/s/xxxx (缺少//)
            # 带提取码: https://pan.baidu.com/s/xxxx?pwd=1234
            if "pan.quark.cn" in domain:
                patterns = [
                    r'https?://pan\.quark\.cn/s/[a-zA-Z0-9]+',
                    r'https?:pan\.quark\.cn/s/[a-zA-Z0-9]+',
                ]
            elif "pan.baidu.com" in domain:
                patterns = [
                    r'https?://pan\.baidu\.com/s/[a-zA-Z0-9_-]+(?:\?pwd=[a-zA-Z0-9]+)?',
                    r'https?:pan\.baidu\.com/s/[a-zA-Z0-9_-]+',
                ]
            elif "aliyundrive.com" in domain or "alipan.com" in domain:
                patterns = [
                    r'https?://(?:www\.)?(?:aliyundrive|alipan)\.com/s/[a-zA-Z0-9]+',
                ]
            elif "pan.xunlei.com" in domain:
                patterns = [
                    r'https?://pan\.xunlei\.com/s/[a-zA-Z0-9_-]+',
                ]
            elif "cloud.189.cn" in domain:
                patterns = [
                    r'https?://cloud\.189\.cn/(?:t|web/share)\?code=[a-zA-Z0-9]+',
                ]
            elif "drive.uc.cn" in domain:
                patterns = [
                    r'https?://drive\.uc\.cn/s/[a-zA-Z0-9]+',
                ]
            elif "115.com" in domain:
                patterns = [
                    r'https?://115\.com/s/[a-zA-Z0-9]+',
                ]
            elif "123pan.com" in domain or "123684.com" in domain:
                patterns = [
                    r'https?://(?:www\.)?123(?:pan|684|865|912)\.com/s/[a-zA-Z0-9_-]+',
                ]
            elif "caiyun.139.com" in domain:
                patterns = [
                    r'https?://caiyun\.139\.com/m/i\?[a-zA-Z0-9]+',
                ]
            else:
                patterns = [
                    rf'https?://{re.escape(domain)}/s/[a-zA-Z0-9]+',
                ]

            for pattern in patterns:
                matches = re.finditer(pattern, text_lower)
                for match in matches:
                    url = match.group()
                    # 修复非标准格式 (https: -> https://)
                    if url.startswith("https:") and "//" not in url[6:8]:
                        url = url.replace("https:", "https://", 1)
                    found.append({"url": url, "domain": domain})

        return found

    def _build_result(
        self, url: str, full_text: str, domain: str, title: str = ""
    ) -> Optional[SearchResult]:
        """从提取的信息构建 SearchResult"""
        cloud_type = self._identify_cloud_type(domain)
        if not cloud_type:
            return None

        # 从文本中提取标题（取搜索结果中 h2 a 的文本）
        # 由于已丢失具体元素，使用第一个有意义的文本作为标题
        title = self._clean_title(title) or self._extract_title(full_text, url)

        # 提取提取码
        share_code = self._extract_code(full_text, url)

        # 提取文件大小
        file_size = self._extract_file_size(full_text)

        # 提取描述
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
        """从文本中提取资源标题"""
        # 先尝试提取云盘链接后面的第一个有意义的文本块
        url_escaped = re.escape(url)
        # 找 URL 后面的文本
        match = re.search(url_escaped[:40] + r'([^。，！？\n]{8,80})', text)
        if match:
            title = self._clean_title(match.group(1).strip())
            if len(title) > 4:
                return title

        # 找 URL 之前的文本
        match = re.search(r'([^。，！？\n]{4,60})' + url_escaped[:30], text)
        if match:
            title = self._clean_title(match.group(1).strip())
            if len(title) > 4:
                return title

        # 从完整文本中取第一个有意义的行
        lines = re.split(r'[\n\r]+', text)
        for line in lines:
            line = self._clean_title(line.strip())
            if len(line) > 8 and 'http' not in line:
                return line[:80] + "..." if len(line) > 80 else line

        # 取整个文本的前 80 个字符
        cleaned = re.sub(r'\s+', ' ', text).strip()
        cleaned = self._clean_title(cleaned)
        if len(cleaned) > 80:
            return cleaned[:80] + "..."
        return cleaned[:80]

    def _clean_title(self, title: str) -> str:
        """清理标题中的杂音"""
        # 移除常见的网站域名前缀
        title = re.sub(r'^[a-zA-Z0-9.-]+\.(com|cn|net|org)\s*', '', title)
        # 移除 "https://" 或 "http://" 开头的垃圾
        title = re.sub(r'^https?://[^\s]+', '', title)
        # 移除多余的空白
        title = re.sub(r'\s+', ' ', title).strip()
        return title

    def _extract_code(self, text: str, url: str) -> str:
        """从文本或 URL 中提取提取码"""
        # 先检查 URL 中的 pwd 参数
        pwd_match = self.PWD_PATTERN.search(url)
        if pwd_match:
            return pwd_match.group(1)

        # 再检查文本中的提取码模式
        code_match = self.CODE_PATTERN.search(text)
        if code_match:
            return code_match.group(1)

        return ""

    def _extract_file_size(self, text: str) -> str:
        """从文本中提取文件大小"""
        size_match = re.search(r'(\d+(?:\.\d+)?\s*(?:GB|MB|TB|KB))', text, re.IGNORECASE)
        if size_match:
            return size_match.group(1).upper()
        return ""

    def _extract_description(self, text: str, url: str, title: str) -> str:
        """提取描述信息"""
        # 移除 URL 和 title，取剩下的文本
        cleaned = text.replace(url, "").replace(title, "")
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        if len(cleaned) > 200:
            return cleaned[:200] + "..."
        return cleaned

    def _identify_cloud_type(self, domain: str) -> Optional[str]:
        """根据域名识别网盘类型"""
        for ct, domains in CLOUD_DOMAIN_MAP.items():
            for d in domains:
                if d in domain:
                    return ct
        return None
