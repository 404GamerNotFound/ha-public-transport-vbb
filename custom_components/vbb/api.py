"""Helpers for communicating with the transport.rest API."""

from __future__ import annotations

import asyncio
from typing import Any, Mapping

from aiohttp import ClientError, ClientResponseError, ClientSession
import async_timeout

from .const import API_BASES, HEADERS, REQUEST_TIMEOUT


async def async_request_json(
    session: ClientSession,
    path: str,
    params: Mapping[str, Any] | None = None,
) -> Any:
    """Query the transport.rest API trying all configured base URLs."""

    last_error: Exception | None = None

    for base_url in API_BASES:
        url = f"{base_url}{path}"
        try:
            async with async_timeout.timeout(REQUEST_TIMEOUT):
                response = await session.get(url, params=params, headers=HEADERS)
                response.raise_for_status()
                return await response.json()
        except (asyncio.TimeoutError, ClientResponseError, ClientError, ValueError) as err:
            last_error = err
            continue

    if last_error is not None:
        raise last_error

    raise RuntimeError("No API base URLs configured")
