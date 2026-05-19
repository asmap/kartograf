import os
from pathlib import Path
import pytest
from kartograf.context import Context
from kartograf.cli import create_parser

@pytest.fixture(name="parser")
def fixture_parser():
    return create_parser()

def test_basic_map_context(parser, tmp_path):
    args = parser.parse_args(['map'])
    os.chdir(tmp_path)  # Use temporary directory
    context = Context(args)

    assert context.args.command == 'map'
    assert context.reproduce is False
    assert context.args.debug is False
    assert context.args.wipe_data_dir is False
    assert context.args.irr is False
    assert context.args.routeviews is False
    assert context.stable_repos is False
    assert not context.cleanup_out_files
    assert isinstance(context.epoch, str)
    assert isinstance(int(context.epoch), int)
    assert context.max_encode == 33521664
    assert Path(context.debug_log).name == ''

def test_map_context_with_reproduce(parser, tmp_path):
    # Setup a mock reproduction directory
    repro_path = tmp_path / "repro"
    repro_path.mkdir()
    (repro_path / "irr").mkdir()
    (repro_path / "collectors").mkdir()

    args = parser.parse_args(['map', '-r', str(repro_path), '-t', '1225411200'])
    context = Context(args)

    assert context.reproduce is True
    assert context.epoch == '1225411200'
    assert context.epoch_dir == 'r1225411200'
    assert context.args.irr is True  # Should be True since irr dir exists
    assert Path(context.data_dir_irr).exists()
    assert context.args.routeviews is True  # Should be True since collectors dir exists
    assert Path(context.data_dir_collectors).exists()
    assert context.args.custom_source is None  # No custom dir in repro

def test_map_context_with_reproduce_custom(parser, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    repro_path = tmp_path / "repro"
    repro_path.mkdir()
    (repro_path / "custom").mkdir()
    (repro_path / "custom" / "custom_source.txt").write_text("1.0.0.0/24 AS13335\n")

    args = parser.parse_args(['map', '-r', str(repro_path), '-t', '1225411201'])
    context = Context(args)

    assert context.args.custom_source is not None
    assert context.args.custom_source.endswith("custom/custom_source.txt")
    assert Path(context.args.custom_source).exists()

def test_map_context_reproduce_overrides_custom_source(parser, tmp_path, monkeypatch):
    """
    In reproduce mode input-related arguments are derived from the reproduction
    directory. If --custom-source is passed but the reproduction directory has
    no custom/ subfolder, args.custom_source must be reset to None to avoid
    parsing a file that was not part of the original run.
    """
    monkeypatch.chdir(tmp_path)
    repro_path = tmp_path / "repro"
    repro_path.mkdir()
    unrelated = tmp_path / "unrelated.txt"
    unrelated.write_text("1.0.0.0/24 AS13335\n")

    args = parser.parse_args(
        ['map', '-r', str(repro_path), '-t', '1225411202', '-cs', str(unrelated)]
    )
    context = Context(args)

    assert context.args.custom_source is None

def test_map_context_with_wait(parser, tmp_path):
    args = parser.parse_args(['map', '-w', '1225411200'])
    os.chdir(tmp_path)
    context = Context(args)

    assert context.epoch == '1225411200'
    assert context.epoch_dir == '1225411200'
    assert not context.reproduce

def test_map_stable_repos(parser, tmp_path):
    args = parser.parse_args(['map', '-s'])
    os.chdir(tmp_path)
    context = Context(args)

    assert context.stable_repos is True

def test_directory_creation(parser, tmp_path):
    args = parser.parse_args(['map', '-irr', '-rv'])
    os.chdir(tmp_path)
    context = Context(args)

    assert Path(context.data_dir).is_absolute()

    rpki_cache = context.data_dir_rpki_cache
    assert isinstance(rpki_cache, str)
    assert Path(rpki_cache).exists()
    assert Path(rpki_cache).parent.name == "rpki"

    rpki_tals = context.data_dir_rpki_tals
    assert isinstance(rpki_tals, str)
    assert Path(rpki_tals).exists()
    assert Path(rpki_tals).parent.name == "rpki"

    data_dir_irr = context.data_dir_irr
    assert isinstance(data_dir_irr, str)
    assert Path(data_dir_irr).exists()
    assert Path(data_dir_irr).name == "irr"

    data_dir_collectors = context.data_dir_collectors
    assert isinstance(data_dir_collectors, str)
    assert Path(data_dir_collectors).exists()
    assert Path(data_dir_collectors).name == "collectors"

    out_dir_rpki = context.out_dir_rpki
    assert isinstance(out_dir_rpki, str)
    assert Path(out_dir_rpki).exists()
    assert Path(out_dir_rpki).name == "rpki"

    out_dir_irr = context.out_dir_irr
    assert isinstance(out_dir_irr, str)
    assert Path(out_dir_irr).exists()
    assert Path(out_dir_irr).name == "irr"

    out_dir_collectors = context.out_dir_collectors
    assert isinstance(out_dir_collectors, str)
    assert Path(out_dir_collectors).exists()
    assert Path(out_dir_collectors).name == "collectors"
