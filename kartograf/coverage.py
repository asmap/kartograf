import ipaddress
import numpy as np
import pandas as pd
from tqdm import tqdm


def coverage(map_file, ip_list_file):
    tqdm.pandas()

    rpki_nets = []
    rpki_masks = []
    for line in map_file:
        pfx, _ = line.split()
        try:
            ipn = ipaddress.ip_network(pfx)
        except ValueError:
            print(f"Invalid IP network provided: {line}")
            continue
        netw = int(ipn.network_address)
        mask = int(ipn.netmask)
        rpki_masks.append(mask)
        rpki_nets.append(netw)

    net_masks = np.array(rpki_masks)
    network_addresses = np.array(rpki_nets)
    zipped = list(zip(net_masks, network_addresses))

    addrs = []
    for line in ip_list_file:
        try:
            ip = ipaddress.ip_address(line.rstrip('\n'))
            addrs.append(int(ip))
        except ValueError:
            continue

    df = pd.DataFrame({'ADDRS': addrs})

    def check_coverage(addr):
        for mask, net_addr in zipped:
            if (addr & mask) == net_addr:
                return 1
        return 0

    df['COVERED'] = df.ADDRS.progress_apply(check_coverage)
    df_cov = df[df.COVERED == 1]

    covered = len(df_cov)
    total = len(df)
    percentage = (covered / total) * 100
    print(f"A total of {covered} IPs out of {total} are covered by the map. "
          f"That's {percentage:.2f}%")
