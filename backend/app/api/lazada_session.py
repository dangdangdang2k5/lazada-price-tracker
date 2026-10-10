import json
from pathlib import Path
from typing import Any, List

from fastapi import APIRouter, HTTPException
import time
from app.services.product_service import reset_lazada_session_alert
from app.core.config import settings
from pydantic import BaseModel

router = APIRouter(prefix="/lazada/session", tags=["Lazada Session"])
COOKIE_FILE = Path(settings.LAZADA_COOKIE_FILE).expanduser()


class CookiePayload(BaseModel):
    cookies: List[dict[str, Any]]


@router.post("")
async def save_lazada_session(payload: CookiePayload):
    if not payload.cookies:
        raise HTTPException(status_code=400, detail="Cookie list is empty")
    for cookie in payload.cookies:
        if not cookie.get("name") or "value" not in cookie:
            raise HTTPException(status_code=400, detail="Each cookie needs name and value")
    COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
    COOKIE_FILE.write_text(json.dumps(payload.cookies, ensure_ascii=False, indent=2), encoding="utf-8")
    reset_lazada_session_alert()
    return {"success": True, "message": "Lazada session saved locally"}


@router.get("")
async def get_lazada_session_status():
    if not COOKIE_FILE.exists():
        return {"exists": False, "cookie_count": 0, "expired_count": 0}
    try:
        cookies = json.loads(COOKIE_FILE.read_text(encoding="utf-8"))
        now = time.time()
        expired = sum(1 for c in cookies if c.get("expirationDate") and float(c["expirationDate"]) <= now)
        return {"exists": True, "cookie_count": len(cookies), "expired_count": expired,
                "status": "expired" if expired == len(cookies) else "active"}
    except Exception:
        return {"exists": True, "cookie_count": 0, "expired_count": 0, "status": "invalid"}


@router.delete("")
async def clear_lazada_session():
    if COOKIE_FILE.exists():
        COOKIE_FILE.unlink()
    return {"success": True}
