import os
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
    assert context.debug_log.endswith('debug.log')

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
    assert context.args.routeviews is True  # Should be True since collectors dir exists

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

    assert os.path.exists(context.data_dir_rpki_cache)
    assert os.path.exists(context.data_dir_rpki_tals)
    assert os.path.exists(context.data_dir_irr)
    assert os.path.exists(context.data_dir_collectors)
    assert os.path.exists(context.out_dir_rpki)
    assert os.path.exists(context.out_dir_irr)
    assert os.path.exists(context.out_dir_collectors)
