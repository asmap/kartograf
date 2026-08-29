from pathlib import Path
import ipaddress
import shutil

from kartograf.timed import timed
from kartograf.trie import IPTrie


class BaseNetworkIndex:
    '''
    An index of the base AS file's networks, backed by an IPTrie
    mapping each network to its ASN.

    To check inclusion of a given IP network in the base AS file,
    contains looks up the nearest covering prefix in the trie.
    '''

    def __init__(self):
        self._trie = IPTrie()

    def update(self, pfx, asn):
        try:
            ipn = ipaddress.ip_network(pfx)
        except ValueError:
            print(f"Invalid prefix provided: {pfx}")
            return
        self._trie.insert(ipn, asn)

    def contains(self, pfx):
        return self._trie.covering_asn(ipaddress.ip_network(pfx)) is not None

@timed
def merge_irr(context):
    rpki_file = Path(context.out_dir_rpki) / "rpki_final.txt"
    irr_file = Path(context.out_dir_irr) / "irr_final.txt"
    irr_filtered_file = Path(context.out_dir_irr) / "irr_filtered.txt"
    out_file = Path(context.out_dir) / "merged_file_rpki_irr.txt"
    context.cleanup_out_files += [irr_filtered_file, out_file]

    general_merge(
        rpki_file,
        irr_file,
        irr_filtered_file,
        out_file
    )
    shutil.copy2(out_file, context.final_result_file)


@timed
def merge_pfx2as(context):
    # We are always doing RPKI but IRR is optional for now so depending on this
    # we are working off of a different base file for the merge.
    if context.args.irr:
        base_file = Path(context.out_dir) / "merged_file_rpki_irr.txt"
        out_file = Path(context.out_dir) / "merged_file_rpki_irr_rv.txt"
    else:
        base_file = Path(context.out_dir_rpki) / "rpki_final.txt"
        out_file = Path(context.out_dir) / "merged_file_rpki_rv.txt"

    rv_file = Path(context.out_dir_collectors) / "pfx2asn_clean.txt"
    rv_filtered_file = Path(context.out_dir_collectors) / "pfx2asn_filtered.txt"
    context.cleanup_out_files += [rv_filtered_file, out_file]

    general_merge(
        base_file,
        rv_file,
        rv_filtered_file,
        out_file
    )
    shutil.copy2(out_file, context.final_result_file)


def general_merge(
    base_file, extra_file, extra_filtered_file, out_file
):
    """
    Merge lists of IP networks into a base file.
    """
    print("Creating network index from base file.")
    base_network_index = BaseNetworkIndex()
    with open(base_file, "r") as file:
        for line in file:
            if not line.strip():
                continue
            pfx, asn = line.split()
            base_network_index.update(pfx, asn.strip())

    print("Merging extra prefixes that were not included in the base file.")
    extra_filtered = []
    with open(extra_file, "r") as file:
        for line in file:
            if not line.strip():
                continue
            pfx, asn = line.split()
            try:
                included = base_network_index.contains(pfx)
            except ValueError:
                print(f"Invalid IP network: {pfx}, skipping")
                continue
            if not included:
                extra_filtered.append(f"{pfx} {asn}\n")

    # Read the base before opening the output, they may be the same file.
    with open(base_file, "r") as base:
        base_contents = base.read()

    if extra_filtered_file:
        with open(extra_filtered_file, "w") as file:
            file.writelines(extra_filtered)

    with open(out_file, "w") as merge_file:
        merge_file.write(base_contents)
        merge_file.writelines(extra_filtered)
