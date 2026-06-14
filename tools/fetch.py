# tools/fetch.py
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse, urlunparse, urljoin

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


def _check_url(url: str) -> str:
    """Validate URL; return the first resolved safe IP to pin the connection to.

    Raises ValueError if the URL is disallowed (bad scheme, unresolvable, private IP).
    Returning the resolved IP lets callers connect to it directly, preventing DNS-rebinding
    TOCTOU: the IP validated here is the IP used for the TCP connection.
    """
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

    first_safe_ip: str | None = None
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

        if first_safe_ip is None:
            first_safe_ip = addr_str

    if first_safe_ip is None:
        raise ValueError("No valid address resolved for hostname.")

    return first_safe_ip


def _build_ip_url(url: str, ip: str) -> tuple[str, str, str | None]:
    """Substitute hostname with resolved IP to pin the TCP connection.

    Returns (ip_url, host_header, sni_hostname):
    - ip_url: URL with hostname replaced by validated IP (what httpx connects to)
    - host_header: original netloc for the HTTP Host header
    - sni_hostname: original hostname for TLS SNI + cert verification (HTTPS only)

    httpcore uses the sni_hostname extension as the server_hostname in ssl.wrap_socket,
    so certificate verification runs against the original domain even though we connect
    to the IP. IPv6 addresses are bracketed per RFC 2732.
    """
    parsed = urlparse(url)
    ip_literal = f"[{ip}]" if ":" in ip else ip
    netloc_with_ip = f"{ip_literal}:{parsed.port}" if parsed.port else ip_literal
    ip_url = urlunparse(parsed._replace(netloc=netloc_with_ip))
    host_header = parsed.netloc
    sni = parsed.hostname if parsed.scheme == "https" else None
    return ip_url, host_header, sni


MAX_RESPONSE_BYTES = 2 * 1024 * 1024  # 2 MB
MAX_TEXT_CHARS = 100_000
TIMEOUT_SECONDS = 10.0


async def _follow_redirects(
    client: httpx.AsyncClient, url: str, depth: int
) -> httpx.Response:
    if depth > 5:
        raise ValueError("Too many redirects.")
    validated_ip = _check_url(url)  # re-validate after every redirect; returns safe IP
    ip_url, host_header, sni = _build_ip_url(url, validated_ip)
    extensions: dict = {"sni_hostname": sni} if sni else {}
    response = await client.get(
        ip_url,
        headers={"Host": host_header},
        extensions=extensions or None,
    )
    if response.is_redirect:
        location = response.headers.get("location", "")
        if not location:
            raise ValueError("Redirect with no Location header.")
        location = urljoin(url, location)  # resolve relative to original URL, not IP URL
        return await _follow_redirects(client, location, depth + 1)
    response.raise_for_status()
    return response


async def fetch_document(url: str, ctx=None) -> DocumentText:
    """Fetch a public contract URL and return cleaned readable text.

    SSRF-hardened: private IPs, metadata endpoints, and redirect-to-internal are blocked.
    Connects to the pre-resolved IP to prevent DNS-rebinding (TOCTOU).
    Rate-limited per authenticated identity (10 requests/hour by default).

    ctx is injected by FastMCP and not exposed in the MCP tool schema.
    """
    from auth import check_rate_limit  # late import avoids circular

    # FastMCP injects ctx with auth info in production; fallback for direct test calls
    identity = ""
    if ctx is not None and ctx.auth is not None:
        identity = ctx.auth.client_id or ctx.auth.claims.get("sub", "")

    if identity and not check_rate_limit(identity):
        raise PermissionError("Rate limit exceeded. Please try again later.")

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
