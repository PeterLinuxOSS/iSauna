"""Async network client for the iSauna controller (binary TCP protocol)."""

from __future__ import annotations

import asyncio
import contextlib

from .const import (
    CONNECT_RETRIES,
    CONNECT_RETRY_DELAY,
    HW_VERSION,
    LOGGER,
    READ_COMMAND,
    SOCKET_TIMEOUT,
)
from .protocol import IsaunaProtocolError, decode_response, encode_settings


class IsaunaConnectionError(Exception):
    """Raised when the controller cannot be reached."""


class IsaunaDevice:
    """Talks to a single iSauna controller over the local network."""

    def __init__(
        self,
        host: str,
        port: int,
        tcp_password: str,
    ) -> None:
        """Initialise the client."""
        self._host = host
        self._port = port
        self._tcp_password = tcp_password

    @property
    def host(self) -> str:
        """Return the controller's host."""
        return self._host

    async def _send_tcp(self, payload: bytes, read_reply: bool) -> bytes:
        """Open a short-lived TCP connection, write ``payload`` and optionally read.

        The controller often refuses connections while busy, so the connect step
        is retried a few times before giving up.
        """
        last_err: Exception | None = None
        for attempt in range(1, CONNECT_RETRIES + 1):
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(self._host, self._port),
                    timeout=SOCKET_TIMEOUT,
                )
            except (TimeoutError, OSError) as err:
                last_err = err
                if attempt < CONNECT_RETRIES:
                    LOGGER.debug(
                        "Connect to %s:%s failed (attempt %s/%s): %s",
                        self._host,
                        self._port,
                        attempt,
                        CONNECT_RETRIES,
                        err,
                    )
                    await asyncio.sleep(CONNECT_RETRY_DELAY)
                continue

            try:
                writer.write(payload)
                await writer.drain()
                if not read_reply:
                    return b""
                return await asyncio.wait_for(reader.read(-1), timeout=SOCKET_TIMEOUT)
            except (TimeoutError, OSError) as err:
                raise IsaunaConnectionError(
                    f"I/O error with controller: {err}"
                ) from err
            finally:
                writer.close()
                with contextlib.suppress(OSError):
                    await writer.wait_closed()

        raise IsaunaConnectionError(
            f"cannot connect to {self._host}:{self._port}: {last_err}"
        ) from last_err

    async def async_poll(self) -> dict | None:
        """Read the controller's current state. Returns ``None`` if no new data."""
        raw = await self._send_tcp(
            (READ_COMMAND + self._tcp_password).encode(), read_reply=True
        )
        try:
            return decode_response(raw, HW_VERSION)
        except IsaunaProtocolError as err:
            LOGGER.debug("Discarding undecodable response: %s", err)
            return None

    async def async_apply(self, state: dict) -> None:
        """Push the full state to the controller via the TCP write command."""
        payload = encode_settings(state, self._tcp_password).encode()
        await self._send_tcp(payload, read_reply=False)
