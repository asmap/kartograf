"""
Drop entries that do not change the map.

Maps use longest prefix match, so an entry whose nearest covering prefix
maps to the same ASN never wins a lookup. Removing such entries makes the
output canonical: files that encode the same map are identical.
"""
import socket


def _parse_prefix(prefix):
    """Return (IP version, network address as int, prefix length)."""
    addr, _, prefixlen = prefix.partition("/")
    if ":" in addr:
        return 6, int.from_bytes(socket.inet_pton(socket.AF_INET6, addr), "big"), int(prefixlen)
    return 4, int.from_bytes(socket.inet_pton(socket.AF_INET, addr), "big"), int(prefixlen)


def _sort_key(entry):
    """One int per entry ordering by (version, network, prefix length)."""
    version, net_int, prefixlen = _parse_prefix(entry[0])
    return (version << 136) | (net_int << 8) | prefixlen


def prune_entries(entries):
    """
    Drop every (prefix, asn) entry whose nearest covering entry has the same
    ASN. Returns the kept entries, sorted by IP version, network address and
    prefix length, and the number of dropped entries.
    """
    entries = sorted(entries, key=_sort_key)
    kept = []
    # Covering prefixes that are still open, as (version, last address, asn).
    # Only kept entries are pushed, a dropped entry has the same ASN as its cover.
    stack = []
    for prefix, asn in entries:
        version, net_int, prefixlen = _parse_prefix(prefix)
        while stack and (stack[-1][0] != version or stack[-1][1] < net_int):
            stack.pop()
        if stack and stack[-1][2] == asn:
            continue
        bits = 32 if version == 4 else 128
        stack.append((version, net_int | ((1 << (bits - prefixlen)) - 1), asn))
        kept.append((prefix, asn))
    return kept, len(entries) - len(kept)
