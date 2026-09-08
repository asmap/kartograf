from pathlib import Path
import ipaddress
import shutil
import pandas as pd

from kartograf.timed import timed
from kartograf.trie import IPTrie


class BaseNetworkIndex:
    '''
    An index of the base AS file's networks, backed by an IPTrie
    mapping each network to its ASN.

    To check inclusion of a given IP network in the base AS file,
    contains_row looks up the nearest covering prefix in the trie.
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

    def contains_row(self, row):
        """
        Check if the prefix in the row is covered by any prefix in the base file.
        A candidate prefix is covered if its network address matches a prefix in the trie
        """
        try:
            candidate = ipaddress.ip_network(row.PFXS)
        except ValueError:
            return 0
        asn = self._trie.covering_asn(candidate)
        if asn is not None:
            return 1
        return 0

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


def extra_file_to_df(extra_file_path):
    extra_asns = []
    extra_pfxs = []
    with open(extra_file_path, "r") as file:
        for line in file:
            if not line.strip():
                continue
            pfx, asn = line.split()
            try:
                ipaddress.ip_network(pfx)
            except ValueError:
                print(f"Invalid IP network: {pfx}, skipping")
                continue
            extra_asns.append(asn.strip())
            extra_pfxs.append(pfx)

    df_extra = pd.DataFrame({
        "ASNS": extra_asns,
        "PFXS": extra_pfxs,
        })

    return df_extra

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

    df_extra = extra_file_to_df(extra_file)

    print("Merging extra prefixes that were not included in the base file.")
    extra_included = []
    for row in df_extra.itertuples(index=False):
        extra_included.append(base_network_index.contains_row(row))

    df_extra["INCLUDED"] = extra_included

    df_filtered = df_extra[df_extra.INCLUDED == 0]

    if extra_filtered_file:
        df_filtered.to_csv(
            extra_filtered_file,
            sep=" ",
            index=False,
            columns=["PFXS", "ASNS"],
            header=False,
        )

        with open(extra_filtered_file, "r") as extra:
            extra_contents = extra.read()
    else:
        extra_contents = df_filtered.to_csv(
            None, sep=" ", index=False, columns=["PFXS", "ASNS"], header=False
        )

    with open(base_file, "r") as base:
        base_contents = base.read()

    with open(out_file, "w") as merge_file:
        merge_file.write(base_contents + extra_contents)
