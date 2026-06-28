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


from unittest.mock import AsyncMock, MagicMock
from tools.fetch import fetch_document
from schemas import DocumentText


class _FakeStream:
    """Stand-in for the async context manager returned by httpx's client.stream()."""

    def __init__(self, body: bytes, is_redirect: bool = False, location: str = ""):
        self._body = body
        self.is_redirect = is_redirect
        self.headers = {"location": location} if location else {}

    def raise_for_status(self):
        return None

    async def aiter_bytes(self):
        yield self._body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _fake_client(stream):
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.stream = MagicMock(return_value=stream)
    return client


@pytest.mark.asyncio
async def test_fetch_document_returns_document_text():
    html = b"<html><body><p>This is the contract text for testing purposes only.</p></body></html>"

    with patch("tools.fetch._check_url", return_value="93.184.216.34"), \
         patch("tools.fetch.httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value = _fake_client(_FakeStream(html))
        result = await fetch_document("https://example.com/tos")

    assert isinstance(result, DocumentText)
    assert result.source_url == "https://example.com/tos"
    assert result.char_count == len(result.text)
    assert result.char_count > 0


@pytest.mark.asyncio
async def test_fetch_document_aborts_oversized_response():
    # A single chunk larger than the 2 MB cap must be rejected.
    from tools.fetch import MAX_RESPONSE_BYTES

    oversized = b"x" * (MAX_RESPONSE_BYTES + 1)

    with patch("tools.fetch._check_url", return_value="93.184.216.34"), \
         patch("tools.fetch.httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value = _fake_client(_FakeStream(oversized))
        with pytest.raises(ValueError, match="too large"):
            await fetch_document("https://example.com/huge")


@pytest.mark.asyncio
async def test_fetch_document_rejects_private_url():
    with pytest.raises(ValueError, match="internal"):
        with patch("tools.fetch.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("10.0.0.1", 0))]
            await fetch_document("http://internal.corp/contract")


