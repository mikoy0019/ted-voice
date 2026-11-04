"""Enforce offline inference: disable hub/telemetry downloads and refuse outbound connections."""

from __future__ import annotations

import ipaddress
import os
import socket

OFFLINE_ENV = {
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "HF_DATASETS_OFFLINE": "1",
    "HF_HUB_DISABLE_TELEMETRY": "1",
    "HF_HUB_DISABLE_IMPLICIT_TOKEN": "1",
    "DO_NOT_TRACK": "1",
    "DISABLE_TELEMETRY": "1",
}

# Every outbound connection attempt made while the guard is active is recorded here.
blocked_attempts: list[str] = []
_installed = False


class NetworkBlockedError(ConnectionError):
    pass


def _is_local(host) -> bool:
    if host is None:
        return True
    host = str(host)
    if host in ("localhost", ""):
        return True
    try:
        return ipaddress.ip_address(host.split("%")[0]).is_loopback
    except ValueError:
        return False


def apply_offline_env() -> None:
    for k, v in OFFLINE_ENV.items():
        os.environ[k] = v


def install(block: bool = True) -> None:
    """Set offline env vars and (optionally) make any non-loopback connection raise."""
    global _installed
    apply_offline_env()
    if not block or _installed:
        return
    _installed = True

    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_getaddrinfo = socket.getaddrinfo

    def _check(address):
        host = address[0] if isinstance(address, tuple) else address
        if isinstance(address, (str, bytes)):
            return  # AF_UNIX / named pipes
        if not _is_local(host):
            blocked_attempts.append(str(address))
            raise NetworkBlockedError(f"OfflineVoice blocked an outbound connection to {address}")

    def guarded_connect(self, address):
        _check(address)
        return real_connect(self, address)

    def guarded_connect_ex(self, address):
        _check(address)
        return real_connect_ex(self, address)

    def guarded_getaddrinfo(host, *args, **kwargs):
        if not _is_local(host):
            blocked_attempts.append(f"dns:{host}")
            raise NetworkBlockedError(f"OfflineVoice blocked a DNS lookup for {host}")
        return real_getaddrinfo(host, *args, **kwargs)

    socket.socket.connect = guarded_connect
    socket.socket.connect_ex = guarded_connect_ex
    socket.getaddrinfo = guarded_getaddrinfo
