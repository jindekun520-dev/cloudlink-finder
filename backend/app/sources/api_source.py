"""
通用API搜索源
支持对接第三方公开的网盘搜索API
"""
import logging
from typing import List, Optional

import httpx

from app.sources import SearchResult, CLOUD_TYPE_MAP

logger = logging.getLogger(__name__)


class APISearchSource:
    """通用API搜索源"""

    name = ""
    source_type = "api"
    enabled = True

    def __init__(
        self,
        name: str,
        endpoint: str,
        method: str = "GET",
        timeout: int = 15,
        headers: Optional[dict] = None,
        params_template: Optional[dict] = None,
        response_path: str = "data.items",  # JSON响应中结果列表的路径
        field_map: Optional[dict] = None,  # 字段映射
    ):
        self.name = name
        self.endpoint = endpoint
        self.method = method.upper()
        self.timeout = timeout
        self.headers = headers or {}
        self.params_template = params_template or {}
        self.response_path = response_path
        self.field_map = field_map or {
            "title": "title",
            "cloud_type": "cloud_type",
            "cloud_name": "cloud_name",
            "share_url": "share_url",
            "share_code": "share_code",
        }

    async def search(
        self, keyword: str, cloud_types: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """调用API搜索"""
        results = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            **self.headers,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as client:
                if self.method == "POST":
                    body = {**self.params_template, "kw": keyword}
                    if cloud_types:
                        body["cloud_types"] = ",".join(cloud_types)
                    response = await client.post(self.endpoint, json=body, headers=headers)
                else:
                    params = {**self.params_template, "kw": keyword}
                    if cloud_types:
                        params["cloud_types"] = ",".join(cloud_types)
                    response = await client.get(self.endpoint, params=params, headers=headers)

                response.raise_for_status()
                data = response.json()

                # 按路径提取结果列表
                items = self._get_nested(data, self.response_path, [])

                for item in items:
                    try:
                        result = self._map_result(item)
                        if result:
                            results.append(result)
                    except Exception as e:
                        logger.debug(f"API结果映射失败: {e}")

        except httpx.TimeoutException:
            logger.warning(f"API搜索源 '{self.name}' 超时")
        except Exception as e:
            logger.error(f"API搜索源 '{self.name}' 异常: {e}")

        return results

    def _get_nested(self, data: dict, path: str, default=None):
        """按点号分隔的路径获取嵌套值"""
        keys = path.split(".")
        for key in keys:
            if isinstance(data, dict):
                data = data.get(key, default)
            elif isinstance(data, list):
                try:
                    data = data[int(key)]
                except (IndexError, ValueError):
                    return default
            else:
                return default
        return data or default

    def _map_result(self, item: dict) -> Optional[SearchResult]:
        """将API返回的原始数据映射为SearchResult"""
        fm = self.field_map
        title = self._get_nested(item, fm.get("title", "title"), "")
        share_url = self._get_nested(item, fm.get("share_url", "share_url"), "")

        if not share_url:
            return None

        cloud_type = self._get_nested(item, fm.get("cloud_type", "cloud_type"), "")
        cloud_name = CLOUD_TYPE_MAP.get(cloud_type, self._get_nested(item, fm.get("cloud_name", "cloud_name"), ""))

        return SearchResult(
            title=title or "未知资源",
            cloud_type=cloud_type or "unknown",
            cloud_name=cloud_name or "未知网盘",
            share_url=share_url,
            share_code=self._get_nested(item, fm.get("share_code", "share_code"), ""),
            description=self._get_nested(item, fm.get("description", "description"), ""),
            file_size=self._get_nested(item, fm.get("file_size", "file_size"), ""),
            source_name=self.name,
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.source_type,
            "enabled": self.enabled,
            "endpoint": self.endpoint,
        }
