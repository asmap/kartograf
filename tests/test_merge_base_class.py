from collections import namedtuple
import ipaddress
from kartograf.merge import BaseNetworkIndex
from kartograf.util import get_root_network

Row = namedtuple("Row", ["INETS", "ASNS", "PFXS", "PFXS_LEADING"])


def _rows_from_networks(networks, asn=123):
    '''
    Create the extra file rows in the expected format for contains_row().
    '''
    rows = []
    for network in networks:
        ipn = ipaddress.ip_network(network)
        root_net = get_root_network(network)
        network_int = int(ipn.network_address)
        rows.append(Row(network_int, asn, str(ipn), root_net))
    return rows


def test_base_dict_create():
    '''
    contains_row returns false when adding a row to an empty base file dict.
    '''
    base = BaseNetworkIndex()
    ipv4_network = "10.10.0.0/16"
    ipv6_network = "2c0f:ff90::/32"
    for row in _rows_from_networks([ipv4_network, ipv6_network]):
        assert not base.contains_row(row)


def test_base_dict_update():
    '''
    contains_row returns true when adding a row already present in the base dict.
    '''
    base = BaseNetworkIndex()
    ipv4_network = "10.10.0.0/16"
    ipv6_network = "2c0f:ff90::/32"
    base.update(ipv4_network)
    base.update(ipv6_network)
    for row in _rows_from_networks([ipv4_network, ipv6_network]):
        assert base.contains_row(row)


def test_check_included_subnet():
    '''
    contains_row returns true when adding a subnet of a row already present in the base dict.
    '''
    base = BaseNetworkIndex()
    network = "10.10.0.0/16"
    base.update(network)
    subnet = "10.10.0.0/21"
    for row in _rows_from_networks([subnet]):
        assert base.contains_row(row)
