import ctypes
import gc
import os
import signal
import sys
from typing import Callable


def zero_bytes(data: bytearray) -> None:
    ctypes.memset(id(data) + (2 * ctypes.sizeof(ctypes.c_ssize_t)), 0, len(data))


def secure_delete_key(key_ref: list) -> None:
    key = key_ref[0]
    if key is None:
        return
    try:
        # bytes object: ob_refcnt + ob_type + ob_hash + ob_size = offset to data
        offset = ctypes.sizeof(ctypes.c_ssize_t) * 2 + ctypes.sizeof(ctypes.c_void_p) + ctypes.sizeof(ctypes.c_ssize_t)
        ctypes.memset(id(key) + offset, 0, len(key))
    except Exception:
        pass
    key_ref[0] = None


def panic(session_keys: list) -> None:
    for key in session_keys:
        if key is None:
            continue
        try:
            if isinstance(key, bytearray):
                zero_bytes(key)
            elif isinstance(key, bytes):
                offset = (ctypes.sizeof(ctypes.c_ssize_t) * 2
                          + ctypes.sizeof(ctypes.c_void_p)
                          + ctypes.sizeof(ctypes.c_ssize_t))
                ctypes.memset(id(key) + offset, 0, len(key))
        except Exception:
            pass
    gc.collect()
    os._exit(0)


def register_sigquit_panic(keys_getter: Callable[[], list]) -> None:
    def _handler(signum, frame):
        panic(keys_getter())

    if sys.platform != "win32":
        signal.signal(signal.SIGQUIT, _handler)
