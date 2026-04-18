from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import ipaddress
import math
import os
import shutil
from types import SimpleNamespace
import pandas as pd

from kartograf.timed import timed
from kartograf.util import get_root_network

MAX_MERGE_WORKERS = 4


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
            if row.INETS & mask == net:
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

    def get_serializable_dict(self):
        """Return the internal dict for serialization to worker processes."""
        return self._dict

    @classmethod
    def from_dict(cls, data_dict):
        """Reconstruct a BaseNetworkIndex from a serialized dict."""
        instance = cls()
        instance._dict = data_dict
        instance._v4_keys = instance._dict[4].keys()
        instance._v6_keys = instance._dict[6].keys()
        return instance

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

def process_chunk_worker(chunk_data, base_dict):
    base = BaseNetworkIndex.from_dict(base_dict)

    results = []
    for original_idx, (net_int, pfx, pfx_leading) in chunk_data:
        row = SimpleNamespace(PFXS=pfx, PFXS_LEADING=pfx_leading, INETS=net_int)

        result = base.contains_row(row)
        results.append((original_idx, result))
    return results


def pick_chunk_size(n_rows: int, workers: int | None = None,
                    min_chunk: int = 5,
                    max_chunk: int = 200_000) -> int:
    if workers is None:
        workers = os.cpu_count() or 4
    chunk = math.ceil(n_rows / workers)
    return max(min_chunk, min(max_chunk, chunk))


def general_merge(
    base_file, extra_file, extra_filtered_file, out_file
):
    """
    Merge lists of IP networks into a base file.
    """
    print("Merging extra prefixes that were not included in the base file.")
    base_network_index = BaseNetworkIndex()
    with open(base_file, "r") as file:
        for line in file:
            pfx, _ = line.split(" ")
            base_network_index.update(pfx)

    df_extra = extra_file_to_df(extra_file)

    len_df_extra = len(df_extra)
    workers = min(os.cpu_count() or 4, MAX_MERGE_WORKERS)
    if len_df_extra:
        workers = min(workers, len_df_extra)

    chunk_size = pick_chunk_size(len_df_extra, workers=workers)
    chunks = []
    chunk_data = []
    for i, row in df_extra.iterrows():
        chunk_data.append((i, (row.INETS, row.PFXS, row.PFXS_LEADING)))
        if (i + 1) % chunk_size == 0 or i == len_df_extra - 1:
            chunks.append(chunk_data)
            chunk_data = []

    all_results = []
    if chunks:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            base_dict = base_network_index.get_serializable_dict()
            futures = [executor.submit(process_chunk_worker, chunk, base_dict) for chunk in chunks]

            for future in futures:
                all_results.extend(future.result())

        # Sort by original index
        all_results.sort(key=lambda x: x[0])

        df_extra["INCLUDED"] = [result for _, result in all_results]
    else:
        df_extra["INCLUDED"] = pd.Series(dtype="int64")

    df_filtered = df_extra[df_extra.INCLUDED == 0]

    def write_non_empty_lines(src_path, dst_handle):
        with open(src_path, "r") as src:
            for line in src:
                line_without_newline = line.rstrip("\r\n")
                if line_without_newline.strip():
                    dst_handle.write(line_without_newline + "\n")

    with open(out_file, "w") as merge_file:
        write_non_empty_lines(base_file, merge_file)

        if extra_filtered_file:
            with open(extra_filtered_file, "w") as filtered_file:
                for row in df_filtered.itertuples(index=False):
                    line = f"{row.PFXS} {row.ASNS}"
                    filtered_file.write(line + "\n")
                    merge_file.write(line + "\n")
        else:
            for row in df_filtered.itertuples(index=False):
                merge_file.write(f"{row.PFXS} {row.ASNS}\n")
