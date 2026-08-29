import pytest

from kartograf.merge import BaseNetworkIndex


def test_base_create():
    '''
    contains returns false for prefixes checked against an empty base index.
    '''
    base = BaseNetworkIndex()
    assert not base.contains("10.10.0.0/16")
    assert not base.contains("2c0f:ff90::/32")


def test_base_update():
    '''
    contains returns true for prefixes that were added to the base index.
    '''
    base = BaseNetworkIndex()
    ipv4_network = "10.10.0.0/16"
    ipv6_network = "2c0f:ff90::/32"
    base.update(ipv4_network, 123)
    base.update(ipv6_network, 123)
    assert base.contains(ipv4_network)
    assert base.contains(ipv6_network)


def test_check_included_subnet():
    '''
    contains returns true for a subnet of a prefix in the base index.
    '''
    base = BaseNetworkIndex()
    base.update("10.10.0.0/16", 123)
    assert base.contains("10.10.0.0/21")


def test_contains_rejects_invalid_prefix():
    base = BaseNetworkIndex()
    with pytest.raises(ValueError):
        base.contains("10.10.0.0/33")
