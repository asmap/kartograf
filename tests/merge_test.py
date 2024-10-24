from generate_data import (
    build_file_lines,
    generate_ip_file,
    generate_file_items,
    generate_asns,
    generate_subnets_from_base,
    make_disjoint
)

from kartograf.merge import general_merge

def __tmp_paths(tmp_path):
    return [tmp_path / p for p in ["rpki_final.txt", "irr_final.txt", "out.txt"]]

def test_merge(tmp_path):
    """
    Assert that merging two identical files is a no-op.
    """
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
    """
    Test merging non-overlapping sets of IP networks.
    """
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
    """
    Test merging overlapping sets of IP networks.
    """
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
