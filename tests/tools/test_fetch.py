# tests/tools/test_fetch.py
import socket
import pytest
from unittest.mock import patch
from tools.fetch import _check_url


def _mock_getaddrinfo(addr):
    """Returns a mock getaddrinfo result for the given IP string."""
    return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", (addr, 0))]


def test_rejects_ftp_scheme():
    with pytest.raises(ValueError, match="Scheme"):
        _check_url("ftp://example.com/contract.pdf")


def test_rejects_file_scheme():
    with pytest.raises(ValueError, match="Scheme"):
        _check_url("file:///etc/passwd")


def test_rejects_no_hostname():
    with pytest.raises(ValueError, match="hostname"):
        _check_url("https:///path")


@patch("tools.fetch.socket.getaddrinfo")
def test_rejects_loopback_ipv4(mock_dns):
    mock_dns.return_value = _mock_getaddrinfo("127.0.0.1")
    with pytest.raises(ValueError, match="internal"):
        _check_url("http://localhost/contract")


@patch("tools.fetch.socket.getaddrinfo")
def test_rejects_private_10_block(mock_dns):
    mock_dns.return_value = _mock_getaddrinfo("10.0.0.1")
    with pytest.raises(ValueError, match="internal"):
        _check_url("http://internal.corp/contract")


@patch("tools.fetch.socket.getaddrinfo")
def test_rejects_private_172_block(mock_dns):
    mock_dns.return_value = _mock_getaddrinfo("172.16.0.1")
    with pytest.raises(ValueError, match="internal"):
        _check_url("http://internal.corp/contract")


@patch("tools.fetch.socket.getaddrinfo")
def test_rejects_private_192_168_block(mock_dns):
    mock_dns.return_value = _mock_getaddrinfo("192.168.1.1")
    with pytest.raises(ValueError, match="internal"):
        _check_url("http://router.local/contract")


@patch("tools.fetch.socket.getaddrinfo")
def test_rejects_cloud_metadata_endpoint(mock_dns):
    # 169.254.169.254 is the AWS/GCP/Azure IMDS endpoint
    mock_dns.return_value = _mock_getaddrinfo("169.254.169.254")
    with pytest.raises(ValueError, match="internal"):
        _check_url("http://169.254.169.254/latest/meta-data/")


@patch("tools.fetch.socket.getaddrinfo")
def test_rejects_link_local(mock_dns):
    mock_dns.return_value = _mock_getaddrinfo("169.254.1.1")
    with pytest.raises(ValueError, match="internal"):
        _check_url("http://link-local.example.com/")


@patch("tools.fetch.socket.getaddrinfo")
def test_allows_public_ipv4(mock_dns):
    mock_dns.return_value = _mock_getaddrinfo("93.184.216.34")  # example.com
    # Should not raise
    _check_url("https://example.com/tos")


def test_rejects_dns_failure():
    with pytest.raises(ValueError, match="resolve"):
        _check_url("https://this-hostname-does-not-exist-xyzxyz.invalid/")


import httpx
from unittest.mock import AsyncMock, MagicMock
from tools.fetch import fetch_document
from schemas import DocumentText


@pytest.mark.asyncio
async def test_fetch_document_returns_document_text():
    html = "<html><body><p>This is the contract text for testing purposes only.</p></body></html>"

    with patch("tools.fetch._check_url", return_value="93.184.216.34"), \
         patch("tools.fetch.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_response = MagicMock()
        mock_response.is_redirect = False
        mock_response.status_code = 200
        mock_response.text = html
        mock_response.content = html.encode()
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await fetch_document("https://example.com/tos")

    assert isinstance(result, DocumentText)
    assert result.source_url == "https://example.com/tos"
    assert result.char_count == len(result.text)
    assert result.char_count > 0


@pytest.mark.asyncio
async def test_fetch_document_rejects_private_url():
    with pytest.raises(ValueError, match="internal"):
        with patch("tools.fetch.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("10.0.0.1", 0))]
            await fetch_document("http://internal.corp/contract")


@pytest.mark.asyncio
async def test_fetch_document_rate_limits():
    mock_ctx = MagicMock()
    mock_ctx.auth = MagicMock()
    mock_ctx.auth.client_id = "test-user-rate-limit-xyz"
    mock_ctx.auth.claims = {"sub": "test-user-rate-limit-xyz"}

    with patch("tools.fetch._check_url", return_value="93.184.216.34"), \
         patch("tools.fetch.httpx.AsyncClient"), \
         patch("auth.check_rate_limit", return_value=False):
        with pytest.raises(PermissionError, match="Rate limit"):
            await fetch_document("https://example.com/tos", ctx=mock_ctx)
