import ipaddress
import sys
from kartograf.asmap import ASMap, net_to_prefix
from kartograf.timed import timed


def load_file(input_file):
    try:
        with open(input_file.name, 'rb') as f:
            contents = f.read()
    except FileNotFoundError as err:
        sys.exit(f"Input file '{input_file.name}' cannot be read: {err.strerror}.")
    txt_error = None
    entries = None
    try:
        txt_contents = str(contents, encoding="utf-8")
    except UnicodeError:
        txt_error = "invalid UTF-8"
        txt_contents = None
    if txt_contents is not None:
        entries = []
        for line in txt_contents.split("\n"):
            idx = line.find('#')
            if idx >= 0:
                line = line[:idx]
            line = line.lstrip(' ').rstrip(' \t\r\n')
            if len(line) == 0:
                continue
            fields = line.split(' ')
            if len(fields) != 2:
                txt_error = f"unparseable line '{line}'"
                entries = None
                break
            prefix, asn = fields
            if len(asn) <= 2 or asn[:2] != "AS" or any(c < '0' or c > '9' for c in asn[2:]):
                txt_error = f"invalid ASN '{asn}'"
                entries = None
                break
            try:
                net = ipaddress.ip_network(prefix)
            except ValueError:
                txt_error = f"invalid network '{prefix}'"
                entries = None
                break
            entries.append((net_to_prefix(net), int(asn[2:])))
    if entries is not None:
        state = ASMap()
        state.update_multi(entries)
        return state
    sys.exit(f"Input file '{input_file.name}' is not valid map entry ({txt_error}).")


def load_ip_list_file(ip_list):
    with open(ip_list.name, 'rb') as f:
        try:
            contents = f.read()
        except OSError as err:
            sys.exit(f"Input file '{ip_list.name}' cannot be read: {err.strerror}.")
        txt_error = None
        try:
            txt_contents = str(contents, encoding="utf-8")
        except UnicodeError:
            txt_error = "invalid UTF-8"
            txt_contents = None
            sys.exit(f"Input file '{ip_list.name}' is not valid: ({txt_error}).")
        addrs = []
        if txt_contents is not None:
            for line in txt_contents.split("\n"):
                if len(line) == 0:
                    continue
                try:
                    ip = ipaddress.ip_address(line)
                    addrs.append((ip, line))
                except ValueError:
                    txt_error = f"Invalid IPv4/IPv6 address provided: {line}. Please remove and re-run."
            if txt_error is not None:
                sys.exit(f"Input file '{ip_list.name}' is not valid IP list ({txt_error}).")
        return addrs

@timed
def coverage(map_file, ip_list_file, output_covered=None, output_uncovered=None):
    trie = load_file(map_file)
    addrs = load_ip_list_file(ip_list_file)

    covered_pairs = []
    not_covered_ips = []
    for ip, raw_addr in addrs:
        if isinstance(ip, ipaddress.IPv4Address):
            net = ipaddress.ip_network(f"{ip}/32")
        else:
            net = ipaddress.ip_network(f"{ip}/128")
        asn = trie.lookup(net_to_prefix(net))
        if asn not in [None, 0]:
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
    with open(output_file, 'w+') as f:
        for addr, asn in covered_pairs:
            formatted = str(ipaddress.ip_address(addr))
            f.write(f"{formatted} AS{asn}\n")
        print(f"Wrote {output_len} IP addresses to {output_file}")

def write_uncovered(ips, output_file, output_len):
    with open(output_file, 'w+') as f:
        for addr in ips:
            formatted = str(ipaddress.ip_address(addr))
            f.write(f"{formatted}\n")
        print(f"Wrote {output_len} IP addresses to {output_file}")
