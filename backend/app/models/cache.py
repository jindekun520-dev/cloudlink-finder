"""
搜索结果缓存模型
"""
import datetime
from sqlalchemy import String, Text, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SearchCache(Base):
    __tablename__ = "search_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    keyword: Mapped[str] = mapped_column(String(200), nullable=False, comment="搜索关键字")
    cloud_types: Mapped[str] = mapped_column(String(200), default="", comment="网盘类型，逗号分隔")
    results_json: Mapped[str] = mapped_column(Text, nullable=False, comment="缓存结果JSON")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )

    def __repr__(self):
        return f"<SearchCache(keyword='{self.keyword}', created_at={self.created_at})>"
