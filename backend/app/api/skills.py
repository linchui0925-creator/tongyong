"""Skills API - 兼容 SQLite 技能格式的 Hermes 平文件桥接"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Any, Dict

import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/skills", tags=["skills"])

_skill_manager = None


def init(skill_manager):
    global _skill_manager
    _skill_manager = skill_manager


@router.get("")
async def list_skills():
    """获取技能列表 (Hermes 平文件格式)"""
    if not _skill_manager:
        return {"skills": [], "total": 0}

    skills = _skill_manager.list_skills()
    # 转换为前端期望的格式
    result = []
    for s in skills:
        detail = _skill_manager.view_skill(s["name"])
        result.append({
            "id": s["name"],
            "name": s["name"],
            "content": detail["body"][:200] if detail and detail.get("body") else s.get("description", ""),
            "category": s.get("category", "general"),
            "usage_count": 0,
            "success_rate": 100.0,
            "version": float(s.get("version", "1.0.0")),
            "trigger_conditions": [],
            "execution_steps": [],
        })
    return {"skills": result, "total": len(result)}


@router.get("/{name}")
async def get_skill(name: str):
    """获取技能详情"""
    if not _skill_manager:
        raise HTTPException(status_code=503, detail="Skill manager not initialized")
    skill = _skill_manager.view_skill(name)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    return skill


@router.delete("/{skill_id}")
async def delete_skill(skill_id: str):
    """删除技能"""
    if not _skill_manager:
        raise HTTPException(status_code=503, detail="Skill manager not initialized")
    ok, msg = _skill_manager.delete_skill(skill_id)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True}
