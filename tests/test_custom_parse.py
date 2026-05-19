from pathlib import Path
import shutil

from kartograf.custom.parse import parse_custom_source
from .context import create_test_context


def build_test_context(tmp_path, epoch="111111113"):
    context = create_test_context(tmp_path, epoch)
    return context


def setup_custom_fixtures(context, fixture_name="custom_source.txt"):
    fixtures_path = Path(__file__).parent / "data"
    shutil.copy2(fixtures_path / fixture_name,
                 Path(context.data_dir_custom) / "custom_source.txt")


def read_clean_file(context):
    result_file = Path(context.out_dir_custom) / "custom_clean.txt"
    assert result_file.exists()
    with open(result_file, 'r') as f:
        return [l.strip() for l in f.readlines()]


def test_parse(tmp_path):
    """
    The fixture exercises all filter paths: valid entries, ASN normalization
    (with and without the "AS" prefix), bogon v4, bogon v6, out-of-range ASN,
    a malformed line, and a duplicate prefix.
    """
    context = build_test_context(tmp_path)
    setup_custom_fixtures(context)
    parse_custom_source(context)

    results = read_clean_file(context)

    assert results == [
        "1.0.0.0/24 AS13335",
        "1.0.4.0/22 AS38803",
        "2001:200::/32 AS2500",
        "1.0.16.0/24 AS2519",
    ]


def test_parse_empty_file(tmp_path):
    context = build_test_context(tmp_path, epoch="111111114")
    (Path(context.data_dir_custom) / "custom_source.txt").touch()

    parse_custom_source(context)

    assert read_clean_file(context) == []


def test_parse_duplicate_prefixes_keeps_first(tmp_path):
    """
    All ASNs used here are valid (non-bogon, within encoding range) so the
    second occurrence of each prefix reaches the dedup step rather than being
    rejected earlier as invalid.
    """
    context = build_test_context(tmp_path, epoch="111111116")
    content = "\n".join([
        "1.0.0.0/24 AS13335",
        "1.0.0.0/24 AS15169",
        "2001:200::/32 AS2500",
        "2001:200::/32 AS38803",
    ]) + "\n"
    (Path(context.data_dir_custom) / "custom_source.txt").write_text(content)

    parse_custom_source(context)

    assert read_clean_file(context) == [
        "1.0.0.0/24 AS13335",
        "2001:200::/32 AS2500",
    ]


def test_parse_writes_debug_log(tmp_path):
    context = build_test_context(tmp_path, epoch="111111117")
    debug_log = Path(context.out_dir) / "debug.log"
    context.debug_log = str(debug_log)
    setup_custom_fixtures(context)

    parse_custom_source(context)

    log_contents = debug_log.read_text()
    assert "malformed line" in log_contents
    assert "invalid entry" in log_contents
    assert "duplicate prefix" in log_contents
