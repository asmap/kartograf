from kartograf.bogon import is_bogon_pfx, is_bogon_asn, extract_asn, is_out_of_encoding_range
from kartograf.util import format_pfx

def test_special_asns():
    special_cases = [0, 112, 23456, 65535, 4294967295]
    for asn in special_cases:
        assert is_bogon_asn(asn) is True
        assert is_bogon_asn(f"AS{asn}") is True

def test_documentation_range():
    assert is_bogon_asn(64496) is True
    assert is_bogon_asn(64511) is True
    assert is_bogon_asn(64503) is True

def test_private_use_range():
    assert is_bogon_asn(64512) is True
    assert is_bogon_asn(65534) is True
    assert is_bogon_asn(4200000000) is True
    assert is_bogon_asn(4294967294) is True

def test_valid_asns():
    valid_asns = [13335, 15169, 32934, 16509]  # Cloudflare, Google, Facebook, Amazon
    for asn in valid_asns:
        assert is_bogon_asn(asn) is False
        assert is_bogon_asn(f"AS{asn}") is False

def test_asn_extraction():
    assert extract_asn("AS12345") == 12345
    assert extract_asn("as12345") == 12345
    assert extract_asn(" AS12345 ") == 12345
    assert extract_asn(12345) == 12345

def test_encoding_range():
    assert is_out_of_encoding_range(33521665) is True
    assert is_out_of_encoding_range(33521664) is False
    assert is_out_of_encoding_range(100) is False

def test_bogon_ipv4_prefixes():
    bogon_prefixes = [
        "0.0.0.0/8",          # RFC791
        "10.0.0.0/8",         # RFC1918 Private-Use
        "127.0.0.0/8",        # Loopback
        "169.254.0.0/16",     # Link Local
        "192.168.0.0/16",     # Private-Use
        "224.0.0.0/4",        # Multicast
        "240.0.0.0/4"         # Reserved
    ]
    for prefix in bogon_prefixes:
        assert is_bogon_pfx(prefix) is True

def test_valid_ipv4_prefixes():
    valid_prefixes = [
        "8.8.8.0/24",         # Google DNS
        "1.1.1.0/24",         # Cloudflare
        "104.16.0.0/12",      # Cloudflare range
        "157.240.0.0/16"      # Facebook
    ]
    for prefix in valid_prefixes:
        assert is_bogon_pfx(prefix) is False

def test_bogon_ipv6_prefixes():
    bogon_prefixes = [
        "::/8",              # IPv4-compatible
        "100::/64",          # Discard-Only
        "2001:db8::/32",     # Documentation
        "fc00::/7",          # Unique-Local
        "fe80::/10",         # Link-Local Unicast
        "ff00::/8"           # Multicast
    ]
    for prefix in bogon_prefixes:
        assert is_bogon_pfx(prefix) is True

def test_valid_ipv6_prefixes():
    valid_prefixes = [
        "2606:4700::/32",    # Cloudflare
        "2620:fe::/48",      # Google
        "2a03:2880::/32"     # Facebook
    ]
    for prefix in valid_prefixes:
        network = format_pfx(prefix)
        assert is_bogon_pfx(network) is False

def test_invalid_prefixes():
    invalid_prefixes = [
        "not.a.prefix",
        "300.0.0.0/8",       # Invalid IPv4
        "2001:xyz::/32"      # Invalid IPv6
    ]
    for prefix in invalid_prefixes:
        network = format_pfx(prefix)
        if network:
            assert is_bogon_pfx(network) is False
        else:
            assert network is None
