from __future__ import annotations

import base64
import hashlib
import os
import struct
from collections.abc import Callable, Generator

from argon2.low_level import Type, hash_secret_raw
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

MAGIC = b"HAZEDROP"
VERSION = 0x02
CHUNK_SIZE = 64 * 1024  # 64 KB plaintext


def derive_key(password: str, salt: bytes) -> bytes:
    return hash_secret_raw(
        secret=password.encode(),
        salt=salt,
        time_cost=3,
        memory_cost=65536,
        parallelism=2,
        hash_len=32,
        type=Type.ID,
    )


def hash_password_for_auth(password: str) -> str:
    return hashlib.sha256(f"hazedrop-v2:{password}".encode()).hexdigest()


def generate_key() -> bytes:
    return os.urandom(32)


def generate_salt() -> bytes:
    return os.urandom(32)


def encrypt_file_chunked(
    filepath: str,
    key: bytes,
    salt: bytes | None = None,
    on_progress: Callable[[int, int], None] | None = None,
) -> Generator[bytes, None, None]:
    filename = os.path.basename(filepath)
    filesize = os.path.getsize(filepath)
    filename_bytes = filename.encode("utf-8")

    flags = 0x01 if salt is not None else 0x00

    header = MAGIC
    header += bytes([VERSION, flags])
    if salt is not None:
        header += salt
    header += struct.pack(">H", len(filename_bytes))
    header += filename_bytes
    header += struct.pack(">Q", filesize)
    yield header

    cipher = ChaCha20Poly1305(key)
    processed = 0

    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            nonce = os.urandom(12)
            ciphertext = cipher.encrypt(nonce, chunk, None)
            enc_len = len(ciphertext)
            yield struct.pack(">I", enc_len) + nonce + ciphertext
            processed += len(chunk)
            if on_progress:
                on_progress(processed, filesize)


def decrypt_file_chunked(data: bytes, key: bytes) -> tuple[str, bytes]:
    offset = 0

    if data[offset : offset + 8] != MAGIC:
        raise ValueError("Invalid HazeDrop file")
    offset += 8

    version = data[offset]
    if version != VERSION:
        raise ValueError(f"Unsupported version: {version}")
    offset += 1

    flags = data[offset]
    offset += 1
    has_password = bool(flags & 0x01)

    if has_password:
        offset += 32  # skip salt — caller already used it for derive_key

    filename_len = struct.unpack(">H", data[offset : offset + 2])[0]
    offset += 2
    filename = data[offset : offset + filename_len].decode("utf-8")
    offset += filename_len

    _orig_size = struct.unpack(">Q", data[offset : offset + 8])[0]
    offset += 8

    cipher = ChaCha20Poly1305(key)
    plaintext_parts = []

    while offset < len(data):
        enc_len = struct.unpack(">I", data[offset : offset + 4])[0]
        offset += 4
        nonce = data[offset : offset + 12]
        offset += 12
        ciphertext = data[offset : offset + enc_len]
        offset += enc_len
        plaintext_parts.append(cipher.decrypt(nonce, ciphertext, None))

    return filename, b"".join(plaintext_parts)


def compute_file_hash(filepath: str) -> str:
    """Returns SHA-256 hex digest of the file at filepath."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_share_url(
    onion_address: str,
    key: bytes | None,
    password_protected: bool,
    file_hash: str | None = None,
) -> str:
    base = f"http://{onion_address}"
    if password_protected or key is None:
        return base
    base64key = base64.urlsafe_b64encode(key).rstrip(b"=").decode()
    if file_hash is not None:
        fragment = f"{base64key}:{file_hash[:16]}"
    else:
        fragment = base64key
    return f"{base}#{fragment}"


def extract_key_from_url(url: str) -> bytes | None:
    if "#" not in url:
        return None
    fragment = url.split("#", 1)[1]
    if not fragment:
        return None
    # If fragment contains hash suffix, strip it
    key_part = fragment.split(":", 1)[0] if ":" in fragment else fragment
    padding = 4 - len(key_part) % 4
    if padding != 4:
        key_part += "=" * padding
    return base64.urlsafe_b64decode(key_part)


def extract_hash_from_url(url: str) -> str | None:
    """Returns the short hash (16 chars) embedded in the URL fragment, or None."""
    if "#" not in url:
        return None
    fragment = url.split("#", 1)[1]
    if ":" not in fragment:
        return None
    parts = fragment.split(":", 1)
    return parts[1] if len(parts) > 1 and parts[1] else None
