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
    assert context.args.debug is True
    assert context.args.cleanup is False
    assert context.args.irr is False
    assert context.args.routeviews is False
    assert isinstance(context.epoch, str)
    assert isinstance(int(context.epoch), int)
    assert context.max_encode == 33521664
    assert Path(context.debug_log).name == 'debug.log'

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

def test_map_context_with_wait(parser, tmp_path):
    args = parser.parse_args(['map', '-w', '1225411200'])
    os.chdir(tmp_path)
    context = Context(args)

    assert context.epoch == '1225411200'
    assert context.epoch_dir == '1225411200'
    assert not context.reproduce

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
