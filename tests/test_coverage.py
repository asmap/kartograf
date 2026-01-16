from pathlib import Path
import pytest
from kartograf.coverage import coverage


def fixtures():
    ip_list = str(Path(__file__).parent / "data/ip_list.txt")
    map_file = str(Path(__file__).parent / "data/map_file.txt")
    return map_file, ip_list

def test_coverage(capsys):
    map_file_path, ip_list_path = fixtures()
    with open(map_file_path, 'r') as f:
        map_items = f.readlines()
    with open(ip_list_path, 'r') as f:
        ip_items = f.readlines()

    coverage(map_items, ip_items)
    captured = capsys.readouterr()
    assert "A total of 2 IPs out of 3 are covered by the map. That's 66.67%" in captured.out

    ip_items.append("averylongnotipaddrstring.onion")
    with pytest.raises(ValueError):
        coverage(map_items, ip_items)
        captured = capsys.readouterr()
        assert "Invalid IPv4/IPv6 address provided" in captured.err

    map_items.append("averylongnotipaddrstring.onion")
    with pytest.raises(ValueError):
        coverage(map_items, ip_items)
        captured = capsys.readouterr()
        assert "Invalid IP network provided" in captured.err

def test_covered_ips_output():
    map_file_path, ip_list_path = fixtures()
    cov_output_file = "cov_output.txt"
    with open(map_file_path, 'r') as f:
        map_items = f.readlines()
    with open(ip_list_path, 'r') as f:
        ip_items = f.readlines()
    coverage(map_items, ip_items, output_covered=cov_output_file, output_uncovered=None)
    with open(cov_output_file, 'r') as f:
        cov_output = f.readlines()
    assert "192.253.209.69 AS12389\n" in cov_output

def test_not_covered_ips_output():
    map_file_path, ip_list_path = fixtures()
    cov_output_file = "not_cov_output.txt"
    with open(map_file_path, 'r') as f:
        map_items = f.readlines()
    with open(ip_list_path, 'r') as f:
        ip_items = f.readlines()
    coverage(map_items, ip_items, output_covered=None, output_uncovered=cov_output_file)
    with open(cov_output_file, 'r') as f:
        cov_output = f.readlines()
    assert "134.26.21.1\n" in cov_output
