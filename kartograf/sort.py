from typing import List
import ipaddress

from kartograf.timed import timed


@timed
def sort_result_by_pfx(context):
    if context.args.irr and context.args.rv:
        out_file = f"{context.out_dir}merged_file_rpki_irr_rv.txt"
    elif context.args.irr:
        out_file = f"{context.out_dir}merged_file_rpki_irr.txt"
    elif context.args.rv:
        out_file = f"{context.out_dir}merged_file_rpki_rv.txt"
    else:
        out_file = f"{context.out_dir_rpki}rpki_final.txt"

    with open(out_file, 'r') as f:
        prefixes = f.read().splitlines()

    # Convert prefixes to a sortable form
    sortable_prefixes = []
    for prefix in prefixes:
        ip_prefix, asn = prefix.split(' ')
        net = ipaddress.ip_network(ip_prefix)
        # Determine if the network is IPv4 or IPv6
        is_ipv6 = int(net.version == 6)
        # Create a tuple containing whether it's IPv6, the IP network as an
        # integer, the prefix length (negated for descending order), and the
        # ASN
        sortable_prefixes.append((is_ipv6, int(net.network_address), -net.prefixlen, asn))

    sortable_prefixes.sort()

    sorted_out_file = f"{context.out_dir}merged_file_sorted.txt"
    with open(sorted_out_file, "w") as f:
        for is_ipv6, net_int, neg_prefixlen, asn in sortable_prefixes:
            net = ipaddress.IPv6Address(net_int) if is_ipv6 else ipaddress.IPv4Address(net_int)
            f.write(f'{str(net)}/{-neg_prefixlen} {asn}\n')
