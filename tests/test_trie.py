import io
from ipaddress import ip_address, ip_network
import pytest
from kartograf.trie import TrieNode, IPTrie


def test_trienode_init():
    node = TrieNode()
    assert node.children == [None, None]
    assert node.asn is None


def test_trienode_slots_prevents_arbitrary_attributes():
    node = TrieNode()
    with pytest.raises(AttributeError):
        node.arbitrary_attr = "value" # pylint: disable=assigning-non-slot


def test_trienode_children_are_independent():
    node = TrieNode()
    node.children[0] = TrieNode()
    assert node.children[1] is None


def test_trienode_asn_can_be_set():
    node = TrieNode()
    node.asn = "AS12345"
    assert node.asn == "AS12345"


def test_insert_overwrite_same_prefix():
    trie = IPTrie()
    trie.insert(ip_network("10.0.0.0/8"), "AS100")
    trie.insert(ip_network("10.0.0.0/8"), "AS200")

    assert trie.lookup(ip_address("10.1.1.1")) == "AS200"


def test_insert_with_strict_false():
    trie = IPTrie()
    trie.insert(ip_network("192.168.1.0/24"), "AS100")

    assert trie.lookup(ip_address("192.168.1.1")) == "AS100"
    assert trie.lookup(ip_address("192.168.1.5")) == "AS100"


def test_insert_invalid_prefix_raises():
    trie = IPTrie()

    with pytest.raises(ValueError):
        trie.insert(ip_network("not.a.network/24"), "AS100")


def test_ipv4_does_not_affect_ipv6():
    '''
    Test that IPv4 and IPv6 are separate roots to the trie.
    '''
    trie = IPTrie()
    trie.insert(ip_network("10.0.0.0/8"), "AS_IPV4")

    assert trie.lookup(ip_address("10.1.1.1")) == "AS_IPV4"
    assert trie.lookup(ip_address("::ffff:10.1.1.1")) is None

    trie.insert(ip_network("::ffff:10.1.1.1"), "AS_IPV6")
    assert trie.lookup(ip_address("::ffff:10.1.1.1")) == "AS_IPV6"


def test_ipv4_lookup():
    '''
    Test IPv4 lookup.
    '''
    trie = IPTrie()
    trie.insert(ip_network("10.0.0.0/8"), "AS100")       # /8
    trie.insert(ip_network("172.16.0.0/12"), "AS200")    # /12
    trie.insert(ip_network("192.168.100.0/24"), "AS300") # /24

    assert trie.lookup(ip_address("10.0.0.1")) == "AS100"
    assert trie.lookup(ip_address("10.255.255.255")) == "AS100"
    assert trie.lookup(ip_address("11.0.0.1")) is None

    assert trie.lookup(ip_address("172.16.0.1")) == "AS200"
    assert trie.lookup(ip_address("172.31.255.255")) == "AS200"
    assert trie.lookup(ip_address("172.32.0.1")) is None

    assert trie.lookup(ip_address("192.168.100.0")) == "AS300"
    assert trie.lookup(ip_address("192.168.100.255")) == "AS300"
    assert trie.lookup(ip_address("192.168.101.0")) is None


def test_ipv6_lookup():
    '''
    Test IPv6 lookup.
    '''
    trie = IPTrie()
    trie.insert(ip_network("2001:db8::/32"), "AS54321")         # /32
    trie.insert(ip_network("2001:db8:1234::/48"), "AS111")      # /48
    trie.insert(ip_network("2001:db8:1234:5678::/64"), "AS222") # /64

    assert trie.lookup(ip_address("2001:db9::1")) is None
    assert trie.lookup(ip_address("2001:db8::1")) == "AS54321"
    assert trie.lookup(ip_address("2001:db8:1234::1")) == "AS111"
    assert trie.lookup(ip_address("2001:db8:1234:5678::1")) == "AS222"


def test_longest_prefix_nested_ipv4():
    '''
    Test IPv4 nested networks.
    '''
    trie = IPTrie()
    trie.insert(ip_network("10.0.0.0/8"), "AS100")
    trie.insert(ip_network("10.1.0.0/16"), "AS200")
    trie.insert(ip_network("10.1.2.0/24"), "AS300")

    assert trie.lookup(ip_address("10.0.0.1")) == "AS100"
    assert trie.lookup(ip_address("10.1.0.1")) == "AS200"
    assert trie.lookup(ip_address("10.1.2.1")) == "AS300"
    assert trie.lookup(ip_address("10.1.2.255")) == "AS300"
    assert trie.lookup(ip_address("10.1.3.1")) == "AS200"
    assert trie.lookup(ip_address("10.2.0.1")) == "AS100"


