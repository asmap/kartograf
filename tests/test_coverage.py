from pathlib import Path
import pytest
from kartograf.coverage import coverage


def fixtures():
    map_file = str(Path(__file__).parent / "data/map_file.txt")
    map_file_invalid = str(Path(__file__).parent / "data/map_file_invalid.txt")
    ip_list = str(Path(__file__).parent / "data/ip_list.txt")
    ip_list_invalid = str(Path(__file__).parent / "data/ip_list_invalid.txt")
    return map_file, map_file_invalid, ip_list, ip_list_invalid

def test_coverage(capsys):
    map_file_path, map_file_invalid_path, ip_list_path, ip_list_invalid_path = fixtures()

    with open(map_file_path, 'r') as map_file, open(ip_list_path, 'r') as ip_file:
        coverage(map_file, ip_file)
        captured = capsys.readouterr()
        assert "A total of 2 IPs out of 3 are covered by the map. That's 66.67%" in captured.out

    with open(map_file_path, 'r') as map_file, open(ip_list_invalid_path, 'r') as ip_file_invalid:
        with pytest.raises(SystemExit):
            coverage(map_file, ip_file_invalid)
            captured = capsys.readouterr()
            assert "Invalid IPv4/IPv6 address provided" in captured.err

    with open(map_file_invalid_path, 'r') as map_file_invalid, open(ip_list_path, 'r') as ip_file:
        with pytest.raises(SystemExit):
            coverage(map_file_invalid, ip_file)
            captured = capsys.readouterr()
            assert "Input file" in captured.err

def test_covered_ips_output():
    map_file_path, _, ip_list_path, _ = fixtures()
    cov_output_file = "cov_output.txt"
    with open(map_file_path, 'r') as map_file, open(ip_list_path, 'r') as ip_file:
        coverage(map_file, ip_file, output_covered=cov_output_file, output_uncovered=None)
    with open(cov_output_file, 'r') as f:
        cov_output = f.readlines()
    assert "192.253.209.69 AS12389\n" in cov_output

def test_not_covered_ips_output():
    map_file_path, _, ip_list_path, _ = fixtures()
    cov_output_file = "not_cov_output.txt"
    with open(map_file_path, 'r') as map_file, open(ip_list_path, 'r') as ip_file:
        coverage(map_file, ip_file, output_covered=None, output_uncovered=cov_output_file)
    with open(cov_output_file, 'r') as f:
        cov_output = f.readlines()
    assert "134.26.21.1\n" in cov_output
