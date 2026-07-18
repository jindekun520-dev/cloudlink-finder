"""
搜索源基类
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SearchResult:
    """统一的搜索结果数据结构"""

    title: str  # 资源标题
    cloud_type: str  # 网盘类型标识：quark/baidu/aliyun/xunlei/tianyi/uc/115/123/yidong
    cloud_name: str  # 网盘中文名：夸克网盘/百度网盘/...
    share_url: str  # 分享链接
    share_code: str = ""  # 提取码
    description: str = ""  # 资源描述
    file_size: str = ""  # 文件大小
    source_name: str = ""  # 来源搜索源名称
    rank: float = 0.0  # 排序分数
    validation_status: str = "unchecked"  # valid/invalid/locked/unknown/unchecked
    validation_message: str = ""  # 链接检测说明
    verified_title: str = ""  # 网盘落地页返回的真实资源名称

    @property
    def unique_key(self) -> str:
        """生成唯一标识（用于去重）"""
        import hashlib
        return hashlib.md5(self.share_url.encode()).hexdigest()[:16]


# 支持的网盘类型映射
CLOUD_TYPE_MAP = {
    "quark": "夸克网盘",
    "baidu": "百度网盘",
    "aliyun": "阿里云盘",
    "xunlei": "迅雷网盘",
    "tianyi": "天翼云盘",
    "uc": "UC网盘",
    "115": "115网盘",
    "123": "123云盘",
    "yidong": "移动云盘",
}

# 各网盘的域名特征（用于识别链接属于哪个网盘）
CLOUD_DOMAIN_MAP = {
    "quark": ["pan.quark.cn"],
    "baidu": ["pan.baidu.com"],
    "aliyun": ["aliyundrive.com", "alipan.com"],
    "xunlei": ["pan.xunlei.com"],
    "tianyi": ["cloud.189.cn"],
    "uc": ["drive.uc.cn"],
    "115": ["115.com"],
    "123": ["123pan.com", "123684.com", "123865.com", "123912.com"],
    "yidong": ["caiyun.139.com"],
}

# 网盘链接正则模式（用于从搜索引擎结果中识别）
CLOUD_URL_PATTERNS = {
    "quark": r'https?://pan\.quark\.cn/s/[a-zA-Z0-9]+',
    "baidu": r'https?://pan\.baidu\.com/s/[a-zA-Z0-9_-]+',
    "aliyun": r'https?://(?:www\.)?(?:aliyundrive|alipan)\.com/s/[a-zA-Z0-9]+',
    "xunlei": r'https?://pan\.xunlei\.com/s/[a-zA-Z0-9_-]+',
    "tianyi": r'https?://cloud\.189\.cn/(?:t|web/share)\?code=[a-zA-Z0-9]+',
    "uc": r'https?://drive\.uc\.cn/s/[a-zA-Z0-9]+',
    "115": r'https?://115\.com/s/[a-zA-Z0-9]+',
    "123": r'https?://(?:www\.)?123(?:pan|684|865|912)\.com/s/[a-zA-Z0-9_-]+',
    "yidong": r'https?://caiyun\.139\.com/m/i\?[a-zA-Z0-9]+',
}


class SearchSource(ABC):
    """搜索源抽象基类"""

    name: str = ""  # 搜索源名称
    source_type: str = ""  # 类型：search_engine / api
    enabled: bool = True

    @abstractmethod
    async def search(
        self, keyword: str, cloud_types: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """执行搜索，返回结果列表"""
        ...

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.source_type,
            "enabled": self.enabled,
        }
