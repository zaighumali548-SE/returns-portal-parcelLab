"""Session-backed throttle for order lookup attempts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.contrib.sessions.backends.base import SessionBase
from django.utils import timezone

_SESSION_KEY = "lookup_throttle"
_MAX_FAILURES = 5
_COOLDOWN_SECONDS = 60


@dataclass(frozen=True)
class LookupThrottleStatus:
    is_blocked: bool
    retry_after_seconds: int


def _now() -> datetime:
    return timezone.now()


def _clear_state(session: SessionBase) -> None:
    session.pop(_SESSION_KEY, None)


def _load_state(session: SessionBase) -> tuple[int, int | None]:
    raw_state = session.get(_SESSION_KEY)
    if not isinstance(raw_state, dict):
        return 0, None
    attempts = raw_state.get("attempts", 0)
    blocked_until = raw_state.get("blocked_until")
    normalized_blocked_until = blocked_until if isinstance(blocked_until, int) else None
    return attempts if isinstance(attempts, int) else 0, normalized_blocked_until


def _remaining_seconds(blocked_until_unix: int) -> int:
    remaining = blocked_until_unix - int(_now().timestamp())
    return max(remaining, 0)


def check_lookup_allowed(session: SessionBase) -> LookupThrottleStatus:
    _, blocked_until = _load_state(session)
    if blocked_until is None:
        return LookupThrottleStatus(is_blocked=False, retry_after_seconds=0)

    remaining_seconds = _remaining_seconds(blocked_until)
    if remaining_seconds <= 0:
        _clear_state(session)
        return LookupThrottleStatus(is_blocked=False, retry_after_seconds=0)

    return LookupThrottleStatus(
        is_blocked=True,
        retry_after_seconds=remaining_seconds,
    )


def record_lookup_failure(session: SessionBase) -> LookupThrottleStatus:
    attempts, _ = _load_state(session)
    next_attempts = attempts + 1
    if next_attempts >= _MAX_FAILURES:
        blocked_until = int(
            (_now() + timedelta(seconds=_COOLDOWN_SECONDS)).timestamp()
        )
        session[_SESSION_KEY] = {
            "attempts": next_attempts,
            "blocked_until": blocked_until,
        }
        return LookupThrottleStatus(
            is_blocked=True,
            retry_after_seconds=_COOLDOWN_SECONDS,
        )

    session[_SESSION_KEY] = {
        "attempts": next_attempts,
        "blocked_until": None,
    }
    return LookupThrottleStatus(is_blocked=False, retry_after_seconds=0)


def record_lookup_success(session: SessionBase) -> None:
    _clear_state(session)


def lookup_throttle_message(retry_after_seconds: int) -> str:
    return (
        "Too many failed lookup attempts. "
        f"Please wait {retry_after_seconds} seconds and try again."
    )
