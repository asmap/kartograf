from pathlib import Path
import ipaddress
import shutil
import pandas as pd

from kartograf.timed import timed
from kartograf.util import get_root_network


class BaseNetworkIndex:
    '''
    A class whose _dict represents a mapping of the network number and
    IP networks within that network for a given AS file.

    To check inclusion of a given IP network in the base AS file,
    we can compare (see check_inclusion) the networks under the root network number
    instead of all the networks in the base file.
    '''


    def __init__(self):
        self._dict = {4: {}, 6: {}}
        self._v4_keys = self._dict[4].keys()
        self._v6_keys = self._dict[6].keys()

    def update(self, pfx):
        try:
            ipn = ipaddress.ip_network(pfx)
        except ValueError:
            print(f"Invalid prefix provided: {pfx}")
            return

        netw = int(ipn.network_address)
        mask = int(ipn.netmask)
        v = ipn.version
        root_net = get_root_network(pfx)

        if (root_net in self._v4_keys) or (root_net in self._v6_keys):
            current = self._dict[v][root_net]
            self._dict[v][root_net] = current + [(netw, mask)]
        else:
            self._dict[v].update({root_net: [(netw, mask)]})

    def check_inclusion(self, row, root_net, version):
        """
        A network is a subnet of another if the bitwise AND of its IP and the base network's netmask
        is equal to the base network IP.
        """
        for net, mask in self._dict[version][root_net]:
            if row[0] & mask == net:
                return 1
        return 0

    def contains_row(self, row):
        root_net = row.PFXS_LEADING
        version = ipaddress.ip_network(row.PFXS).version
        if version == 4 and (root_net in self._v4_keys):
            return self.check_inclusion(row, root_net, version)
        if version == 6 and (root_net in self._v6_keys):
            return self.check_inclusion(row, root_net, version)
        return 0


@timed
def merge_irr(context):
    rpki_file = Path(context.out_dir_rpki) / "rpki_final.txt"
    irr_file = Path(context.out_dir_irr) / "irr_final.txt"
    irr_filtered_file = Path(context.out_dir_irr) / "irr_filtered.txt"
    out_file = Path(context.out_dir) / "merged_file_rpki_irr.txt"

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

    general_merge(
        base_file,
        rv_file,
        rv_filtered_file,
        out_file
    )
    shutil.copy2(out_file, context.final_result_file)


def extra_file_to_df(extra_file_path):
    extra_nets_int = []
    extra_asns = []
    extra_pfxs = []
    extra_pfxs_leading = []
    with open(extra_file_path, "r") as file:
        for line in file:
            pfx, asn = line.split(" ")
            try:
                ipn = ipaddress.ip_network(pfx)
            except ValueError:
                print(f"Invalid IP network: {pfx}, skipping")
                continue
            netw_int = int(ipn.network_address)
            extra_nets_int.append(netw_int)
            extra_asns.append(asn.strip())
            extra_pfxs.append(pfx)
            root_net = get_root_network(pfx)
            extra_pfxs_leading.append(root_net)

    df_extra = pd.DataFrame({
        "INETS": extra_nets_int,
        "ASNS": extra_asns,
        "PFXS": extra_pfxs,
        "PFXS_LEADING": extra_pfxs_leading
        })

    return df_extra


def general_merge(
    base_file, extra_file, extra_filtered_file, out_file
):
    """
    Merge lists of IP networks into a base file.
    """
    print("Parse base file to dictionary")
    base = BaseNetworkIndex()
    with open(base_file, "r") as file:
        for line in file:
            pfx, _ = line.split(" ")
            base.update(pfx)

    print("Parse extra file to Pandas DataFrame")
    df_extra = extra_file_to_df(extra_file)

    print("Merging extra prefixes that were not included in the base file.")
    chunk_size = 10000
    extra_included = []

    total_rows = len(df_extra)

    for start_idx in range(0, total_rows, chunk_size):
        end_idx = min(start_idx + chunk_size, total_rows)
        chunk = df_extra.iloc[start_idx:end_idx]

        chunk_results = []
        for row in chunk.itertuples(index=False):
            result = base.contains_row(row)
            chunk_results.append(result)

        extra_included.extend(chunk_results)

    df_extra["INCLUDED"] = extra_included
    df_filtered = df_extra[df_extra.INCLUDED == 0]

    print("Finished merging extra prefixes.")

    if extra_filtered_file:
        print(
            f"Finished filtering! Originally {len(df_extra.index)} "
            f"entries filtered down to {len(df_filtered.index)}"
        )
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
        print(
            f"Finished filtering! Originally {len(df_extra.index)} entries "
            f"filtered down to {len(df_filtered.index)}"
        )
        extra_contents = df_filtered.to_csv(
            None, sep=" ", index=False, columns=["PFXS", "ASNS"], header=False
        )

    print("Merging base file with filtered extra file")
    with open(base_file, "r") as base:
        base_contents = base.read()

    with open(out_file, "w") as merge_file:
        merge_file.write(base_contents + extra_contents)
