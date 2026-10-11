"""Persistent, evidence-based health state for the Lazada browser session."""

import datetime
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.logging import logger


SESSION_RELATED_ERRORS = {"SESSION_EXPIRED", "ANTI_BOT_CHALLENGE"}


@dataclass(frozen=True)
class SessionHealthUpdate:
    state: str
    failure_count: int
    became_unusable: bool = False
    recovered: bool = False
    counted_failure: bool = False


class LazadaSessionHealth:
    """Track only evidence collected from real product fetches, never HTTP status alone."""

    def __init__(self, path: Path | None = None, failure_threshold: int | None = None) -> None:
        configured_path = settings.LAZADA_SESSION_HEALTH_FILE
        self.path = path or (
            Path(configured_path).expanduser()
            if configured_path
            else Path(settings.LAZADA_COOKIE_FILE).expanduser().with_name("lazada_session_health.json")
        )
        self.failure_threshold = max(1, failure_threshold or settings.LAZADA_SESSION_FAILURE_THRESHOLD)
        self._state: dict[str, Any] = self._load()

    def reset(self) -> None:
        """Reset old failure evidence when the user stores a new cookie export."""
        self._state = self._default_state()
        self._state["last_checked_at"] = self._now()
        self._save()

    def observe_success(self) -> SessionHealthUpdate:
        previous_state = self._state["state"]
        self._state.update({
            "state": "HEALTHY",
            "failure_count": 0,
            "last_checked_at": self._now(),
            "last_verified_at": self._now(),
            "last_failure_code": None,
            "last_failure_message": None,
        })
        self._save()
        return SessionHealthUpdate(
            state="HEALTHY",
            failure_count=0,
            recovered=previous_state == "UNUSABLE",
        )

    def observe_failure(self, error_code: str | None, error_message: str | None = None) -> SessionHealthUpdate:
        """Count only login/captcha evidence; product and network errors do not expire a session."""
        code = error_code or "UNKNOWN"
        counted = code in SESSION_RELATED_ERRORS
        previous_state = self._state["state"]
        failure_count = int(self._state.get("failure_count", 0))
        if counted:
            failure_count += 1

        self._state.update({
            "failure_count": failure_count,
            "last_checked_at": self._now(),
            "last_failure_at": self._now(),
            "last_failure_code": code,
            "last_failure_message": (error_message or "")[:300] or None,
        })
        if counted and failure_count >= self.failure_threshold:
            self._state["state"] = "UNUSABLE"
        elif counted:
            self._state["state"] = "DEGRADED"
        self._save()

        return SessionHealthUpdate(
            state=self._state["state"],
            failure_count=failure_count,
            became_unusable=counted and self._state["state"] == "UNUSABLE" and previous_state != "UNUSABLE",
            counted_failure=counted,
        )

    def snapshot(self) -> dict[str, Any]:
        return {**self._state, "failure_threshold": self.failure_threshold}

    @staticmethod
    def _now() -> str:
        return datetime.datetime.now(datetime.timezone.utc).isoformat()

    @staticmethod
    def _default_state() -> dict[str, Any]:
        return {
            "state": "UNKNOWN",
            "failure_count": 0,
            "last_checked_at": None,
            "last_verified_at": None,
            "last_failure_at": None,
            "last_failure_code": None,
            "last_failure_message": None,
        }

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._default_state()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("health state is not an object")
            return {**self._default_state(), **data}
        except Exception as exc:
            logger.warning(f"[SESSION HEALTH] Could not load health state: {type(exc).__name__}")
            return self._default_state()

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self.path.with_suffix(self.path.suffix + ".tmp")
            temp_path.write_text(json.dumps(self._state, ensure_ascii=False, indent=2), encoding="utf-8")
            temp_path.replace(self.path)
        except OSError as exc:
            # A monitoring helper must never interrupt a price refresh if storage is unavailable.
            logger.error(f"[SESSION HEALTH] Could not persist health state: {type(exc).__name__}")


session_health = LazadaSessionHealth()
