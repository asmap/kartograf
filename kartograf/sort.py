import ipaddress
from pathlib import Path

from kartograf.prune import prune_entries
from kartograf.timed import timed


def _sort_key(entry):
    # IPv4 before IPv6, then by network address, longer prefixes first for
    # the same address, then by ASN
    net = ipaddress.ip_network(entry[0])
    return (int(net.version == 6), int(net.network_address), -net.prefixlen, entry[1])


@timed
def sort_result_by_pfx(context):
    if context.args.irr and context.args.routeviews:
        out_file = Path(context.out_dir) / "merged_file_rpki_irr_rv.txt"
    elif context.args.irr:
        out_file = Path(context.out_dir) / "merged_file_rpki_irr.txt"
    elif context.args.routeviews:
        out_file = Path(context.out_dir) / "merged_file_rpki_rv.txt"
    else:
        out_file = Path(context.out_dir_rpki) / "rpki_final.txt"

    with open(out_file, 'r') as file:
        entries = [tuple(line.split()) for line in file if line.strip()]

    # Catches entries that only became redundant through the merge, e.g. an
    # RPKI /24 under an IRR /23 with the same ASN.
    entries, pruned = prune_entries(entries)
    print(f"Redundant entries pruned: {pruned}")

    # The prefixes are canonical strings from our parsers, so they are
    # written back as they are once sorted.
    entries.sort(key=_sort_key)

    sorted_out_file = Path(context.out_dir) / "merged_file_sorted.txt"
    with open(sorted_out_file, "w") as file:
        for prefix, asn in entries:
            file.write(f"{prefix} {asn}\n")

    sorted_out_file.rename(Path(context.final_result_file))
