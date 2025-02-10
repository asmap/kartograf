import pytest
from kartograf.util import parse_pfx, is_valid_pfx, get_root_network, rir_from_str


def test_valid_ipv4_network():
    pfx = "192.144.11.0/24"
    assert parse_pfx(pfx) == pfx


def test_valid_ipv4_addr():
    pfx = "192.144.11.0"
    assert parse_pfx(pfx) == pfx


def test_valid_ipv6_network():
    pfx = "2001:db8::/64"
    assert parse_pfx(pfx) == pfx


def test_valid_ipv6_addr():
    pfx = "2001:db8::1"
    assert parse_pfx(pfx) == pfx


def test_invalid_ip_network():
    pfx = "192.1/asdf"
    assert parse_pfx(pfx) is None


def test_invalid_input():
    pfx = "no.slash"
    assert parse_pfx(pfx) is None


def test_invalid_prefixes():
    invalid_prefixes = [
        "not.a.prefix",
        "300.0.0.0/8",       # Invalid IPv4
        "2001:xyz::/32"      # Invalid IPv6
    ]
    for prefix in invalid_prefixes:
        assert is_valid_pfx(prefix) is False


def test_private_network():
    pfx = "0.128.0.0/24"
    assert parse_pfx(pfx) == pfx


def test_ipv4_prefix_with_leading_zeros():
    pfx = "010.10.00.00/16"
    assert parse_pfx(pfx) is None
    assert not is_valid_pfx(pfx)


def test_ipv6_prefix_with_leading_zeros():
    pfx = "001:db8::0/24"
    assert parse_pfx(pfx) is None
    assert not is_valid_pfx(pfx)


def test_get_root_network():
    ipv4 = "192.144.11.0/24"
    assert get_root_network(ipv4) == 192
    ipv6 = "2001:db8::/64"
    assert get_root_network(ipv6) == int("2001", 16)
    invalid = "not.a.network"
    assert get_root_network(invalid) is None


def test_rir_from_string():
    assert rir_from_str("ripe.db.route") == "RIPE"
    assert rir_from_str("ARIN-file") == "ARIN"
    assert rir_from_str("lacnic.db") == "LACNIC"
    assert rir_from_str("afrinic-data") == "AFRINIC"
    assert rir_from_str("apnic.db") == "APNIC"
    with pytest.raises(Exception):
        rir_from_str("invalid")
