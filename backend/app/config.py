"""
应用配置管理
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置，支持环境变量覆盖"""

    # 应用基本信息
    APP_NAME: str = "网盘资源搜索神器"
    APP_VERSION: str = "1.0.6"
    DEBUG: bool = False

    # 服务配置
    HOST: str = "127.0.0.1"
    PORT: int = 8001

    # 数据库配置
    DATA_DIR: str = str(Path(__file__).parent.parent / "data")
    DATABASE_URL: str = ""

    def get_database_url(self) -> str:
        """获取数据库URL，默认使用SQLite"""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        os.makedirs(self.DATA_DIR, exist_ok=True)
        db_path = os.path.join(self.DATA_DIR, "pan_search.db")
        return f"sqlite+aiosqlite:///{db_path}"

    # 搜索配置
    SEARCH_TIMEOUT: int = 15  # 搜索源请求超时（秒）
    SEARCH_CONCURRENCY: int = 5  # 并发搜索源数量
    CACHE_TTL: int = 300  # 搜索结果缓存有效期（秒）
    LINK_CHECK_TIMEOUT: int = 8  # 单个网盘有效性检测超时（秒）
    LINK_CHECK_CONCURRENCY: int = 16  # 同时检测的链接数量
    LINK_CHECK_CACHE_TTL: int = 120  # 检测结果短缓存；到期后重新向网盘确认
    MAX_LINKS_TO_VALIDATE: int = 60  # 单次搜索最多检测的高相关候选数

    # 搜索源配置文件
    SOURCES_CONFIG: str = str(Path(__file__).parent.parent / "data" / "sources.yaml")

    # 请求头伪装
    USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    )

    class Config:
        env_prefix = "PANSEARCH_"
        env_file = ".env"


settings = Settings()
