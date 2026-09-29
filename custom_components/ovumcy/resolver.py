"""Pin a single hostname to a fixed IP, like `curl --resolve`.

Ovumcy's COOKIE_SECURE=true means the auth cookie only survives over HTTPS,
so simply talking to the bare LAN IP over plain HTTP isn't a real option —
the session cookie wouldn't be stored/sent back. This resolver instead lets
the request keep using the real hostname (correct Host header, correct SNI,
cert hostname verification still passes against the wildcard cert) while
forcing the TCP connection itself to a specific IP, bypassing whatever
broke normal DNS resolution.
"""
from __future__ import annotations

import socket

from aiohttp.abc import AbstractResolver, ResolveResult


class StaticHostResolver(AbstractResolver):
    """Resolve one specific hostname to a fixed IP; defer everything else."""

    def __init__(self, pinned_host: str, pinned_ip: str) -> None:
        self._pinned_host = pinned_host
        self._pinned_ip = pinned_ip
        # aiohttp's default resolver, used as a fallback for any other host
        # (there shouldn't be any in normal operation, but this keeps the
        # resolver well-behaved rather than hard-failing on the unexpected).
        from aiohttp.resolver import ThreadedResolver

        self._fallback = ThreadedResolver()

    async def resolve(
        self, host: str, port: int = 0, family: int = socket.AF_INET
    ) -> list[ResolveResult]:
        if host == self._pinned_host:
            return [
                ResolveResult(
                    hostname=host,
                    host=self._pinned_ip,
                    port=port,
                    family=socket.AF_INET,
                    proto=0,
                    flags=0,
                )
            ]
        return await self._fallback.resolve(host, port, family)

    async def close(self) -> None:
        await self._fallback.close()
