import ipaddress
import shutil
import pandas as pd

from kartograf.timed import timed

class BaseNetworkIndex:
    '''
    A class whose _dict represents a mapping of the network number and IP networks within that network for a given AS file.

    To check inclusion of a given IP network in the base AS file, we can compare (see check_inclusion) the networks under the root network number instead of all the networks in the base file.
    '''


    def __init__(self):
        self._dict = {}
        self._keys = self._dict.keys()
        for i in range(0, 255):
            self._dict[i] = []

    def update(self, pfx):
        ipn = ipaddress.ip_network(pfx)
        netw = int(ipn.network_address)
        mask = int(ipn.netmask)
        if ipn.version == 4:
            root_net = int(str(pfx).split(".", maxsplit=1)[0])
            current = self._dict[root_net]
            self._dict[root_net] = current + [(netw, mask)]
        else:
            root_net = str(pfx).split(":", maxsplit=1)[0]
            if root_net in self._keys:
                current = self._dict[root_net]
                self._dict[root_net] = current + [(netw, mask)]
            else:
                self._dict.update({root_net: [(netw, mask)]})

    def check_inclusion(self, row, root_net):
        """
        A network is a subnet of another if the bitwise AND of its IP and the base network's netmask
        is equal to the base network IP.
        """
        for net, mask in self._dict[root_net]:
            if row[0] & mask == net:
                return 1
        return 0

    def contains_row(self, row):
        root_net = row.PFXS_LEADING
        if root_net in self._keys:
            return self.check_inclusion(row, root_net)
        return 0


@timed
def merge_irr(context):
    rpki_file = f"{context.out_dir_rpki}rpki_final.txt"
    irr_file = f"{context.out_dir_irr}irr_final.txt"
    irr_filtered_file = f"{context.out_dir_irr}irr_filtered.txt"
    out_file = f"{context.out_dir}merged_file_rpki_irr.txt"

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
        base_file = f"{context.out_dir}merged_file_rpki_irr.txt"
        out_file = f"{context.out_dir}merged_file_rpki_irr_rv.txt"
    else:
        base_file = f"{context.out_dir_rpki}rpki_final.txt"
        out_file = f"{context.out_dir}merged_file_rpki_rv.txt"

    rv_file = f"{context.out_dir_collectors}pfx2asn_clean.txt"
    rv_filtered_file = f"{context.out_dir_collectors}pfx2asn_filtered.txt"

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
    print("Parse base file to dictionary")
    base = BaseNetworkIndex()
    with open(base_file, "r") as file:
        for line in file:
            pfx, asn = line.split(" ")
            base.update(pfx)

    print("Parse extra file to Pandas DataFrame")
    extra_nets_int = []
    extra_asns = []
    extra_pfxs = []
    extra_pfxs_leading = []
    with open(extra_file, "r") as file:
        for line in file:
            pfx, asn = line.split(" ")
            ipn = ipaddress.ip_network(pfx)
            netw_int = int(ipn.network_address)
            extra_nets_int.append(netw_int)
            extra_asns.append(asn.strip())
            extra_pfxs.append(pfx)
            if ipn.version == 4:
                root_net = int(pfx.split(".", maxsplit=1)[0])
            else:
                root_net = str(pfx).split(":", maxsplit=1)[0]
            extra_pfxs_leading.append(root_net)

    df_extra = pd.DataFrame()
    df_extra["INETS"] = extra_nets_int
    df_extra["ASNS"] = extra_asns
    df_extra["PFXS"] = extra_pfxs
    df_extra["PFXS_LEADING"] = extra_pfxs_leading

    print("Merging extra prefixes that were not included in the base file:\n")

    extra_included = []
    for row in df_extra.itertuples(index=False):
        result = base.contains_row(row)
        extra_included.append(result)

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

    merged_contents = base_contents + extra_contents

    with open(out_file, "w") as merge_file:
        merge_file.write(merged_contents)
