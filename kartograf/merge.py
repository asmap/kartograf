import ipaddress
import shutil
import numpy as np
import pandas as pd
from tqdm import tqdm

from kartograf.timed import timed


@timed
def merge_irr(context):
    rpki_file = f'{context.out_dir_rpki}rpki_final.txt'
    irr_file = f'{context.out_dir_irr}irr_final.txt'
    irr_filtered_file = f'{context.out_dir_irr}irr_filtered.txt'
    out_file = f"{context.out_dir}merged_file_rpki_irr.txt"

    general_merge(rpki_file, irr_file, irr_filtered_file, out_file)
    shutil.copy2(out_file, context.final_result_file)


@timed
def merge_pfx2as(context):
    # We are always doing RPKI but IRR is optional for now so depending on this
    # we are working off of a different base file for the merge.
    if context.args.irr:
        base_file = f'{context.out_dir}merged_file_rpki_irr.txt'
        out_file = f"{context.out_dir}merged_file_rpki_irr_rv.txt"
    else:
        base_file = f'{context.out_dir_rpki}rpki_final.txt'
        out_file = f"{context.out_dir}merged_file_rpki_rv.txt"

    rv_file = f'{context.out_dir_collectors}pfx2asn_clean.txt'
    rv_filtered_file = f'{context.out_dir_collectors}pfx2asn_filtered.txt'

    general_merge(base_file, rv_file, rv_filtered_file, out_file)
    shutil.copy2(out_file, context.final_result_file)


def general_merge(base_file, extra_file, extra_filtered_file, out_file):
    tqdm.pandas()

    print("Parse base file to numpy arrays")
    base_nets = []
    base_masks = []
    with open(base_file, "r") as file:
        for line in file:
            pfx, asn = line.split(" ")
            ipn = ipaddress.ip_network(pfx)
            netw = int(ipn.network_address)
            mask = int(ipn.netmask)
            base_masks.append(mask)
            base_nets.append(netw)

    net_masks = np.array(base_masks)
    network_addresses = np.array(base_nets)

    print("Parse extra file to Pandas DataFrame")
    extra_nets_int = []
    extra_asns = []
    extra_pfxs = []
    with open(extra_file, "r") as file:
        for line in file:
            pfx, asn = line.split(" ")
            ipn = ipaddress.ip_network(pfx)
            netw_int = int(ipn.network_address)
            extra_nets_int.append(netw_int)
            extra_asns.append(asn.strip())
            extra_pfxs.append(pfx)

    df_extra = pd.DataFrame()
    df_extra['INETS'] = extra_nets_int
    df_extra['ASNS'] = extra_asns
    df_extra['PFXS'] = extra_pfxs

    def check_inclusion(extra_net):
        inclusion_list = int(extra_net) & net_masks == network_addresses

        if np.any(inclusion_list):
            return 1

        return 0

    print("Filtering extra prefixes that were already "
          "included in the base file")
    df_extra['INCLUDED'] = df_extra.INETS.progress_apply(check_inclusion)
    df_filtered = df_extra[df_extra.INCLUDED == 0]

    if extra_filtered_file:
        print(f"Finished filtering! Originally {len(df_extra.index)} entries "
              f"filtered down to {len(df_filtered.index)}")
        df_filtered.to_csv(extra_filtered_file,
                           sep=' ',
                           index=False,
                           columns=["PFXS", "ASNS"],
                           header=False)

        with open(extra_filtered_file, "r") as extra:
            extra_contents = extra.read()
    else:
        print(f"Finished filtering! Originally {len(df_extra.index)} entries "
              f"filtered down to {len(df_filtered.index)}")
        extra_contents = df_filtered.to_csv(None,
                                            sep=' ',
                                            index=False,
                                            columns=["PFXS", "ASNS"],
                                            header=False)

    print("Merging base file with filtered extra file")
    with open(base_file, "r") as base:
        base_contents = base.read()

    merged_contents = base_contents + extra_contents

    with open(out_file, "w") as merge_file:
        merge_file.write(merged_contents)
