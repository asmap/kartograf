import ipaddress
import numpy as np
import pandas as pd


def coverage(map_file, ip_list_file, output_covered=None, output_uncovered=None):
    nets = []
    masks = []
    asns = []
    for line in map_file:
        pfx, asn = line.split()
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
        asns.append(asn)

    net_masks = np.array(masks)
    network_addresses = np.array(nets)
    zipped = list(zip(net_masks, network_addresses, asns))

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
        for mask, net_addr, asn in zipped:
            if (addr & mask) == net_addr:
                return asn
        return 0

    df['COVERED'] = df.ADDRS.apply(check_coverage)
    df_cov = df[df.COVERED != 0]

    len_covered = len(df_cov)
    total = len(df)
    percentage = (len_covered / total) * 100
    print(f"A total of {len_covered} IPs out of {total} are covered by the map. "
          f"That's {percentage:.2f}%")

    if output_covered:
        if percentage > 0:
            write_covered(df_cov, output_covered, len_covered)
        else:
            print(f"No covered IPs, nothing to write to {output_covered}.")
    if output_uncovered:
        if percentage < 100:
            df_uncov = df[df.COVERED == 0]
            write_uncovered(df_uncov, output_uncovered, total - len_covered)
        else:
            print(f"All IPs covered, nothing to write to {output_uncovered}.")

def write_covered(df_cov, output_file, output_len):
    with open(output_file, 'w+') as f:
        for addr, asn in zip(df_cov['ADDRS'], df_cov['COVERED']):
            formatted = str(ipaddress.ip_address(addr))
            f.write(f"{formatted} {asn}\n")
        print(f"Wrote {output_len} IP addresses to {output_file}")

def write_uncovered(df_uncov, output_file, output_len):
    with open(output_file, 'w+') as f:
        for addr in df_uncov['ADDRS']:
            formatted = str(ipaddress.ip_address(addr))
            f.write(f"{formatted}\n")
        print(f"Wrote {output_len} IP addresses to {output_file}")
