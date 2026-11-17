import ipaddress

MAX_PREFIXLEN = {4: 24, 6: 48}


def limit_prefix_length(entries):
    """
    Drop entries longer than MAX_PREFIXLEN, they are not routed globally. A
    block fully covered by dropped entries of one ASN is mapped to that ASN.
    Returns the kept entries and the numbers of dropped entries and aggregated
    blocks.
    """
    kept = []
    long_entries = {}
    for entry in entries:
        prefix = entry[0]
        if int(prefix[prefix.rindex("/") + 1:]) <= MAX_PREFIXLEN[6 if ":" in prefix else 4]:
            kept.append(entry)
            continue
        net = ipaddress.ip_network(prefix)
        block = net.supernet(new_prefix=MAX_PREFIXLEN[net.version])
        long_entries.setdefault(block, []).append((net, entry[1]))

    aggregated = {}
    for block, pieces in long_entries.items():
        asn = pieces[0][1]
        if any(piece_asn != asn for _, piece_asn in pieces):
            continue
        covered = 0
        last = None
        for net, _ in sorted(pieces):
            # Nested
            if last is not None and net.network_address <= last:
                continue
            covered += net.num_addresses
            last = net.broadcast_address
        if covered == block.num_addresses:
            aggregated[str(block)] = asn

    dropped = len(entries) - len(kept)
    count = len(aggregated)
    if aggregated:
        # Replace a shadowed entry for the block
        for i, (prefix, _) in enumerate(kept):
            if prefix in aggregated:
                kept[i] = (prefix, aggregated.pop(prefix))
        kept.extend(aggregated.items())
    return kept, dropped, count
