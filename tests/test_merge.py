'''
Test merging multiple sets of networks, as if they were independent AS files.
'''
from pathlib import Path

from kartograf.merge import general_merge

from .util.generate_data import (
    build_file_lines,
    generate_ip_file,
    generate_file_items,
    generate_asns,
    generate_subnets_from_base,
    make_disjoint
)


def __tmp_paths(tmp_path):
    return [tmp_path / p for p in ["rpki_final.txt", "irr_final.txt", "out.txt"]]

def __read_test_vectors(filepath):
    '''
    Fixtures for IP networks are under tests/data.
    Read them and return the list of valid networks and the list of individual subnets in the file.
    '''
    all_networks = []
    all_in_result = []
    with open(filepath, "r") as f:
        lines = f.readlines()[1:]
        for line in lines:
            network, in_result, _comment = line.split(',')
            all_networks.append(network)
            if in_result.strip() == "1":
                all_in_result.append(network)
    return all_networks, all_in_result

def test_merge_from_fixtures(tmp_path):
    '''
    Assert that general_merge merges subnets correctly,
    and validates against expected networks,
    i.e. subnets are merged into the root network appropriately.
    '''
    data_dir = Path(__file__).parent / "data"
    base_nets, base_results = __read_test_vectors(data_dir / "base_file.csv")
    base_path = tmp_path / "base.txt"
    extra_nets, extra_results = __read_test_vectors(data_dir / "extra_file.csv")
    extra_path = tmp_path / "extra.txt"
    # write the networks to disk, generating ASNs for each network
    generate_ip_file(base_path, build_file_lines(base_nets, generate_asns(len(base_nets))))
    generate_ip_file(extra_path, build_file_lines(extra_nets, generate_asns(len(extra_nets))))

    outpath = tmp_path / "final_result.txt"
    general_merge(base_path, extra_path, None, outpath)
    with open(outpath, "r") as f:
        l = f.readlines()
        merged_networks = sorted([line.split()[0] for line in l])
    expected_networks = sorted(base_results + extra_results)
    # Compare the merged result of networks, excluding duplicates and subnets,
    # with the expected results
    assert merged_networks == expected_networks

def test_merge(tmp_path):
    '''
    Assert that merging two identical files is a no-op.
    '''
    rpki_data = generate_file_items(100)
    rpki_path, _, out_path = __tmp_paths(tmp_path)
    generate_ip_file(rpki_path, rpki_data)

    general_merge(rpki_path, rpki_path, None, out_path)

    with open(out_path, "r") as f:
        lines = f.readlines()
        final_ips = [item.split()[0] for item in lines]
        assert lines == rpki_data
        assert len(final_ips) == len(rpki_data)


def test_merge_disjoint(tmp_path):
    '''
    Test merging non-overlapping sets of IP networks.
    '''
    main_data = generate_file_items(100)
    main_ips = [item.split()[0] for item in main_data]
    rpki_ips = main_ips[:50]
    irr_ips = main_ips[50:]
    irr_ips = make_disjoint(rpki_ips, irr_ips)
    rpki_data = build_file_lines(rpki_ips, generate_asns(len(rpki_ips)))
    irr_data = build_file_lines(irr_ips, generate_asns(len(irr_ips)))

    rpki_path, irr_path, out_path = __tmp_paths(tmp_path)
    generate_ip_file(rpki_path, rpki_data)
    generate_ip_file(irr_path, irr_data)
    general_merge(rpki_path, irr_path, None, out_path)

    with open(out_path, "r") as f:
        lines = f.readlines()
        final_ips = [item.split()[0] for item in lines]

    assert set(final_ips) == (set(irr_ips) | set(rpki_ips))


def test_merge_joint(tmp_path):
    '''
    Test merging overlapping sets of IP networks.
    '''
    overlap = 10
    rpki_data = generate_file_items(100)
    rpki_ips = [item.split()[0] for item in rpki_data]
    # generate subnets of the rpki networks that should get merged into the base file
    irr_ips = generate_subnets_from_base(rpki_ips, overlap)
    irr_data = build_file_lines(irr_ips, generate_asns(len(irr_ips)))

    rpki_path, irr_path, out_path = __tmp_paths(tmp_path)
    generate_ip_file(rpki_path, rpki_data)
    generate_ip_file(irr_path, irr_data)
    general_merge(rpki_path, irr_path, None, out_path)

    with open(out_path, "r") as f:
        lines = f.readlines()
        final_ips = [item.split()[0] for item in lines]

    # no subnets from irr_ips are included in the final merged network list
    assert set(final_ips).isdisjoint(set(irr_ips))
