from __future__ import annotations

import asyncio
import hashlib
import json
import os
from collections.abc import Callable

import aiohttp

from hazedrop.core.crypto import derive_key, decrypt_file_chunked, extract_key_from_url, extract_hash_from_url


async def fetch_info(onion_url: str, socks_port: int) -> dict:
    if not onion_url.startswith("http://") and not onion_url.startswith("https://"):
        onion_url = f"http://{onion_url}"
    base = onion_url.split("#")[0].rstrip("/")
    proxy_url = f"socks5://127.0.0.1:{socks_port}"

    connector = aiohttp.TCPConnector()
    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(
                f"{base}/info",
                proxy=proxy_url,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                resp.raise_for_status()
                return await resp.json(content_type=None)
    except aiohttp.ClientConnectorError as e:
        raise ConnectionError("Cannot connect via Tor proxy. Check that Tor is running.") from e
    except asyncio.TimeoutError as e:
        raise TimeoutError("Connection timed out. The sender may be offline.") from e
    except aiohttp.ClientError as e:
        raise aiohttp.ClientError(f"Network error: {e}") from e


async def download_and_decrypt(
    onion_address: str,
    output_dir: str,
    socks_port: int,
    password: str | None = None,
    key_from_url: bytes | None = None,
    on_progress: Callable[[int, int], None] | None = None,
    on_info: Callable[[dict], None] | None = None,
) -> str:
    if not onion_address.startswith("http://") and not onion_address.startswith("https://"):
        onion_address = f"http://{onion_address}"
    base = onion_address.split("#")[0].rstrip("/")
    proxy_url = f"socks5://127.0.0.1:{socks_port}"

    if key_from_url is None:
        key_from_url = extract_key_from_url(onion_address)

    try:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{base}/info",
                    proxy=proxy_url,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    resp.raise_for_status()
                    info = await resp.json(content_type=None)
            except aiohttp.ClientConnectorError as e:
                raise ConnectionError("Cannot connect via Tor proxy. Check that Tor is running.") from e
            except asyncio.TimeoutError as e:
                raise TimeoutError("Connection timed out. The sender may be offline.") from e
            except aiohttp.ClientError as e:
                raise aiohttp.ClientError(f"Network error: {e}") from e

            if on_info:
                on_info(info)

            post_body: dict = {}
            if info.get("password_required") and password:
                post_body["password"] = password

            try:
                async with session.post(
                    f"{base}/download",
                    json=post_body,
                    proxy=proxy_url,
                    timeout=aiohttp.ClientTimeout(total=3600),
                ) as resp:
                    if resp.status == 401:
                        raise PermissionError("Wrong password or authentication failed")
                    if resp.status == 410:
                        raise FileNotFoundError("File no longer available (expired or already downloaded)")
                    resp.raise_for_status()

                    total = int(resp.headers.get("X-HazeDrop-Size", 0))
                    chunks = []
                    received = 0

                    async for chunk in resp.content.iter_chunked(64 * 1024):
                        chunks.append(chunk)
                        received += len(chunk)
                        if on_progress:
                            on_progress(received, total)
            except (PermissionError, FileNotFoundError):
                raise
            except aiohttp.ClientConnectorError as e:
                raise ConnectionError("Cannot connect via Tor proxy. Check that Tor is running.") from e
            except asyncio.TimeoutError as e:
                raise TimeoutError("Connection timed out. The sender may be offline.") from e
            except aiohttp.ClientError as e:
                raise aiohttp.ClientError(f"Network error: {e}") from e
    except (ConnectionError, TimeoutError, PermissionError, FileNotFoundError, aiohttp.ClientError):
        raise
    except Exception:
        raise

    encrypted_data = b"".join(chunks)

    if info.get("password_required"):
        if password is None:
            raise ValueError("Password required but not provided")
        # extract salt from header
        salt = encrypted_data[10:42]  # after MAGIC(8) + VERSION(1) + FLAGS(1)
        key = derive_key(password, salt)
    elif key_from_url is not None:
        key = key_from_url
    else:
        raise ValueError("No key available: provide password or URL with key fragment")

    filename, plaintext = decrypt_file_chunked(encrypted_data, key)

    # Hash verification
    expected = extract_hash_from_url(onion_address)
    if expected:
        actual = hashlib.sha256(plaintext).hexdigest()[:16]
        if actual != expected:
            raise ValueError("File integrity check failed — hash mismatch")

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, filename)
    if os.path.exists(out_path):
        base_name, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(out_path):
            out_path = os.path.join(output_dir, f"{base_name}_{counter}{ext}")
            counter += 1

    with open(out_path, "wb") as f:
        f.write(plaintext)

    return out_path
