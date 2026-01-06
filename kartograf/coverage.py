import ipaddress
import numpy as np
import pandas as pd
from tqdm import tqdm


def coverage(map_file, ip_list_file, output_file=None):
    tqdm.pandas()

    nets = []
    masks = []
    for line in map_file:
        pfx, _ = line.split()
        try:
            ipn = ipaddress.ip_network(pfx)
        except ValueError:
            raise ValueError(f"""
                  Invalid IP network provided: {line}
                  Please remove and re-run.
                  """)

        netw = int(ipn.network_address)
        mask = int(ipn.netmask)
        masks.append(mask)
        nets.append(netw)

    net_masks = np.array(masks)
    network_addresses = np.array(nets)
    zipped = list(zip(net_masks, network_addresses))

    addrs = []
    for line in ip_list_file:
        try:
            ip = ipaddress.ip_address(line.rstrip('\n'))
            addrs.append(int(ip))
        except ValueError:
            raise ValueError(f"""
                  Invalid IPv4/IPv6 address provided: {line}.
                  Please remove and re-run.
                  """)

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

    if output_file:
        with open(output_file, 'w') as f:
            for addr in df_cov['ADDRS']:
                formatted = str(ipaddress.ip_address(addr))
                f.write(f"{formatted}\n")
        print(f"Wrote {covered} IP addresses to {output_file}")
