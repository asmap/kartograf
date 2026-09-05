from pathlib import Path

from kartograf.irr.parse import parse_irr
from .context import create_test_context, setup_test_data


def build_test_context(tmp_path):
    epoch = "111111112"
    context = create_test_context(tmp_path, epoch)
    setup_test_data(context)
    return context


def test_parse_validation_cases(tmp_path):
    """
    Test various IRR parsing validation cases.
    """
    context = build_test_context(tmp_path)
    parse_irr(context)

    result_file = Path(context.out_dir_irr) / "irr_final.txt"

    with open(str(result_file), 'r') as f:
        content = [l.strip() for l in f.readlines()]

    assert result_file.exists()

    # Test duplicate network, newer timestamp wins
    assert "212.16.0.0/24 AS12346" in content
    assert "212.16.0.0/24 AS12345" not in content

    # Test same timestamp resolution, lower ASN wins
    assert "212.17.0.0/24 AS12347" in content
    assert "212.17.0.0/24 AS12348" not in content

    # Test IPv6 inclusion
    assert "2345:2ca::/32 AS12345" in content

    # Test wrong source exclusion: ARIN in RIPE file
    assert "212.18.0.0/24 AS12345" not in content

    # Test incomplete entry (no source in data)
    assert "212.19.0.0/24 AS12345" not in content

    # Last complete object has no trailing blank in the fixture
    assert "212.20.0.0/24 AS12345" in content

    # Test expected set, the output is sorted by IP version and network
    assert content == ["193.254.30.0/24 AS12726", "212.16.0.0/24 AS12346", "212.17.0.0/24 AS12347", "212.20.0.0/24 AS12345", "212.80.191.0/24 AS12541", "212.166.64.0/19 AS12321", "2345:2ca::/32 AS12345"]


def test_parse_prunes_same_asn_more_specifics(tmp_path, capsys):
    context = create_test_context(tmp_path, "111111113")
    irr_file = Path(context.out_dir_irr) / "irr_ripe_nested.txt"
    irr_file.write_text(
        "route:          212.100.0.0/23\n"
        "origin:         AS1\n"
        "source:         RIPE\n"
        "\n"
        "route:          212.100.0.0/24\n"
        "origin:         AS1\n"
        "source:         RIPE\n"
        "\n"
        "route:          212.100.1.0/24\n"
        "origin:         AS2\n"
        "source:         RIPE\n"
    )

    parse_irr(context)

    result_file = Path(context.out_dir_irr) / "irr_final.txt"
    with open(str(result_file), 'r') as f:
        content = [l.strip() for l in f.readlines()]

    assert content == ["212.100.0.0/23 AS1", "212.100.1.0/24 AS2"]
    captured = capsys.readouterr()
    assert "Found valid, unique entries: 3" in captured.out
    assert "Redundant entries pruned: 1" in captured.out
