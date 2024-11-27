import ipaddress
import pandas as pd
from kartograf.merge import BaseNetworkIndex
from kartograf.util import get_root_network


def _df_from_network(network, asn=123):
    '''
    Create a one-row dataframe that holds the extra file rows in the expected format for contains_row().
    '''
    ipn = ipaddress.ip_network(network)
    root_net = get_root_network(network)
    network_int = int(ipn.network_address)
    df_extra = pd.DataFrame(
        data={"INETS": network_int, "ASNS": asn, "PFXS": network, "PFXS_LEADING": root_net},
        index=[0],
    )
    return df_extra


def test_base_dict_create():
    '''
    contains_row returns false when adding a row to an empty base file dict.
    '''
    base = BaseNetworkIndex()
    network = "10.10.0.0/16"
    df_extra = _df_from_network(network)
    for row in df_extra.itertuples(index=False):
        assert not base.contains_row(row)


def test_base_dict_update():
    '''
    contains_row returns true when adding a row already present in the base dict.
    '''
    base = BaseNetworkIndex()
    network = "10.10.0.0/16"
    base.update(network)
    df_extra = _df_from_network(network)
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
    df_extra = _df_from_network(subnet)
    for row in df_extra.itertuples(index=False):
        assert base.contains_row(row)
