"""
搜索API路由
"""
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.searcher import orchestrator
from app.sources import CLOUD_TYPE_MAP

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["搜索"])


@router.get("/search")
async def search(
    kw: str = Query(..., min_length=1, max_length=200, description="搜索关键字"),
    types: Optional[str] = Query(None, description="网盘类型，逗号分隔。可选: quark,baidu,aliyun,xunlei,tianyi,uc,115,123,yidong"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页条数"),
    sort: str = Query("relevance", description="排序方式: relevance(综合), recent(最新)"),
    refresh: bool = Query(False, description="是否跳过缓存强制刷新"),
    db: AsyncSession = Depends(get_db),
):
    """
    搜索网盘资源

    并发请求多个搜索源（百度/必应/API），聚合去重后返回结果。
    支持按网盘类型筛选、分页、排序、缓存。
    """
    # 解析网盘类型
    cloud_types = None
    if types:
        cloud_types = [t.strip().lower() for t in types.split(",") if t.strip()]
        # 验证网盘类型
        valid_types = set(CLOUD_TYPE_MAP.keys())
        invalid = [t for t in cloud_types if t not in valid_types]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"无效的网盘类型: {', '.join(invalid)}。可选: {', '.join(sorted(valid_types))}",
            )

    if sort not in {"relevance", "recent"}:
        raise HTTPException(
            status_code=400,
            detail="无效的排序方式。可选: relevance, recent",
        )

    try:
        result = await orchestrator.search(
            db=db,
            keyword=kw,
            cloud_types=cloud_types,
            page=page,
            page_size=size,
            sort_by=sort,
            skip_cache=refresh,
        )
        return {"code": 0, "data": result, "message": "ok"}
    except HTTPException:
        raise
    except Exception:
        logger.exception("搜索服务异常")
        raise HTTPException(status_code=500, detail="搜索服务暂时不可用，请稍后重试")


@router.get("/hot")
async def hot_keywords(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """获取热门搜索关键字"""
    keywords = await orchestrator.get_hot_keywords(db, limit)
    return {"code": 0, "data": keywords}


@router.get("/history")
async def search_history(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取搜索历史"""
    history = await orchestrator.get_history(db, limit)
    return {"code": 0, "data": history}


@router.delete("/history")
async def clear_history(db: AsyncSession = Depends(get_db)):
    """清空搜索历史"""
    await orchestrator.clear_history(db)
    return {"code": 0, "message": "搜索历史已清空"}
