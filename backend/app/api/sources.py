"""
搜索源管理API
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.searcher import orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sources", tags=["搜索源"])


class SourceInfo(BaseModel):
    name: str
    type: str
    enabled: bool


class SourceListResponse(BaseModel):
    code: int = 0
    data: List[SourceInfo]


@router.get("")
async def list_sources():
    """获取所有搜索源列表"""
    sources = orchestrator.get_sources()
    return {"code": 0, "data": sources}


@router.get("/types")
async def cloud_types():
    """获取支持的网盘类型列表"""
    from app.sources import CLOUD_TYPE_MAP

    types = [
        {"key": k, "name": v}
        for k, v in CLOUD_TYPE_MAP.items()
    ]
    return {"code": 0, "data": types}
