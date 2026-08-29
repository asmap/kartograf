from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import ipaddress
import math
import os
import shutil
from types import SimpleNamespace

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
            self._dict[v][root_net] = current + [(netw, mask, ipn.prefixlen)]
        else:
            self._dict[v].update({root_net: [(netw, mask, ipn.prefixlen)]})

    def check_inclusion(self, row, root_net, version):
        """
        A network is a subnet of another if the bitwise AND of its IP and the base network's netmask
        is equal to the base network IP, and the network's prefix length is larger or equal than the base network's
        prefix length.
        """
        candidate = ipaddress.ip_network(row.PFXS)
        for net, mask, prefixlen in self._dict[version][root_net]:
            if candidate.prefixlen >= prefixlen and row.INETS & mask == net:
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


def read_extra_file(extra_file_path):
    """Return a list of (network_int, asn, prefix, root_network) tuples."""
    rows = []
    with open(extra_file_path, "r") as file:
        for line in file:
            pfx, asn = line.split(" ")
            try:
                ipn = ipaddress.ip_network(pfx)
            except ValueError:
                print(f"Invalid IP network: {pfx}, skipping")
                continue
            rows.append((int(ipn.network_address), asn.strip(), pfx, get_root_network(pfx)))

    return rows

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

    extra_rows = read_extra_file(extra_file)

    chunk_size = pick_chunk_size(len(extra_rows))
    chunks = []
    for start in range(0, len(extra_rows), chunk_size):
        chunks.append([
            (i, (net_int, pfx, root_net))
            for i, (net_int, _, pfx, root_net)
            in enumerate(extra_rows[start:start + chunk_size], start)
        ])

    all_results = []
    with ProcessPoolExecutor() as executor:
        base_dict = base_network_index.get_serializable_dict()
        futures = [executor.submit(process_chunk_worker, chunk, base_dict) for chunk in chunks]

        for future in futures:
            all_results.extend(future.result())

    # Sort by original index
    all_results.sort(key=lambda x: x[0])

    extra_contents = "".join(
        f"{pfx} {asn}\n"
        for (_, asn, pfx, _), (_, included) in zip(extra_rows, all_results, strict=True)
        if included == 0
    )

    if extra_filtered_file:
        with open(extra_filtered_file, "w") as extra:
            extra.write(extra_contents)

    with open(base_file, "r") as base:
        base_contents = base.read()

    with open(out_file, "w") as merge_file:
        merge_file.write(base_contents + extra_contents)
