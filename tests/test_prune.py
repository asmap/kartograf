import ipaddress
import random

from kartograf.prune import prune_entries


def test_nested_same_asn_is_dropped():
    kept, removed = prune_entries([("10.0.0.0/23", "AS1"), ("10.0.0.0/24", "AS1")])
    assert kept == [("10.0.0.0/23", "AS1")]
    assert removed == 1


def test_nested_different_asn_is_kept():
    entries = [("10.0.0.0/23", "AS1"), ("10.0.0.0/24", "AS2")]
    assert prune_entries(entries) == (entries, 0)


def test_chain_collapses_to_least_specific():
    entries = [("10.0.0.0/24", "AS1"), ("10.0.0.0/22", "AS1"), ("10.0.0.0/23", "AS1")]
    assert prune_entries(entries) == ([("10.0.0.0/22", "AS1")], 2)


def test_chain_with_different_asn_in_the_middle_is_kept():
    # Dropping the /24 would hand its addresses to the /23 and AS2
    entries = [("10.0.0.0/22", "AS1"), ("10.0.0.0/23", "AS2"), ("10.0.0.0/24", "AS1")]
    assert prune_entries(entries) == (entries, 0)


def test_sibling_networks_are_not_covers():
    entries = [("10.0.0.0/24", "AS1"), ("10.0.1.0/24", "AS1"), ("10.0.2.0/23", "AS1")]
    assert prune_entries(entries) == (entries, 0)


def test_ipv4_and_ipv6_do_not_cover_each_other():
    # ::a00:0/112 has the same integer address range start as 10.0.0.0/8
    entries = [("10.0.0.0/8", "AS1"), ("::a00:0/112", "AS1"),
               ("2001:db8::/32", "AS2"), ("2001:db8:1::/48", "AS2")]
    kept, removed = prune_entries(entries)
    assert kept == [("10.0.0.0/8", "AS1"), ("::a00:0/112", "AS1"), ("2001:db8::/32", "AS2")]
    assert removed == 1


def test_output_is_sorted_by_version_network_and_prefix_length():
    entries = [("2001:db8::/32", "AS4"), ("192.0.2.0/24", "AS3"), ("10.0.0.0/24", "AS1"),
               ("10.0.0.0/23", "AS2"), ("172.16.0.0/12", "AS2"), ("10.0.0.0/22", "AS1")]
    kept, removed = prune_entries(entries)
    assert kept == [("10.0.0.0/22", "AS1"), ("10.0.0.0/23", "AS2"), ("10.0.0.0/24", "AS1"),
                    ("172.16.0.0/12", "AS2"), ("192.0.2.0/24", "AS3"), ("2001:db8::/32", "AS4")]
    assert removed == 0


def test_input_is_not_modified():
    entries = [("10.0.0.0/24", "AS1"), ("10.0.0.0/23", "AS1")]
    prune_entries(entries)
    assert entries == [("10.0.0.0/24", "AS1"), ("10.0.0.0/23", "AS1")]


def brute_force_kept(entries):
    '''Keep an entry unless its most specific containing entry has the same ASN.'''
    nets = [(ipaddress.ip_network(prefix), asn) for prefix, asn in entries]
    kept = set()
    for i, (net, asn) in enumerate(nets):
        cover_len = -1
        cover_asn = None
        for j, (other, other_asn) in enumerate(nets):
            if i == j or net.version != other.version:
                continue
            if other.prefixlen < net.prefixlen and net.subnet_of(other):
                if other.prefixlen > cover_len:
                    cover_len = other.prefixlen
                    cover_asn = other_asn
        if cover_len < 0 or cover_asn != asn:
            kept.add(entries[i])
    return kept


def random_entries(rng, count):
    entries = {}
    while len(entries) < count:
        if rng.random() < 0.7:
            prefixlen = rng.randint(8, 24)
            addr = ipaddress.IPv4Address(rng.getrandbits(32))
        else:
            prefixlen = rng.randint(16, 64)
            # Small address space so that nesting is common
            addr = ipaddress.IPv6Address(rng.getrandbits(48) << 80)
        net = ipaddress.ip_network((addr, prefixlen), strict=False)
        entries[str(net)] = f"AS{rng.randint(1, 3)}"
    return list(entries.items())


def test_randomized_against_brute_force():
    for seed in range(25):
        entries = random_entries(random.Random(seed), 150)
        kept, removed = prune_entries(entries)
        assert set(kept) == brute_force_kept(entries), f"seed {seed}"
        assert len(kept) + removed == len(entries)
