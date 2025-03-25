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

    # Test expected set
    assert content == ["193.254.30.0/24 AS12726", "212.166.64.0/19 AS12321", "212.80.191.0/24 AS12541", "212.16.0.0/24 AS12346", "212.17.0.0/24 AS12347", "2345:2ca::/32 AS12345" ]
