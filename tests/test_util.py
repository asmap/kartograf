from kartograf.util import format_pfx, is_valid_pfx, get_root_network

def test_valid_ipv4_network():
    pfx = "192.144.11.0/24"
    assert format_pfx(pfx) == pfx


def test_valid_ipv4_addr():
    pfx = "192.144.11.0"
    assert format_pfx(pfx) == pfx


def test_valid_ipv6_network():
    pfx = "2001:db8::/64"
    assert format_pfx(pfx) == pfx


def test_valid_ipv6_addr():
    pfx = "2001:db8::1"
    assert format_pfx(pfx) == pfx


def test_invalid_ip_network():
    pfx = "192.1/asdf"
    assert format_pfx(pfx) is None


def test_invalid_input():
    pfx = "no.slash"
    assert format_pfx(pfx) is None


def test_private_network():
    pfx = "0.128.0.0/24"
    assert format_pfx(pfx) == pfx


def test_ipv4_prefix_with_leading_zeros():
    pfx = "010.10.00.00/16"
    assert format_pfx(pfx) is None
    assert not is_valid_pfx(pfx)


def test_ipv6_prefix_with_leading_zeros():
    pfx = "001:db8::0/24"
    assert format_pfx(pfx) is None
    assert not is_valid_pfx(pfx)


def test_get_root_network():
    ipv4 = "192.144.11.0/24"
    assert get_root_network(ipv4) == 192
    ipv6 = "2001:db8::/64"
    assert get_root_network(ipv6) == int("2001", 16)
    invalid = "not.a.network"
    # TODO: use pytest
    try:
        get_root_network(invalid)
    except ValueError:
        assert True
    else:
        assert False
