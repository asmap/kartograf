import ipaddress
from kartograf.trie import IPTrie
from kartograf.timed import timed

@timed
def coverage(map_file, ip_list_file, output_covered=None, output_uncovered=None):
    print("Running coverage check...\n")

    trie = IPTrie()
    trie.from_map_file(map_file)
    addrs = []
    for line in ip_list_file:
        line = line.rstrip('\n')
        if not line:
            continue
        try:
            ip = ipaddress.ip_address(line)
            addrs.append((ip, line))
        except ValueError:
            raise ValueError(f"""
                  Invalid IPv4/IPv6 address provided: {line}.
                  Please remove and re-run.
                  """)

    covered_pairs = []
    not_covered_ips = []
    for ip, raw_addr in addrs:
        asn = trie.lookup(ip)
        if asn is not None:
            covered_pairs.append((raw_addr, asn))
        else:
            not_covered_ips.append(ip)

    len_covered = len(covered_pairs)
    total = len(addrs)
    percentage = (len_covered / total) * 100
    print(f"A total of {len_covered} IPs out of {total} are covered by the map. "
          f"That's {percentage:.2f}%")

    if output_covered:
        if percentage > 0:
            write_covered(covered_pairs, output_covered, len_covered)
        else:
            print(f"No covered IPs, nothing to write to {output_covered}.")
    if output_uncovered:
        if percentage < 100:
            write_uncovered(not_covered_ips, output_uncovered, total - len_covered)
        else:
            print(f"All IPs covered, nothing to write to {output_uncovered}.")

def write_covered(covered_pairs, output_file, output_len):
    with open(output_file, 'w') as f:
        for addr, asn in covered_pairs:
            formatted = str(ipaddress.ip_address(addr))
            f.write(f"{formatted} {asn}\n")
        print(f"Wrote {output_len} IP addresses to {output_file}")

def write_uncovered(ips, output_file, output_len):
    with open(output_file, 'w') as f:
        for addr in ips:
            formatted = str(ipaddress.ip_address(addr))
            f.write(f"{formatted}\n")
        print(f"Wrote {output_len} IP addresses to {output_file}")
