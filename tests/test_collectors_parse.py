from pathlib import Path
import shutil

from kartograf.collectors.parse import parse_routeviews_pfx2as
from .context import create_test_context

def build_test_context(tmp_path):
    epoch = "111111112"
    context = create_test_context(tmp_path, epoch)
    return context

def fixtures():
    return ["pfx2asn.txt"]

def setup_collectors_fixtures(context):
    fixtures_path = Path(__file__).parent / "data"
    for file in fixtures():
        shutil.copy2(Path(fixtures_path) / file, context.out_dir_collectors)

def test_parse(tmp_path):
    context = build_test_context(tmp_path)
    setup_collectors_fixtures(context)
    parse_routeviews_pfx2as(context)

    result_file = Path(context.out_dir_collectors) / "pfx2asn_clean.txt"

    assert result_file.exists()

    with open(result_file, 'r') as f:
        results = [l.strip() for l in f.readlines()]

    assert "127.0.0.0/24 AS12345" not in results
    assert "2001:db8::/32 AS54321" not in results
    assert "2ab1:db8::/32 AS33521665" not in results

    assert results == ["1.0.0.0/24 AS13335", "1.0.4.0/24 AS38803", "1.0.16.0/24 AS2519"]
