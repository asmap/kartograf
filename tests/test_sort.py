from pathlib import Path

from kartograf.sort import sort_result_by_pfx
from .context import create_test_context


def test_sort_prunes_and_orders_result(tmp_path, capsys):
    context = create_test_context(tmp_path, "111111113")
    # The /24 only became redundant when the merge added the /23
    unsorted = Path(context.out_dir_rpki) / "rpki_final.txt"
    unsorted.write_text("10.0.1.0/24 AS2\n10.0.0.0/24 AS1\n10.0.0.0/23 AS1\n2001:db8::/32 AS3\n")

    sort_result_by_pfx(context)

    result = Path(context.final_result_file).read_text()
    assert result == "10.0.0.0/23 AS1\n10.0.1.0/24 AS2\n2001:db8::/32 AS3\n"
    assert "Redundant entries pruned: 1" in capsys.readouterr().out
