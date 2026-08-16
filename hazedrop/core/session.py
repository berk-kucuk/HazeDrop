from __future__ import annotations

import time
from dataclasses import dataclass, field

from hazedrop.core.crypto import build_share_url
from hazedrop.secure.memory import secure_delete_key


@dataclass
class DropSession:
    filepath: str
    filename: str
    filesize: int
    password: str | None
    once: bool
    expire_seconds: int | None

    salt: bytes | None
    key: bytes
    created_at: float = field(default_factory=time.time)
    download_count: int = 0
    onion_address: str | None = None
    file_hash: str | None = None
    max_downloads: int = 1

    _key_ref: list = field(default_factory=list, init=False, repr=False)

    def __post_init__(self):
        self._key_ref = [self.key]
        # once=True implies max_downloads=1 if not explicitly overridden
        if self.once and self.max_downloads != 1:
            self.max_downloads = 1

    @property
    def is_password_protected(self) -> bool:
        return self.password is not None

    @property
    def is_expired(self) -> bool:
        # Check once (backward compat)
        if self.once and self.download_count >= 1:
            return True
        # Check max_downloads limit
        if self.max_downloads > 0 and self.download_count >= self.max_downloads:
            return True
        if self.expire_seconds is not None:
            return time.time() - self.created_at >= self.expire_seconds
        return False

    def force_expire(self) -> None:
        """Immediately mark this session as expired."""
        self.expire_seconds = 0
        self.created_at = 0

    @property
    def share_url(self) -> str:
        assert self.onion_address is not None, "onion_address not set yet"
        return build_share_url(self.onion_address, self.key, self.is_password_protected, self.file_hash)

    def zero_key(self) -> None:
        secure_delete_key(self._key_ref)
        self.key = b""
