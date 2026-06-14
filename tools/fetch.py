# tools/fetch.py
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse, urljoin

import httpx
import trafilatura

from schemas import DocumentText

_BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local / cloud metadata
    ipaddress.ip_network("100.64.0.0/10"),   # carrier-grade NAT
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def _check_url(url: str) -> None:
    """Raise ValueError if the URL is disallowed (non-http/s, private/internal IP)."""
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            f"Scheme not allowed: '{parsed.scheme}'. Only http and https are permitted."
        )

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL has no hostname.")

    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise ValueError(f"Cannot resolve hostname '{hostname}': {exc}") from exc

    for info in infos:
        addr_str = info[4][0]
        try:
            ip = ipaddress.ip_address(addr_str)
        except ValueError:
            continue

        if ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
            raise ValueError(
                "Requests to internal/reserved addresses are not allowed."
            )

        for network in _BLOCKED_NETWORKS:
            try:
                if ip in network:
                    raise ValueError(
                        "Requests to internal/reserved addresses are not allowed."
                    )
            except TypeError:
                continue  # mixed IPv4/IPv6 comparison


MAX_RESPONSE_BYTES = 2 * 1024 * 1024  # 2 MB
MAX_TEXT_CHARS = 100_000
TIMEOUT_SECONDS = 10.0


async def _follow_redirects(
    client: httpx.AsyncClient, url: str, depth: int
) -> httpx.Response:
    if depth > 5:
        raise ValueError("Too many redirects.")
    _check_url(url)  # Re-validate after every redirect
    response = await client.get(url)
    if response.is_redirect:
        location = response.headers.get("location", "")
        if not location:
            raise ValueError("Redirect with no Location header.")
        location = urljoin(url, location)
        return await _follow_redirects(client, location, depth + 1)
    response.raise_for_status()
    return response


async def fetch_document(url: str) -> DocumentText:
    """Fetch a public contract URL and return cleaned readable text.

    SSRF-hardened: private IPs, metadata endpoints, and redirect-to-internal are blocked.
    Rate-limited per authenticated identity (10 requests/hour by default).
    """
    from auth import check_rate_limit, current_identity  # late import avoids circular

    identity = current_identity.get()
    if identity and not check_rate_limit(identity):
        raise PermissionError("Rate limit exceeded. Please try again later.")

    _check_url(url)

    async with httpx.AsyncClient(
        timeout=TIMEOUT_SECONDS,
        follow_redirects=False,
    ) as client:
        response = await _follow_redirects(client, url, depth=0)

    raw = response.content
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError(f"Response too large (>{MAX_RESPONSE_BYTES // 1024 // 1024} MB).")

    extracted = trafilatura.extract(response.text) or response.text
    if len(extracted) > MAX_TEXT_CHARS:
        extracted = extracted[:MAX_TEXT_CHARS]

    return DocumentText(
        text=extracted,
        char_count=len(extracted),
        source_url=url,
    )
