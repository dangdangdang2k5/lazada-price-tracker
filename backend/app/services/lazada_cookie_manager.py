"""Safe management of user-provided Lazada cookie profiles.

Cookie values stay in private JSON files. SQLite holds only metadata, ordering,
and the active profile id so the application never needs to log or expose a
cookie value.
"""

import asyncio
import datetime
import json
import os
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.logging import logger
from app.models.lazada_cookie_profile import LazadaCookieProfile, LazadaCookieState
from app.services.providers.base import ProductScrapedData
from app.services.providers.factory import get_price_provider_for_url


SESSION_EXPIRED = "SESSION_EXPIRED"


@dataclass
class CookieFetchOutcome:
    data: ProductScrapedData
    active_profile_id: Optional[int]
    switched_profile: bool = False
    all_profiles_invalid: bool = False
    notify_all_invalid: bool = False


class LazadaCookieManager:
    """Keeps one active cookie mirrored to the legacy cookie file."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()

    @property
    def legacy_file(self) -> Path:
        return Path(settings.LAZADA_COOKIE_FILE).expanduser()

    @property
    def profiles_dir(self) -> Path:
        configured = settings.LAZADA_COOKIE_PROFILES_DIR.strip()
        return Path(configured).expanduser() if configured else self.legacy_file.parent / "profiles"

    async def bootstrap(self) -> None:
        """Import the legacy single cookie file once without changing its data."""
        async with self._lock:
            async with AsyncSessionLocal() as session:
                profiles = list((await session.scalars(
                    select(LazadaCookieProfile).order_by(LazadaCookieProfile.priority, LazadaCookieProfile.id)
                )).all())
                state = await self._get_state(session)
                if not profiles and self.legacy_file.is_file() and self._cookie_file_is_valid(self.legacy_file):
                    profile = LazadaCookieProfile(
                        label="Cookie 1",
                        priority=1,
                        cookie_file=str(self.legacy_file),
                        status="UNKNOWN",
                    )
                    session.add(profile)
                    await session.flush()
                    state.active_profile_id = profile.id
                    state.paused = False
                    await session.commit()
                    return

                if profiles and not state.active_profile_id:
                    first = next((p for p in profiles if p.status != "EXPIRED" and self._cookie_file_is_valid(Path(p.cookie_file))), None)
                    if first:
                        await self._activate_in_session(session, state, first)
                # Persist a newly-created singleton state even when there is
                # no legacy cookie yet.
                await session.commit()

    async def list_profiles(self) -> dict[str, Any]:
        await self.bootstrap()
        async with AsyncSessionLocal() as session:
            state = await self._get_state(session)
            profiles = list((await session.scalars(
                select(LazadaCookieProfile).order_by(LazadaCookieProfile.priority, LazadaCookieProfile.id)
            )).all())
            return {
                "active_profile_id": state.active_profile_id,
                "paused": state.paused,
                "profiles": [self._public_profile(profile, state.active_profile_id) for profile in profiles],
            }

    async def add_profile(self, label: str, cookies: list[dict[str, Any]], priority: Optional[int] = None) -> dict[str, Any]:
        self.validate_cookies(cookies)
        clean_label = (label or "").strip()[:100] or "Cookie mới"
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        profile_file = self.profiles_dir / f"lazada-cookie-{uuid.uuid4().hex}.json"

        async with self._lock:
            async with AsyncSessionLocal() as session:
                state = await self._get_state(session)
                max_priority = await session.scalar(select(LazadaCookieProfile.priority).order_by(LazadaCookieProfile.priority.desc()).limit(1))
                profile = LazadaCookieProfile(
                    label=clean_label,
                    priority=max(1, int(priority)) if priority else (max_priority or 0) + 1,
                    cookie_file=str(profile_file),
                    status="UNKNOWN",
                )
                session.add(profile)
                await session.flush()
                try:
                    self._write_cookie_file(profile_file, cookies)
                except OSError:
                    await session.rollback()
                    raise
                if not state.active_profile_id:
                    await self._activate_in_session(session, state, profile)
                await session.commit()
                return self._public_profile(profile, state.active_profile_id)

    async def replace_active(self, cookies: list[dict[str, Any]], label: Optional[str] = None) -> dict[str, Any]:
        """Compatibility path for the legacy single-session endpoint/upload."""
        self.validate_cookies(cookies)
        await self.bootstrap()
        async with self._lock:
            async with AsyncSessionLocal() as session:
                state = await self._get_state(session)
                profile = await session.get(LazadaCookieProfile, state.active_profile_id) if state.active_profile_id else None
                if not profile:
                    # The first uploaded session becomes Cookie 1.
                    profile = LazadaCookieProfile(label=(label or "Cookie 1")[:100], priority=1, cookie_file=str(self.legacy_file))
                    session.add(profile)
                    await session.flush()
                    state.active_profile_id = profile.id
                if label and label.strip():
                    profile.label = label.strip()[:100]
                self._write_cookie_file(Path(profile.cookie_file), cookies)
                profile.status = "UNKNOWN"
                profile.last_error_code = None
                profile.last_checked_at = datetime.datetime.utcnow()
                state.paused = False
                state.all_invalid_notified = False
                await self._mirror_to_legacy(profile)
                await session.commit()
                return self._public_profile(profile, state.active_profile_id)

    async def activate(self, profile_id: int) -> dict[str, Any]:
        await self.bootstrap()
        async with self._lock:
            async with AsyncSessionLocal() as session:
                state = await self._get_state(session)
                profile = await session.get(LazadaCookieProfile, profile_id)
                if not profile:
                    raise ValueError("Cookie profile not found")
                if not self._cookie_file_is_valid(Path(profile.cookie_file)):
                    raise ValueError("Cookie file is missing or invalid")
                await self._activate_in_session(session, state, profile)
                await session.commit()
                return self._public_profile(profile, state.active_profile_id)

    async def reorder(self, profile_ids: list[int]) -> None:
        await self.bootstrap()
        async with self._lock:
            async with AsyncSessionLocal() as session:
                profiles = list((await session.scalars(select(LazadaCookieProfile))).all())
                by_id = {profile.id: profile for profile in profiles}
                if set(profile_ids) != set(by_id):
                    raise ValueError("Priority list must contain every cookie profile exactly once")
                for priority, profile_id in enumerate(profile_ids, start=1):
                    by_id[profile_id].priority = priority
                await session.commit()

    async def delete(self, profile_id: int) -> None:
        await self.bootstrap()
        async with self._lock:
            async with AsyncSessionLocal() as session:
                state = await self._get_state(session)
                profile = await session.get(LazadaCookieProfile, profile_id)
                if not profile:
                    return
                was_active = state.active_profile_id == profile.id
                cookie_file = Path(profile.cookie_file)
                await session.delete(profile)
                await session.flush()
                if was_active:
                    next_profile = await self._next_profile(session, excluded_profile_id=profile_id)
                    if next_profile:
                        await self._activate_in_session(session, state, next_profile)
                    else:
                        state.active_profile_id = None
                        state.paused = True
                        self._remove_legacy_file()
                await session.commit()
                if cookie_file != self.legacy_file:
                    cookie_file.unlink(missing_ok=True)

    async def clear_all(self) -> None:
        """Legacy delete action: remove every stored profile and the mirror."""
        async with self._lock:
            async with AsyncSessionLocal() as session:
                profiles = list((await session.scalars(select(LazadaCookieProfile))).all())
                for profile in profiles:
                    file_path = Path(profile.cookie_file)
                    if file_path != self.legacy_file:
                        file_path.unlink(missing_ok=True)
                    await session.delete(profile)
                state = await self._get_state(session)
                state.active_profile_id = None
                state.paused = True
                state.all_invalid_notified = False
                await session.commit()
        self._remove_legacy_file()

    async def is_paused(self) -> bool:
        await self.bootstrap()
        async with AsyncSessionLocal() as session:
            return (await self._get_state(session)).paused

    async def fetch_product(self, url: str, use_cache: bool = True) -> CookieFetchOutcome:
        """Fetch using the active profile and only fail over on SESSION_EXPIRED."""
        await self.bootstrap()
        switched = False
        attempts = 0
        while True:
            async with AsyncSessionLocal() as session:
                state = await self._get_state(session)
                active_profile_id = state.active_profile_id
                paused = state.paused
            if paused or not active_profile_id:
                return CookieFetchOutcome(
                    data=ProductScrapedData(name="Lazada product", price=0, url=url, success=False,
                                             error_code=SESSION_EXPIRED,
                                             error_message="No valid Lazada cookie profile is available"),
                    active_profile_id=active_profile_id,
                    all_profiles_invalid=True,
                )

            provider = get_price_provider_for_url(url)
            data = await provider.get_product_info(url, use_cache=use_cache if attempts == 0 else False)
            if data.success and data.price > 0:
                await self.record_success(active_profile_id)
                return CookieFetchOutcome(data=data, active_profile_id=active_profile_id, switched_profile=switched)

            # Captcha, 429/network failure, server errors and extraction errors
            # never select another profile. They receive normal scheduler backoff.
            if data.error_code != SESSION_EXPIRED:
                await self.record_non_session_result(active_profile_id, data.error_code)
                return CookieFetchOutcome(data=data, active_profile_id=active_profile_id, switched_profile=switched)

            outcome = await self.fail_active_and_select_next(active_profile_id)
            if not outcome[0]:
                return CookieFetchOutcome(
                    data=ProductScrapedData(name=data.name, price=0, url=url, success=False,
                                             error_code=SESSION_EXPIRED,
                                             error_message="All Lazada cookie profiles require renewal"),
                    active_profile_id=None,
                    switched_profile=switched,
                    all_profiles_invalid=True,
                    notify_all_invalid=outcome[1],
                )
            switched = True
            attempts += 1

    async def record_success(self, profile_id: Optional[int]) -> None:
        if not profile_id:
            return
        async with AsyncSessionLocal() as session:
            state = await self._get_state(session)
            profile = await session.get(LazadaCookieProfile, profile_id)
            if profile:
                profile.status = "VALID"
                profile.last_error_code = None
                profile.last_checked_at = datetime.datetime.utcnow()
                profile.last_verified_at = datetime.datetime.utcnow()
            state.paused = False
            state.all_invalid_notified = False
            await session.commit()

    async def record_non_session_result(self, profile_id: Optional[int], error_code: Optional[str]) -> None:
        if not profile_id:
            return
        async with AsyncSessionLocal() as session:
            profile = await session.get(LazadaCookieProfile, profile_id)
            if profile:
                # Preserve VALID/UNKNOWN: this is not proof the session expired.
                profile.last_error_code = error_code
                profile.last_checked_at = datetime.datetime.utcnow()
                await session.commit()

    async def fail_active_and_select_next(self, profile_id: int) -> tuple[bool, bool]:
        """Expire the current profile and atomically choose the next priority."""
        async with self._lock:
            async with AsyncSessionLocal() as session:
                state = await self._get_state(session)
                profile = await session.get(LazadaCookieProfile, profile_id)
                if profile:
                    profile.status = "EXPIRED"
                    profile.last_error_code = SESSION_EXPIRED
                    profile.last_checked_at = datetime.datetime.utcnow()
                next_profile = await self._next_profile(session, excluded_profile_id=profile_id)
                if next_profile:
                    await self._activate_in_session(session, state, next_profile)
                    await session.commit()
                    logger.info("[COOKIE PROFILES] Selected the next configured Lazada cookie profile.")
                    return True, False
                state.active_profile_id = None
                state.paused = True
                should_notify = not state.all_invalid_notified
                state.all_invalid_notified = True
                await session.commit()
                self._remove_legacy_file()
                logger.warning("[COOKIE PROFILES] No valid Lazada cookie profile remains; session requests paused.")
                return False, should_notify

    async def _get_state(self, session) -> LazadaCookieState:
        state = await session.get(LazadaCookieState, 1)
        if not state:
            state = LazadaCookieState(id=1)
            session.add(state)
            await session.flush()
        return state

    async def _next_profile(self, session, excluded_profile_id: Optional[int] = None) -> Optional[LazadaCookieProfile]:
        profiles = list((await session.scalars(
            select(LazadaCookieProfile).order_by(LazadaCookieProfile.priority, LazadaCookieProfile.id)
        )).all())
        for profile in profiles:
            if profile.id != excluded_profile_id and profile.status != "EXPIRED" and self._cookie_file_is_valid(Path(profile.cookie_file)):
                return profile
        return None

    async def _activate_in_session(self, session, state: LazadaCookieState, profile: LazadaCookieProfile) -> None:
        if not self._cookie_file_is_valid(Path(profile.cookie_file)):
            raise ValueError("Cookie file is missing or invalid")
        await self._mirror_to_legacy(profile)
        state.active_profile_id = profile.id
        state.paused = False
        state.all_invalid_notified = False
        profile.last_error_code = None
        profile.last_checked_at = datetime.datetime.utcnow()

    async def _mirror_to_legacy(self, profile: LazadaCookieProfile) -> None:
        source = Path(profile.cookie_file)
        if source == self.legacy_file:
            return
        self.legacy_file.parent.mkdir(parents=True, exist_ok=True)
        temp = self.legacy_file.with_suffix(self.legacy_file.suffix + ".tmp")
        shutil.copyfile(source, temp)
        self._secure_file(temp)
        temp.replace(self.legacy_file)
        self._secure_file(self.legacy_file)

    @staticmethod
    def validate_cookies(cookies: list[dict[str, Any]]) -> None:
        if not isinstance(cookies, list) or not cookies:
            raise ValueError("Cookie list is empty")
        if len(cookies) > 2_000:
            raise ValueError("Cookie list is too large")
        for cookie in cookies:
            if not isinstance(cookie, dict) or not str(cookie.get("name", "")).strip() or not isinstance(cookie.get("value"), str):
                raise ValueError("Each cookie needs a name and value")

    def _write_cookie_file(self, path: Path, cookies: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8")
        self._secure_file(temp)
        temp.replace(path)
        self._secure_file(path)

    @staticmethod
    def _secure_file(path: Path) -> None:
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass

    def _remove_legacy_file(self) -> None:
        self.legacy_file.unlink(missing_ok=True)

    @staticmethod
    def _cookie_file_is_valid(path: Path) -> bool:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return isinstance(payload, list) and bool(payload)
        except (OSError, json.JSONDecodeError):
            return False

    @staticmethod
    def _public_profile(profile: LazadaCookieProfile, active_profile_id: Optional[int]) -> dict[str, Any]:
        return {
            "id": profile.id,
            "label": profile.label,
            "priority": profile.priority,
            "status": profile.status,
            "active": profile.id == active_profile_id,
            "last_error_code": profile.last_error_code,
            "last_verified_at": profile.last_verified_at.isoformat() if profile.last_verified_at else None,
            "last_checked_at": profile.last_checked_at.isoformat() if profile.last_checked_at else None,
        }


cookie_manager = LazadaCookieManager()
