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
