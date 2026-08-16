"""Shared expiry-duration parsing for the GUI and the CLI.

Canonical tokens are the international ``s`` / ``m`` / ``h`` / ``d``.
Turkish aliases are accepted where they are unambiguous (``sn``, ``dk``,
``sa``, ``g``) — note that bare ``s`` always means *seconds* and bare ``d``
always means *days*, in every language, so that a link never expires a
thousand times sooner (or later) than intended.
"""

from __future__ import annotations

import re

_UNITS: dict[str, int] = {
    "s": 1,        "sn": 1,      "sec": 1,     "saniye": 1,
    "m": 60,       "dk": 60,     "min": 60,    "dakika": 60,
    "h": 3600,     "sa": 3600,   "hr": 3600,   "saat": 3600,
    "d": 86400,    "g": 86400,   "day": 86400, "gun": 86400,
}

_TOKEN_RE = re.compile(r"(\d+)\s*([a-zçğıöşü]*)")

MAX_SECONDS = 30 * 86400  # 30 days — beyond this an "ephemeral" drop is a lie


def parse_duration(value: str | None) -> int | None:
    """Parse ``10m``, ``1h30m``, ``90`` (bare = seconds) into seconds.

    Returns ``None`` for empty input. Raises ``ValueError`` with a short,
    user-facing message for anything unparseable or out of range.
    """
    if value is None:
        return None

    raw = value.strip().lower().replace(" ", "")
    if not raw:
        return None

    matches = _TOKEN_RE.findall(raw)
    # Reject leftovers like "10mx" or "abc" that the token scan skipped over.
    if not matches or "".join(n + u for n, u in matches) != raw:
        raise ValueError(value)

    total = 0
    for number, unit in matches:
        if unit == "":
            total += int(number)  # bare number = seconds
        elif unit in _UNITS:
            total += int(number) * _UNITS[unit]
        else:
            raise ValueError(value)

    if total <= 0 or total > MAX_SECONDS:
        raise ValueError(value)
    return total


def format_duration(seconds: int) -> str:
    """Render seconds back as a compact ``1h30m`` style string."""
    parts: list[str] = []
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60), ("s", 1)):
        if seconds >= size:
            count, seconds = divmod(seconds, size)
            parts.append(f"{count}{unit}")
    return "".join(parts) or "0s"
