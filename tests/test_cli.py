import pytest
from kartograf.cli import create_parser

parser = create_parser()

def test_map_command():
    args = parser.parse_args(['map'])
    assert args.command == 'map'
    assert args.debug is True  # default is True
    assert args.cleanup is False  # default is False
    assert args.irr is False  # default is False
    assert args.routeviews is False  # default is False
    assert args.reproduce is None
    assert args.epoch is None
    assert args.max_encode == 33521664

def test_map_with_options():
    args = parser.parse_args(['map', '-c', '-irr', '-rv', '-r', '/path', '-t', '123'])
    assert args.cleanup is True
    assert args.irr is True
    assert args.routeviews is True
    assert args.reproduce == '/path'
    assert args.epoch == '123'

def test_merge_command():
    args = parser.parse_args(['merge'])
    assert args.command == 'merge'
    assert args.base.endswith('base_file.txt')
    assert args.extra.endswith('extra_file.txt')
    assert args.output.endswith('out_file.txt')

def test_cov_command(capsys):
    with pytest.raises(SystemExit):
        # Should fail without required arguments
        parser.parse_args(['cov'])
    captured = capsys.readouterr()
    assert captured.err.startswith("usage:")

def test_invalid_command(capsys):
    with pytest.raises(SystemExit):
        parser.parse_args(['invalid'])
    captured = capsys.readouterr()
    assert captured.err.startswith("usage:")

def test_version_flag(capsys):
    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(['--version'])
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "version" in captured.out
