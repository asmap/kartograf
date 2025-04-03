from pathlib import Path

from kartograf.collectors.parse import parse_routeviews_pfx2as
from .context import create_test_context

import shutil

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

