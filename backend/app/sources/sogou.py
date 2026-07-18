"""
搜狗搜索引擎聚合源
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


class SogouSearchSource:
    """搜狗搜索引擎"""

    name = "搜狗搜索"
    source_type = "search_engine"
    enabled = True

    BASE_URL = "https://www.sogou.com/web"

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

    def _build_queries(self, keyword: str, cloud_types: Optional[List[str]] = None) -> List[str]:
        """构造搜索查询，限制数量以避免触发反爬"""
        domains = self._get_cloud_patterns(cloud_types)

        queries = []
        for domain in domains:
            # 只对主要云盘域名生成查询，避免过多请求
            # 并且只搜索 URL 模式，不生成 "链接:" 前缀的变体
            queries.append(f"{domain}/s/ {keyword}")
            # 最多5个查询，避免触发反爬
            if len(queries) >= 5:
                break

        return queries

    def _extract_cloud_urls_from_html(self, html: str, domains: List[str]) -> List[dict]:
        """从 HTML 中提取所有匹配的云盘分享链接"""
        found = []

        for domain in domains:
            domain_escaped = re.escape(domain)

            # 搜狗摘要经常会把 URL 拆成： https:// pan.quark.cn/s/ abc123
            # 因此这里允许协议、域名分隔符和分享码前出现空白。
            if "cloud.189.cn" in domain:
                patterns = [
                    rf'https?\s*:\s*/\s*/\s*{domain_escaped}\s*/\s*(?:t|web/share)\s*\?\s*code\s*=\s*[a-zA-Z0-9]+',
                ]
            elif "caiyun.139.com" in domain:
                patterns = [
                    rf'https?\s*:\s*/\s*/\s*{domain_escaped}\s*/\s*m\s*/\s*i\s*\?\s*[a-zA-Z0-9]+',
                ]
            else:
                patterns = [
                    rf'https?\s*:\s*/\s*/\s*{domain_escaped}\s*/\s*s\s*/\s*[a-zA-Z0-9_-]+(?:\s*\?\s*pwd\s*=\s*[a-zA-Z0-9]+)?',
                ]

            for pattern in patterns:
                matches = re.finditer(pattern, html, re.IGNORECASE)
                for match in matches:
                    # URL 可能包含空格，先压缩后再交给后续逻辑。
                    url = re.sub(r"\s+", "", match.group())
                    found.append({"url": url, "domain": domain})

        return found

    async def search(
        self, keyword: str, cloud_types: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """通过搜狗搜索网盘资源"""
        results = []
        seen_urls = set()

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

        domains_to_search = self._get_cloud_patterns(cloud_types)
        queries = self._build_queries(keyword, cloud_types)

        # 为每个域名构造不同的搜索查询
        # 使用同一个客户端来保持 cookies，并在请求间加入延时
        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            # NAS 直连搜索引擎时不应继承宿主机错误的代理环境变量。
            trust_env=False,
        ) as client:
            # 先访问首页获取 cookies
            try:
                await client.get("https://www.sogou.com/", headers=headers)
            except Exception:
                pass

            for index, query in enumerate(queries):
                try:
                    # 只在连续请求之间做很短的礼貌间隔。原来的 1.5 秒会让
                    # 全网盘搜索固定增加 7.5 秒以上，严重拖慢用户体验。
                    if index > 0:
                        await asyncio.sleep(0.25)

                    response = await client.get(
                        self.BASE_URL,
                        params={"query": query},
                        headers=headers,
                    )

                    # 检查是否被反爬拦截
                    if (
                        "antispider" in str(response.url)
                        or response.status_code in (301, 302, 303)
                        or "验证" in response.text
                    ):
                        logger.warning(f"搜狗搜索反爬拦截 (query: {query})")
                        break

                    if response.status_code != 200:
                        continue

                    soup = BeautifulSoup(response.text, "lxml")
                    items = soup.select(".vrwrap")

                    for item in items:
                        try:
                            full_text = item.get_text("\n", strip=True)
                            title_elem = item.select_one("h3 a")
                            title = title_elem.get_text(strip=True) if title_elem else ""

                            # 从文本中提取云盘链接
                            url_infos = self._extract_cloud_urls_from_html(
                                str(item), domains_to_search
                            )

                            # 搜索摘要块里有多个链接时，标题与具体链接的对应关系
                            # 无法可靠证明。严格模式只接受“一卡一链接”。
                            unique_infos = {
                                info["url"]: info for info in url_infos
                            }
                            if len(unique_infos) != 1:
                                continue

                            for info in unique_infos.values():
                                url = info["url"]
                                if url in seen_urls:
                                    continue
                                seen_urls.add(url)

                                result = self._build_result(
                                    url=url,
                                    title=title,
                                    full_text=full_text,
                                )
                                if result:
                                    results.append(result)

                        except Exception as e:
                            logger.debug(f"解析搜狗搜索结果项失败: {e}")
                            continue

                except httpx.TimeoutException:
                    logger.debug(f"搜狗搜索超时 (query: {query})")
                    continue
                except Exception as e:
                    logger.debug(f"搜狗搜索异常 (query: {query}): {e}")
                    continue

        return results

    def _build_result(
        self, url: str, title: str, full_text: str
    ) -> Optional[SearchResult]:
        """从提取的信息构建 SearchResult"""
        cloud_type = self._identify_cloud_type(url)
        if not cloud_type:
            return None

        # 优先从分享链接前的上下文恢复完整标题，搜索引擎 h3 经常会截断标题。
        clean_title = self._extract_better_title(title, full_text, url)

        # 提取提取码
        share_code = self._extract_code(full_text, url)

        # 提取文件大小
        file_size = self._extract_file_size(full_text)

        # 提取描述
        description = self._extract_description(full_text, url, clean_title)

        return SearchResult(
            title=clean_title or url,
            cloud_type=cloud_type,
            cloud_name=CLOUD_TYPE_MAP.get(cloud_type, ""),
            share_url=url,
            share_code=share_code,
            description=description,
            file_size=file_size,
            source_name=self.name,
        )

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
        cleaned = text.replace(url, "").replace(title, "")
        # 删除被搜索引擎拼进摘要的链接、公众号和推荐词，避免把广告噪声展示给用户。
        cleaned = re.sub(
            r'https?\s*:\s*(?:/\s*/\s*)?[^\s，。！？）】》]+', '', cleaned, flags=re.IGNORECASE
        )
        cleaned = re.sub(r'(?:链接|夸克链接|百度链接|分享链接)\s*[：:：]?\s*', '', cleaned)
        cleaned = re.sub(r'(?:公众号|微信)\s*', '', cleaned)
        cleaned = re.sub(r'20\d{2}[-年]\d{1,2}[-月]\d{1,2}日?', '', cleaned)
        cleaned = re.split(r'推荐您搜索|相关推荐|网页快照|免责声明', cleaned, maxsplit=1)[0]
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        # 只有短于 8 个字符的残片或纯符号时才认为没有有效描述。
        cleaned = re.sub(r'^[：:、\-\s]+|[：:、\-\s]+$', '', cleaned)
        if len(cleaned) < 8 or not re.search(r'[\u4e00-\u9fffA-Za-z0-9]', cleaned):
            return ""
        if len(cleaned) > 200:
            return cleaned[:200] + "..."
        return cleaned

    def _extract_better_title(self, title: str, text: str, url: str) -> str:
        """从搜索标题和分享链接附近的上下文中恢复更完整、干净的标题。"""
        cleaned_title = self._clean_title(title)
        if cleaned_title and not cleaned_title.startswith("..."):
            return cleaned_title

        normalized = re.sub(r"\s+", " ", text).strip()
        # 搜索摘要可能在 URL 的协议、域名和 /s/ 两侧插入空格，
        # 用压缩后的副本定位链接，才能拿到链接前的完整标题。
        compact = re.sub(r"https?\s*:\s*/\s*/\s*", "https://", normalized, flags=re.IGNORECASE)
        compact = re.sub(r"\s*/\s*", "/", compact)
        compact = re.sub(r"(?<=/s/)\s+", "", compact)
        url_pos = compact.lower().find(url.lower())
        if url_pos >= 0:
            prefix = compact[max(0, url_pos - 120):url_pos]
            # 从最近的句号/日期/公众号提示之后开始取，避免带上前一段摘要。
            prefix = re.split(r'公众号|微信|推荐您搜索|\d{4}[-年]\d{1,2}', prefix)[-1]
            prefix = re.sub(r'(?:链接|夸克链接|百度链接|分享链接)\s*[：:：]?\s*$', '', prefix)
            candidate = self._clean_title(prefix)
            candidate = re.sub(r'^(?:…|\.{2,})\s*', '', candidate)
            candidate = re.sub(r'^[：:、\-\s]+|[：:、\-\s]+$', '', candidate)
            if len(candidate) >= 4 and 'http' not in candidate.lower():
                return candidate[:80] + '...' if len(candidate) > 80 else candidate

        return re.sub(r'^(?:…|\.{2,})\s*', '', cleaned_title)

    def _clean_title(self, title: str) -> str:
        """清理标题中的杂音"""
        if not title:
            return ""
        # 搜索摘要标题经常包含“链接：https://...”或被拆开的 URL。
        title = re.sub(
            r'https?\s*:\s*(?:/\s*/\s*)?[^\s，。！？）】》]+', '', title, flags=re.IGNORECASE
        )
        title = re.sub(r'链接\s*[：:]\s*', '', title)
        title = re.sub(r'^(.{2,40})[：:]\s*\1', r'\1', title)
        # 移除常见的网站域名前缀
        # 移除常见的网站域名前缀 "xxx.com" 或 "xxx.cn"
        title = re.sub(r'^[a-zA-Z0-9.-]+\.(com|cn|net|org)\s+', '', title)
        # 移除多余的空白
        title = re.sub(r'\s+', ' ', title).strip()
        title = re.sub(r'[：:、\-\s]+$', '', title)
        title = re.sub(r'^[：:、\-\s]+', '', title)
        return title

    def _identify_cloud_type(self, url: str) -> Optional[str]:
        """根据URL判断网盘类型"""
        url_lower = url.lower()
        for ct, domains in CLOUD_DOMAIN_MAP.items():
            for domain in domains:
                if domain in url_lower:
                    return ct
        return None
