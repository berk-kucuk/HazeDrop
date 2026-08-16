from __future__ import annotations

import asyncio
import atexit
import os
import random
import shutil
import tempfile
from collections.abc import Callable

import stem.process
from stem.control import Controller


class TorManager:
    def __init__(self):
        self._socks_port: int = random.randint(19050, 19150)
        self._control_port: int = random.randint(19200, 19350)
        self._data_dir: str = tempfile.mkdtemp(prefix="hazedrop_tor_")
        self._process = None
        self._controller: Controller | None = None
        atexit.register(self._sync_cleanup)

    def _sync_cleanup(self) -> None:
        try:
            if self._controller:
                try:
                    self._controller.close()
                except Exception:
                    pass
                self._controller = None
        except Exception:
            pass
        try:
            if self._process:
                try:
                    self._process.terminate()
                except Exception:
                    pass
                self._process = None
        except Exception:
            pass
        try:
            shutil.rmtree(self._data_dir, ignore_errors=True)
        except Exception:
            pass

    @property
    def socks_port(self) -> int:
        return self._socks_port

    @property
    def control_port(self) -> int:
        return self._control_port

    @property
    def is_running(self) -> bool:
        return self._process is not None

    async def start(
        self,
        on_progress: Callable[[str], None] | None = None,
        bridges: list[str] | None = None,
        use_bridges: bool = False,
    ) -> None:
        if self._process is not None:
            return

        # Recreate data dir if a previous stop() cleaned it up
        if not os.path.exists(self._data_dir):
            self._data_dir = tempfile.mkdtemp(prefix="hazedrop_tor_")

        loop = asyncio.get_running_loop()

        def _sync_start():
            def _progress_handler(line: str):
                if on_progress and "Bootstrapped" in line:
                    loop.call_soon_threadsafe(on_progress, line.strip())

            config: dict = {
                "SocksPort": str(self._socks_port),
                "ControlPort": str(self._control_port),
                "DataDirectory": self._data_dir,
                "Log": "notice stdout",
            }

            if use_bridges and bridges:
                config["UseBridges"] = "1"
                config["Bridge"] = bridges

            self._process = stem.process.launch_tor_with_config(
                config=config,
                init_msg_handler=_progress_handler,
                take_ownership=True,
            )
            self._controller = Controller.from_port(port=self._control_port)
            self._controller.authenticate()

        await loop.run_in_executor(None, _sync_start)

    def create_hidden_service(self, local_port: int) -> str:
        assert self._controller is not None, "TorManager not started"
        response = self._controller.create_ephemeral_hidden_service(
            {80: local_port},
            await_publication=True,
            key_type="NEW",
            key_content="ED25519-V3",
        )
        return response.service_id + ".onion"

    async def renew_circuit(self) -> None:
        if self._controller:
            self._controller.signal("NEWNYM")

    async def stop(self) -> None:
        if self._controller:
            try:
                self._controller.close()
            except Exception:
                pass
            self._controller = None
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
            self._process = None
        try:
            shutil.rmtree(self._data_dir, ignore_errors=True)
        except Exception:
            pass
