import ipaddress
import pandas as pd
from kartograf.merge import BaseNetworkIndex
from kartograf.util import get_root_network


def _df_from_networks(networks, asn=123):
    '''
    Create a one-row dataframe that holds the extra file rows in the expected format for contains_row().
    '''
    df = pd.DataFrame(
        columns=["INETS", "ASNS", "PFXS", "PFXS_LEADING"],
    )
    for network in networks:
        ipn = ipaddress.ip_network(network)
        root_net = get_root_network(network)
        print(root_net)
        network_int = int(ipn.network_address)
        df.loc[len(df)] = [network_int, asn, str(ipn), root_net]
    return df


def test_base_dict_create():
    '''
    contains_row returns false when adding a row to an empty base file dict.
    '''
    base = BaseNetworkIndex()
    ipv4_network = "10.10.0.0/16"
    ipv6_network = "2c0f:ff90::/32"
    df_extra = _df_from_networks([ipv4_network, ipv6_network])
    for row in df_extra.itertuples(index=False):
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
    df_extra = _df_from_networks([ipv4_network, ipv6_network])
    for row in df_extra.itertuples(index=False):
        assert base.contains_row(row)


def test_check_included_subnet():
    '''
    contains_row returns true when adding a subnet of a row already present in the base dict.
    '''
    base = BaseNetworkIndex()
    network = "10.10.0.0/16"
    base.update(network)
    subnet = "10.10.0.0/21"
    df_extra = _df_from_networks([subnet])
    for row in df_extra.itertuples(index=False):
        assert base.contains_row(row)
