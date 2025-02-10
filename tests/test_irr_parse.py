from pathlib import Path

from kartograf.irr.parse import parse_irr
from .context import create_test_context, setup_test_data


def build_test_context(tmp_path):
    epoch = "111111112"
    context = create_test_context(tmp_path, epoch)
    setup_test_data(context)
    return context


def test_parse_basic(tmp_path):
    context = build_test_context(tmp_path)
    parse_irr(context)
    result_file = Path(context.out_dir_irr) / "irr_final.txt"
    assert result_file.exists()

    content = []
    with open(str(result_file), 'r') as f:
        for l in f.readlines():
            content.append(l.strip())
    assert content == ["193.254.30.0/24 AS12726", "212.166.64.0/19 AS12321", "212.80.191.0/24 AS12541"]
    # removed duplicate network with higher ASN
    assert "212.80.191.0/24 AS12542" not in content
