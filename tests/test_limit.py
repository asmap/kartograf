import ipaddress
import random

from kartograf.limit import limit_prefix_length


def test_long_entries_are_dropped():
    entries = [("10.0.0.0/24", "AS1"), ("10.0.0.0/25", "AS2"), ("10.0.0.1/32", "AS3"),
               ("2001:db8::/48", "AS4"), ("2001:db8::/49", "AS5"), ("2001:db8::1/128", "AS6")]
    assert limit_prefix_length(entries) == ([("10.0.0.0/24", "AS1"), ("2001:db8::/48", "AS4")], 4, 0)


def test_pieces_of_any_size_are_aggregated():
    entries = [("10.0.0.0/25", "AS1"), ("10.0.0.128/26", "AS1"), ("10.0.0.192/27", "AS1"),
               ("10.0.0.224/28", "AS1"), ("10.0.0.240/29", "AS1"), ("10.0.0.248/30", "AS1"),
               ("10.0.0.252/30", "AS1"), ("2001:db8::/49", "AS2"), ("2001:db8:0:8000::/49", "AS2")]
    assert limit_prefix_length(entries) == ([("10.0.0.0/24", "AS1"), ("2001:db8::/48", "AS2")], 9, 2)


def test_gaps_are_not_filled():
    entries = [("10.0.0.0/16", "AS2"), ("10.0.0.0/25", "AS1"), ("10.0.0.128/26", "AS1")]
    assert limit_prefix_length(entries) == ([("10.0.0.0/16", "AS2")], 2, 0)


def test_different_asns_are_not_aggregated():
    entries = [("10.0.0.0/25", "AS1"), ("10.0.0.128/25", "AS2")]
    assert limit_prefix_length(entries) == ([], 2, 0)


def test_nested_entries_do_not_add_coverage():
    entries = [("10.0.0.0/25", "AS1"), ("10.0.0.0/26", "AS1"), ("10.0.0.64/26", "AS1")]
    assert limit_prefix_length(entries) == ([], 3, 0)
    entries = [("10.0.0.0/25", "AS1"), ("10.0.0.127/32", "AS1"), ("10.0.0.128/25", "AS1")]
    assert limit_prefix_length(entries) == ([("10.0.0.0/24", "AS1")], 3, 1)


def test_aggregated_block_replaces_shadowed_entry():
    entries = [("10.0.0.0/24", "AS2"), ("10.0.0.0/25", "AS1"), ("10.0.0.128/25", "AS1")]
    assert limit_prefix_length(entries) == ([("10.0.0.0/24", "AS1")], 2, 1)


def brute_force(entries):
    '''Aggregate a /24 if its longer entries have one ASN and contain every address.'''
    result = {}
    blocks = {}
    for prefix, asn in entries:
        net = ipaddress.ip_network(prefix)
        if net.prefixlen <= 24:
            result[prefix] = asn
        else:
            blocks.setdefault(net.supernet(new_prefix=24), []).append((net, asn))
    for block, nets in blocks.items():
        addresses = set()
        for net, _ in nets:
            addresses.update(range(int(net.network_address), int(net.broadcast_address) + 1))
        if len({asn for _, asn in nets}) == 1 and len(addresses) == block.num_addresses:
            result[str(block)] = nets[0][1]
    return result


def random_tiling(rng, net):
    if net.prefixlen < 32 and (net.prefixlen == 24 or rng.random() < 0.5):
        return [prefix for half in net.subnets() for prefix in random_tiling(rng, half)]
    return [str(net)]


def random_entries(rng):
    entries = {}
    for i in range(4):
        if rng.random() < 0.5:
            cover = ipaddress.ip_network((f"10.0.{i}.0", rng.randint(22, 24)), strict=False)
            entries[str(cover)] = f"AS{rng.randint(1, 3)}"
        # Mostly one ASN with some gaps, so that both outcomes are common
        for prefix in random_tiling(rng, ipaddress.ip_network(f"10.0.{i}.0/24")):
            if rng.random() < 0.9:
                entries[prefix] = "AS1" if rng.random() < 0.9 else "AS2"
        for _ in range(rng.randint(0, 3)):
            net = ipaddress.ip_network((f"10.0.{i}.{rng.randint(0, 255)}", rng.randint(25, 32)), strict=False)
            entries[str(net)] = f"AS{rng.randint(1, 3)}"
    return list(entries.items())


def test_randomized_against_brute_force():
    for seed in range(200):
        entries = random_entries(random.Random(seed))
        kept, _, _ = limit_prefix_length(entries)
        assert sorted(kept) == sorted(brute_force(entries).items()), f"seed {seed}"
