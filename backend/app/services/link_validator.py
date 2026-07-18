"""网盘分享链接有效性检测。

检测发生在搜索结果返回前。明确失效、需要但缺少提取码、网络状态无法确认的
链接都不会进入严格搜索结果；只有网盘接口明确确认可访问的链接才会保留。
"""
import asyncio
import difflib
import logging
import re
import time
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import parse_qs, quote, urlparse

import httpx

from app.config import settings
from app.sources import SearchResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ValidationResult:
    status: str
    message: str
    verified_title: str = ""

    @property
    def usable(self) -> bool:
        return self.status == "valid"


class LinkValidator:
    """使用各网盘公开落地页/API并发确认分享状态。"""

    STRICT_SUPPORTED_TYPES = {"quark", "baidu", "aliyun", "123"}

    INVALID_MARKERS = (
        "分享已取消", "分享被取消", "链接已失效", "分享已失效", "分享不存在",
        "文件不存在", "页面不存在", "已过期", "违规", "被删除", "not found",
    )

    def __init__(self):
        self._cache: dict[str, tuple[float, ValidationResult]] = {}
        self._cache_ttl = settings.LINK_CHECK_CACHE_TTL

    async def validate_many(self, results: List[SearchResult]) -> List[SearchResult]:
        if not results:
            return []

        timeout = httpx.Timeout(settings.LINK_CHECK_TIMEOUT)
        limits = httpx.Limits(
            max_connections=settings.LINK_CHECK_CONCURRENCY,
            max_keepalive_connections=settings.LINK_CHECK_CONCURRENCY,
        )
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36"
            )
        }
        semaphore = asyncio.Semaphore(settings.LINK_CHECK_CONCURRENCY)
        async with httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            follow_redirects=True,
            trust_env=False,
            headers=headers,
        ) as client:
            checks = await asyncio.gather(
                *(
                    self._validate_cached(client, item, semaphore)
                    for item in results
                ),
                return_exceptions=True,
            )

        usable: List[SearchResult] = []
        for item, check in zip(results, checks):
            if isinstance(check, Exception):
                logger.debug("链接检测异常 %s: %s", item.share_url, check)
                item.validation_status = "unknown"
                item.validation_message = "检测请求失败"
                continue
            item.validation_status = check.status
            item.validation_message = check.message
            item.verified_title = check.verified_title
            if (
                check.usable
                and not item.source_name.startswith("PanSou聚合")
                and check.verified_title
                and not self._titles_consistent(item.title, check.verified_title)
            ):
                item.validation_status = "invalid"
                item.validation_message = "搜索标题与网盘实际内容不符"
                continue
            if check.usable:
                usable.append(item)
        return usable

    async def _validate_cached(
        self,
        client: httpx.AsyncClient,
        item: SearchResult,
        semaphore: asyncio.Semaphore,
    ) -> ValidationResult:
        key = f"{item.cloud_type}:{item.share_url}:{item.share_code}"
        cached = self._cache.get(key)
        now = time.monotonic()
        if cached and cached[0] > now:
            return cached[1]

        async with semaphore:
            result = await self._validate(client, item)
        self._cache[key] = (now + self._cache_ttl, result)
        return result

    async def _validate(
        self, client: httpx.AsyncClient, item: SearchResult
    ) -> ValidationResult:
        handlers = {
            "quark": self._check_quark,
            "baidu": self._check_baidu,
            "aliyun": self._check_aliyun,
            "123": self._check_123,
        }
        handler = handlers.get(item.cloud_type)
        if handler is None:
            return ValidationResult("unknown", "该网盘暂不支持强有效性检测")
        try:
            return await handler(client, item)
        except (httpx.HTTPError, ValueError) as exc:
            logger.debug("链接检测请求失败 %s: %s", item.share_url, exc)
            return ValidationResult("unknown", "网盘暂时无法确认状态")

    def supports_strict_check(self, cloud_type: str) -> bool:
        return cloud_type in self.STRICT_SUPPORTED_TYPES

    async def _check_quark(
        self, client: httpx.AsyncClient, item: SearchResult
    ) -> ValidationResult:
        match = re.search(r"/s/([A-Za-z0-9_-]+)", item.share_url)
        if not match:
            return ValidationResult("invalid", "分享地址格式无效")
        share_id = match.group(1)
        password = self._password(item)
        response = await client.post(
            "https://drive-h.quark.cn/1/clouddrive/share/sharepage/token",
            json={
                "pwd_id": share_id,
                "passcode": password,
                "support_visit_limit_private_share": True,
            },
            headers={
                "origin": "https://pan.quark.cn",
                "referer": "https://pan.quark.cn/",
                "content-type": "application/json",
            },
        )
        data = response.json()
        code = int(data.get("code", -1))
        message = str(data.get("message", ""))
        if code in {41004, 41006, 41010, 41011}:
            return ValidationResult("invalid", message or "链接失效")
        if code == 41008:
            return ValidationResult("locked", "缺少或错误的提取码")
        if code != 0:
            if self._contains_invalid(message):
                return ValidationResult("invalid", message)
            return ValidationResult("unknown", message or "无法确认链接状态")

        detail = data.get("data") or {}
        title = str(detail.get("title", "")).strip()
        file_num = detail.get("file_num")
        if file_num is not None and int(file_num) <= 0:
            return ValidationResult("invalid", "分享内容为空", title)
        if not title and file_num is None:
            return ValidationResult("unknown", "网盘未返回资源信息")
        return ValidationResult("valid", "网盘已确认链接有效", title)

    async def _check_baidu(
        self, client: httpx.AsyncClient, item: SearchResult
    ) -> ValidationResult:
        match = re.search(r"/s/([A-Za-z0-9_-]+)", item.share_url)
        if not match:
            return ValidationResult("invalid", "分享地址格式无效")
        short_url = match.group(1).lstrip("1")
        password = self._password(item)
        cookie = ""
        if password:
            verify = await client.post(
                f"https://pan.baidu.com/share/verify?surl={quote(short_url)}&pwd={quote(password)}",
                data={"pwd": password, "vcode": "", "vcode_str": ""},
                headers={"referer": item.share_url},
            )
            verify_data = verify.json()
            errno = int(verify_data.get("errno", -1))
            if errno in {-9, -12}:
                return ValidationResult("locked", "提取码错误")
            if errno != 0:
                message = str(verify_data.get("errmsg") or verify_data.get("err_msg") or "")
                return ValidationResult(
                    "invalid" if self._contains_invalid(message) else "unknown",
                    message or "提取码验证失败",
                )
            cookie = str(verify_data.get("randsk", ""))

        list_response = await client.get(
            "https://pan.baidu.com/share/list",
            params={
                "web": "1", "page": "1", "num": "20", "order": "time",
                "desc": "1", "showempty": "0", "shorturl": short_url,
                "root": "1", "clienttype": "0",
            },
            headers={"referer": item.share_url},
            cookies={"BDCLND": cookie} if cookie else None,
        )
        data = list_response.json()
        errno = int(data.get("errno", -1))
        title = str(data.get("title", "")).strip().lstrip("/")
        files = data.get("list") or []
        if errno == 0 and files:
            if not title and isinstance(files[0], dict):
                title = str(files[0].get("server_filename", "")).strip()
            return ValidationResult("valid", "网盘已确认链接有效", title)
        if errno in {-9, -12}:
            return ValidationResult("locked", "需要正确的提取码")
        message = str(data.get("show_msg") or data.get("errmsg") or "")
        if errno in {-7, -21, 105, 115, 117, 145} or self._contains_invalid(message):
            return ValidationResult("invalid", message or "链接失效")
        return ValidationResult("unknown", message or f"网盘返回状态 {errno}")

    async def _check_aliyun(
        self, client: httpx.AsyncClient, item: SearchResult
    ) -> ValidationResult:
        match = re.search(r"/s/([A-Za-z0-9_-]+)", item.share_url)
        if not match:
            return ValidationResult("invalid", "分享地址格式无效")
        share_id = match.group(1)
        response = await client.post(
            "https://api.aliyundrive.com/adrive/v3/share_link/get_share_by_anonymous",
            params={"share_id": share_id},
            json={"share_id": share_id},
            headers={
                "origin": "https://www.alipan.com",
                "referer": "https://www.alipan.com/",
                "x-canary": "client=web,app=share,version=v2.3.1",
            },
        )
        data = response.json()
        code = str(data.get("code", ""))
        message = str(data.get("message", ""))
        title = str(data.get("share_name") or data.get("share_title") or "").strip()
        file_count = data.get("file_count")
        if code or self._contains_invalid(message):
            return ValidationResult("invalid", message or code or "链接失效")
        if title or (file_count is not None and int(file_count) > 0):
            return ValidationResult("valid", "网盘已确认链接有效", title)
        return ValidationResult("unknown", "网盘未返回资源信息")

    async def _check_123(
        self, client: httpx.AsyncClient, item: SearchResult
    ) -> ValidationResult:
        match = re.search(r"/s/([A-Za-z0-9_-]+)", item.share_url)
        if not match:
            return ValidationResult("invalid", "分享地址格式无效")
        response = await client.get(
            "https://www.123pan.com/api/share/info",
            params={"shareKey": match.group(1)},
        )
        if response.status_code == 403:
            return ValidationResult("valid", "网盘已确认链接有效")
        data = response.json()
        code = int(data.get("code", -1))
        message = str(data.get("message", ""))
        if code == 0:
            return ValidationResult("valid", "网盘已确认链接有效")
        if (data.get("data") or {}).get("HasPwd"):
            return ValidationResult("locked", "需要正确的提取码")
        return ValidationResult("invalid", message or "链接失效")

    async def _check_web_page(
        self, client: httpx.AsyncClient, item: SearchResult
    ) -> ValidationResult:
        response = await client.get(item.share_url)
        if response.status_code in {404, 410}:
            return ValidationResult("invalid", f"网盘返回 HTTP {response.status_code}")
        body = response.text[:250000].casefold()
        if self._contains_invalid(body):
            return ValidationResult("invalid", "落地页显示链接失效")
        hostname = (urlparse(item.share_url).hostname or "").casefold()
        if response.status_code < 400 and hostname and hostname in str(response.url).casefold():
            # 只有页面能打开不能证明分享文件仍存在。缺少稳定公开检测 API 的
            # 网盘按 unknown 处理，严格搜索不会展示，避免把“页面200”误报为有效。
            return ValidationResult("unknown", "落地页可访问，但无法确认分享内容")
        return ValidationResult("unknown", "无法确认链接状态")

    def _password(self, item: SearchResult) -> str:
        if item.share_code:
            return item.share_code
        try:
            query = parse_qs(urlparse(item.share_url).query)
            return (query.get("pwd") or query.get("password") or [""])[0]
        except ValueError:
            return ""

    def _contains_invalid(self, text: str) -> bool:
        lowered = text.casefold()
        return any(marker.casefold() in lowered for marker in self.INVALID_MARKERS)

    def _titles_consistent(self, search_title: str, verified_title: str) -> bool:
        """判断非结构化搜索标题是否确实对应网盘中的资源名称。"""
        def normalize(value: str) -> str:
            value = value.casefold()
            value = re.sub(
                r"(?:夸克|百度|阿里|迅雷)?(?:网盘|云盘)|资源|分享|链接|合集|全集|"
                r"4k|8k|1080p|2160p|高清|中字|电影|电视剧",
                "",
                value,
                flags=re.IGNORECASE,
            )
            return re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", value)

        left = normalize(search_title)
        right = normalize(verified_title)
        if len(left) < 2 or len(right) < 2:
            return False
        if (len(left) >= 3 and left in right) or (len(right) >= 3 and right in left):
            return True
        left_pairs = {left[i:i + 2] for i in range(len(left) - 1)}
        right_pairs = {right[i:i + 2] for i in range(len(right) - 1)}
        if left_pairs & right_pairs:
            return True
        return difflib.SequenceMatcher(None, left, right).ratio() >= 0.35


link_validator = LinkValidator()
