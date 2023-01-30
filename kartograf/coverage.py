import ipaddress
import numpy as np
import pandas as pd
from tqdm import tqdm


def coverage(map_file, ip_list_file):
    tqdm.pandas()

    rpki_nets = []
    rpki_masks = []
    for line in map_file:
        pfx, asn = line.split(" ")
        ipn = ipaddress.ip_network(pfx)
        netw = int(ipn.network_address) # W: Constant name "netw" doesn't conform to UPPER_CASE naming style
        mask = int(ipn.netmask)
        rpki_masks.append(mask)
        rpki_nets.append(netw)

    net_masks = np.array(rpki_masks)
    network_addresses = np.array(rpki_nets)

    addrs = []
    for line in ip_list_file:
        ip = int(ipaddress.ip_address(line.rstrip('\n')))
        addrs.append(ip)

    df = pd.DataFrame()
    df['ADDRS'] = addrs

    def check_coverage(addr):
        cov_list = addr & net_masks == network_addresses

        if np.any(cov_list):
            return 1

        return 0

    df['COVERED'] = df.ADDRS.progress_apply(check_coverage)
    df_cov = df[df.COVERED == 1]

    covered = len(df_cov.index)
    total = len(df.index)
    percentage = (covered / total) * 100
    print(f"A total of {covered} IPs out of {total} are covered by the map. That's {percentage:.2f}%")