def test_longest_prefix_nested_ipv6():
    '''
    Test IPv6 nested networks.
    '''
    trie = IPTrie()
    trie.insert(ip_network("2001::/16"), "AS_16")
    trie.insert(ip_network("2001:db8::/32"), "AS_32")
    trie.insert(ip_network("2001:db8:1234::/48"), "AS_48")

    assert trie.lookup(ip_address("2001::1")) == "AS_16"
    assert trie.lookup(ip_address("2001:db8::1")) == "AS_32"
    assert trie.lookup(ip_address("2001:db8:1234::1")) == "AS_48"
    assert trie.lookup(ip_address("2001:db8:1235::1")) == "AS_32"
    assert trie.lookup(ip_address("2001:db9::1")) == "AS_16"


def test_default_route_ipv4():
    '''
    Check that it handles /0 correctly for IPv4.
    '''
    trie = IPTrie()
    trie.insert(ip_network("0.0.0.0/0"), "AS_DEFAULT")

    assert trie.lookup(ip_address("1.2.3.4")) == "AS_DEFAULT"
    assert trie.lookup(ip_address("255.255.255.255")) == "AS_DEFAULT"
    assert trie.lookup(ip_address("0.0.0.0")) == "AS_DEFAULT"


def test_default_route_ipv6():
    '''
    Check that it handles /0 correctly for IPv6.
    '''
    trie = IPTrie()
    trie.insert(ip_network("::/0"), "AS_DEFAULT_V6")

    assert trie.lookup(ip_address("::1")) == "AS_DEFAULT_V6"
    assert trie.lookup(ip_address("2001:db8::1")) == "AS_DEFAULT_V6"
    assert trie.lookup(ip_address("ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff")) == "AS_DEFAULT_V6"


def test_single_host_ipv4():
    '''
    Test a single IPv4 host.
    '''
    trie = IPTrie()
    trie.insert(ip_network("192.168.1.100/32"), "AS_SINGLE")

    assert trie.lookup(ip_address("192.168.1.100")) == "AS_SINGLE"
    assert trie.lookup(ip_address("192.168.1.99")) is None
    assert trie.lookup(ip_address("192.168.1.101")) is None


def test_single_host_ipv6():
    '''
    Test a single IPv6 host.
    '''
    trie = IPTrie()
    trie.insert(ip_network("2001:db8::1/128"), "AS_SINGLE_V6")

    assert trie.lookup(ip_address("2001:db8::1")) == "AS_SINGLE_V6"
    assert trie.lookup(ip_address("2001:db8::2")) is None


def test_from_map_file_basic():
    map_content = """192.168.1.0/24 AS111
10.0.0.0/8 AS222
2001:db8::/32 AS333
"""
    map_file = io.StringIO(map_content)
    trie = IPTrie()
    trie.from_map_file(map_file)

    assert trie.lookup(ip_address("192.168.1.50")) == "AS111"
    assert trie.lookup(ip_address("10.5.5.5")) == "AS222"
    assert trie.lookup(ip_address("2001:db8::1234")) == "AS333"


def test_from_map_file_with_empty_lines():
    map_content = """192.168.0.0/16 AS100

10.0.0.0/8 AS200

"""
    map_file = io.StringIO(map_content)
    trie = IPTrie()
    trie.from_map_file(map_file)

    assert trie.lookup(ip_address("192.168.1.1")) == "AS100"
    assert trie.lookup(ip_address("10.1.1.1")) == "AS200"


def test_from_map_file_invalid_network_raises():
    map_content = """
    192.168.0.0/16 AS100
    not.a.network.0/8 AS200
    """
    map_file = io.StringIO(map_content)
    trie = IPTrie()

    with pytest.raises(ValueError):
        trie.from_map_file(map_file)


def test_from_map_file_invalid_asn_raises():
    map_content = """
    192.168.0.0/16 AS100
    192.169.0.0/8 ASBAD
    """
    map_file = io.StringIO(map_content)
    trie = IPTrie()

    with pytest.raises(ValueError):
        trie.from_map_file(map_file)


def test_from_map_file_with_extra_whitespace():
    map_content = "  192.168.1.0/24   AS100  \n 10.0.0.0/8    AS200 "
    map_file = io.StringIO(map_content)
    trie = IPTrie()
    trie.from_map_file(map_file)

    assert trie.lookup(ip_address("192.168.1.1")) == "AS100"
    assert trie.lookup(ip_address("10.1.1.1")) == "AS200"


def test_from_map_file_empty():
    map_content = ""
    map_file = io.StringIO(map_content)
    trie = IPTrie()
    trie.from_map_file(map_file)

    assert trie.lookup(ip_address("10.0.0.1")) is None


def test_lookup_rejects_int():
    trie = IPTrie()
    trie.insert(ip_network("10.0.0.0/8"), "AS100")

    with pytest.raises(TypeError):
        trie.lookup(167772161)


def test_lookup_rejects_invalid_string():
    trie = IPTrie()
    trie.insert(ip_network("10.0.0.0/8"), "AS100")

    with pytest.raises(TypeError):
        trie.lookup("not.an.ip.address")
