import json
import time
from pathlib import Path
from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.lazada_cookie_manager import cookie_manager
from app.services.lazada_session_health import session_health
from app.services.product_service import reset_lazada_session_alert


router = APIRouter(prefix="/lazada", tags=["Lazada Session"])
COOKIE_FILE = Path(settings.LAZADA_COOKIE_FILE).expanduser()


class CookiePayload(BaseModel):
    cookies: List[dict[str, Any]]


class CookieProfilePayload(CookiePayload):
    label: str = Field(default="Cookie mới", max_length=100)
    priority: Optional[int] = Field(default=None, ge=1)


class CookiePriorityPayload(BaseModel):
    profile_ids: List[int]


@router.post("/session")
async def save_lazada_session(payload: CookiePayload):
    """Legacy single-session API: replace the current active profile."""
    try:
        profile = await cookie_manager.replace_active(payload.cookies)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    reset_lazada_session_alert()
    return {"success": True, "message": "Lazada session saved locally", "active_profile": profile}


@router.get("/session")
async def get_lazada_session_status():
    profiles = await cookie_manager.list_profiles()
    if not COOKIE_FILE.exists():
        return {"exists": False, "cookie_count": 0, "expired_count": 0, "profiles": profiles, "health": session_health.snapshot()}
    try:
        cookies = json.loads(COOKIE_FILE.read_text(encoding="utf-8"))
        now = time.time()
        expired = sum(1 for c in cookies if c.get("expirationDate") and float(c["expirationDate"]) <= now)
        return {
            "exists": True, "cookie_count": len(cookies), "expired_count": expired,
            "status": "paused" if profiles["paused"] else ("expired" if expired == len(cookies) else "active"),
            "profiles": profiles, "health": session_health.snapshot(),
        }
    except Exception:
        return {"exists": True, "cookie_count": 0, "expired_count": 0, "status": "invalid", "profiles": profiles, "health": session_health.snapshot()}


@router.delete("/session")
async def clear_lazada_session():
    await cookie_manager.clear_all()
    session_health.reset()
    return {"success": True}


@router.get("/cookies")
async def list_cookie_profiles():
    return await cookie_manager.list_profiles()


@router.post("/cookies", status_code=201)
async def add_cookie_profile(payload: CookieProfilePayload):
    try:
        profile = await cookie_manager.add_profile(payload.label, payload.cookies, payload.priority)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "profile": profile}


@router.post("/cookies/{profile_id}/activate")
async def activate_cookie_profile(profile_id: int):
    try:
        profile = await cookie_manager.activate(profile_id)
    except ValueError as exc:
        raise HTTPException(status_code=400 if "invalid" in str(exc).lower() else 404, detail=str(exc)) from exc
    reset_lazada_session_alert()
    return {"success": True, "profile": profile}


@router.put("/cookies/priorities")
async def reorder_cookie_profiles(payload: CookiePriorityPayload):
    try:
        await cookie_manager.reorder(payload.profile_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True}


@router.delete("/cookies/{profile_id}")
async def delete_cookie_profile(profile_id: int):
    await cookie_manager.delete(profile_id)
    return {"success": True}
