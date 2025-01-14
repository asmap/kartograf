"""
A module to generate IP networks and ASNs for testing purposes.
"""

import ipaddress
from random import randint

MAX_ASN = 33521664

def generate_ip(ip_type="v4", subnet_size="16"):
    """
    Return a random IP network address for a given IP addr type and subnet size.
    """
    if ip_type == "v4":
        end_ip = int(ipaddress.IPv4Address("255.255.255.255"))
        subnet_mask = int(ipaddress.IPv4Network(f"0.0.0.0/{subnet_size}", strict=False).netmask)
    elif ip_type == "v6":
        end_ip = int(ipaddress.IPv6Address("ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff"))
        subnet_mask = int(ipaddress.IPv6Network(f"::::::::/{subnet_size}", strict=False).netmask)
    else:
        raise TypeError(f"invalid IP address type provided: {ip_type}")

    random_ip_int = randint(0, end_ip)

    if ip_type == "v4":
        network_addr = ipaddress.IPv4Address(random_ip_int & subnet_mask)
        return ipaddress.ip_network(str(network_addr) + f"/{subnet_size}")
    if ip_type == "v6":
        network_addr = ipaddress.IPv6Address(random_ip_int & subnet_mask)
        return ipaddress.ip_network(str(network_addr) + f"/{subnet_size}")
    return None

def generate_ip_networks(
    count, ip_type="v4", subnet_range_start=8, subnet_range_end=24
):
    ips = set()
    while count > 0:
        random_subnet = randint(subnet_range_start, subnet_range_end)
        ip = generate_ip(ip_type=ip_type, subnet_size=random_subnet)
        if ip not in ips:
            ips.add(ip)
            count -= 1
    return ips


def generate_asns(count):
    asns = set()
    while count > 0:
        asn = randint(1, MAX_ASN)
        if asn not in asns:
            asns.add(asn)
            count -= 1
    return asns


def generate_subnets_from_base(base_networks, count):
    subnets = []
    for network in base_networks[:count]:
        subnet = list(ipaddress.ip_network(network).subnets())[0]
        subnets.append(str(subnet.network_address))
    return subnets


def build_file_lines(ips, asns):
    lines = []
    for ip, asn in zip(ips, asns):
        lines.append(str(ip) + " " + "AS" + str(asn) + "\n")
    return lines


def generate_file_items(count, ip_type="v4"):
    """
    Generate the lines for an AS file, such as would be received from RPKI or RIR
    """
    ips = generate_ip_networks(count, ip_type)
    asns = generate_asns(count)
    lines = build_file_lines(ips, asns)
    return lines


def generate_ip_file(file_name, lines):
    """
    Write the items to a local file.
    """
    with open(file_name, "w") as f:
        for line in lines:
            f.write(line)
    return f"Generated {file_name}"


def make_disjoint(base_items, extra_items):
    """
    Takes two IP network lists and returns the extra networks without subnets of the base list, i.e. non overlapping networks from the extra list.
    """
    extra_new = []
    for extra in extra_items:
        included = False
        for network in base_items:
            if ipaddress.ip_network(extra).overlaps(ipaddress.ip_network(network)):
                included = True
                break
        if included is False:
            extra_new.append(extra)

    return extra_new
