import asyncio
import json
import time
from collections.abc import Callable

from aiohttp import web

from hazedrop.core.crypto import encrypt_file_chunked, hash_password_for_auth
from hazedrop.core.session import DropSession
from hazedrop.core.web_template import HTML


class TorDropServer:
    def __init__(
        self,
        session: DropSession,
        local_port: int,
        on_download_start: Callable | None = None,
        on_download_complete: Callable | None = None,
        on_wrong_password: Callable | None = None,
        on_expired: Callable | None = None,
    ):
        self._session = session
        self._local_port = local_port
        self._on_download_start = on_download_start
        self._on_download_complete = on_download_complete
        self._on_wrong_password = on_wrong_password
        self._on_expired = on_expired
        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None
        self._download_lock = asyncio.Lock()
        self._wrong_pw_attempts = 0

    async def start(self) -> None:
        self._app = web.Application()
        self._app.router.add_get("/", self._handle_index)
        self._app.router.add_get("/health", self._handle_health)
        self._app.router.add_get("/info", self._handle_info)
        self._app.router.add_post("/download", self._handle_download)
        self._app.router.add_post("/web-download", self._handle_web_download)

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "127.0.0.1", self._local_port)
        await site.start()

    async def stop(self) -> None:
        if self._runner:
            await self._runner.cleanup()
            self._runner = None

    async def _handle_index(self, request: web.Request) -> web.Response:
        return web.Response(
            text=HTML,
            content_type="text/html",
            charset="utf-8",
        )

    async def _handle_health(self, request: web.Request) -> web.Response:
        return web.Response(text="ok")

    async def _handle_info(self, request: web.Request) -> web.Response:
        s = self._session
        if s.is_expired:
            if self._on_expired:
                self._on_expired()
            return web.Response(status=410)

        expires_at = None
        if s.expire_seconds is not None:
            expires_at = int(s.created_at + s.expire_seconds)

        body = {
            "filename": s.filename,
            "size": s.filesize,
            "password_required": s.is_password_protected,
            "once": s.once,
            "downloads": s.download_count,
            "expires_at": expires_at,
            "haze_version": "2",
            "file_hash": s.file_hash,
        }
        return web.Response(
            content_type="application/json",
            text=json.dumps(body),
        )

    async def _handle_download(self, request: web.Request) -> web.Response:
        """CLI/GUI protocol — sends encrypted stream."""
        s = self._session

        async with self._download_lock:
            if s.is_expired:
                if self._on_expired:
                    self._on_expired()
                return web.Response(status=410)

            if s.is_password_protected:
                try:
                    body = await request.json()
                    provided = body.get("password", "")
                except Exception:
                    return web.Response(status=401)

                expected = hash_password_for_auth(s.password)
                if hash_password_for_auth(provided) != expected:
                    if self._on_wrong_password:
                        self._on_wrong_password()
                    self._wrong_pw_attempts += 1
                    if self._wrong_pw_attempts >= 3:
                        self._session.force_expire()
                        return web.Response(status=429)
                    return web.Response(status=401)

            if self._on_download_start:
                self._on_download_start()

            response = web.StreamResponse(
                status=200,
                headers={
                    "Content-Type": "application/octet-stream",
                    "Content-Disposition": f'attachment; filename="{s.filename}.hazedrop"',
                    "X-HazeDrop-Filename": s.filename,
                    "X-HazeDrop-Size": str(s.filesize),
                    "X-HazeDrop-Version": "2",
                },
            )
            await response.prepare(request)

            for chunk in encrypt_file_chunked(s.filepath, s.key, s.salt):
                await response.write(chunk)

            await response.write_eof()

            s.download_count += 1
            if self._on_download_complete:
                self._on_download_complete()

            return response

    async def _handle_web_download(self, request: web.Request) -> web.Response:
        """Browser download — serves plaintext file directly."""
        s = self._session

        async with self._download_lock:
            if s.is_expired:
                if self._on_expired:
                    self._on_expired()
                return web.Response(status=410, text="File expired or already downloaded")

            if s.is_password_protected:
                try:
                    body = await request.json()
                    provided = body.get("password", "")
                except Exception:
                    return web.Response(status=401, text="Password required")

                expected = hash_password_for_auth(s.password)
                if hash_password_for_auth(provided) != expected:
                    if self._on_wrong_password:
                        self._on_wrong_password()
                    self._wrong_pw_attempts += 1
                    if self._wrong_pw_attempts >= 3:
                        self._session.force_expire()
                        return web.Response(status=429, text="Too many wrong attempts — link locked")
                    return web.Response(status=401, text="Wrong password")

            if self._on_download_start:
                self._on_download_start()

            response = web.StreamResponse(
                status=200,
                headers={
                    "Content-Type": "application/octet-stream",
                    "Content-Disposition": f'attachment; filename="{s.filename}"',
                    "Content-Length": str(s.filesize),
                    "X-HazeDrop-Filename": s.filename,
                },
            )
            await response.prepare(request)

            with open(s.filepath, "rb") as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    await response.write(chunk)

            await response.write_eof()

            s.download_count += 1
            if self._on_download_complete:
                self._on_download_complete()

            return response
