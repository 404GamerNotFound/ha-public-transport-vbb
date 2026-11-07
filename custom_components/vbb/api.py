"""Helpers for communicating with the transport.rest API."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from collections.abc import Mapping

from aiohttp import ClientError, ClientSession

from .const import API_BASES, HEADERS, REQUEST_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class VbbApiError(Exception):
    """Raised when no API base URL returned a usable response."""


async def async_request_json(
    session: ClientSession,
    path: str,
    params: Mapping[str, Any] | None = None,
) -> Any:
    """Query the transport.rest API, trying each configured base URL in turn.

    The response is read inside the ``async with`` block so the connection is
    always released back to the pool, even when the body is invalid.
    """

    last_error: Exception | None = None

    for base_url in API_BASES:
        url = f"{base_url}{path}"
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                async with session.get(url, params=params, headers=HEADERS) as response:
                    response.raise_for_status()
                    return await response.json(content_type=None)
        except (TimeoutError, ClientError, ValueError) as err:
            _LOGGER.debug("VBB request to %s failed: %s", url, err)
            last_error = err

    raise VbbApiError(
        f"All VBB API endpoints failed for {path}: {last_error!r}"
    ) from last_error
