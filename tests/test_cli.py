from pathlib import Path
import pytest
from kartograf.cli import create_parser, main

@pytest.fixture(name="parser")
def fixture_parser():
    return create_parser()

def test_map_command(parser):
    args = parser.parse_args(['map'])
    assert args.command == 'map'
    assert args.debug is False # default is False
    assert args.wipe_data_dir is False  # default is False
    assert args.irr is False  # default is False
    assert args.routeviews is False  # default is False
    assert args.reproduce is None
    assert args.epoch is None
    assert args.max_encode == 33521664

def test_reproduce_args_failure(capsys):
    '''
    Both --reproduce and --epoch must be set if either one is set.
    A usage help text is returned with the error.
    '''
    args = ['map', '-r', '/path']
    with pytest.raises(SystemExit):
        main(args)
    captured = capsys.readouterr()
    assert "--epoch is required when --reproduce is set." in captured.err

    args = ['map', '-t', '123456789']
    with pytest.raises(SystemExit):
        main(args)
    captured = capsys.readouterr()
    assert "--reproduce is required when --epoch is set." in captured.err

def test_map_with_options(parser):
    args = parser.parse_args(['map', '-wd', '-irr', '-rv', '-r', '/path', '-t', '123'])
    assert args.wipe_data_dir is True
    assert args.irr is True
    assert args.routeviews is True
    assert args.reproduce == '/path'
    assert args.epoch == '123'

def test_stable_repos_flag(parser):
    args = parser.parse_args(['map'])
    assert args.stable_repos is False

    args = parser.parse_args(['map', '-s'])
    assert args.stable_repos is True

    args = parser.parse_args(['map', '--stable-repos'])
    assert args.stable_repos is True

def test_map_with_past_wait(capsys):
    args = ['map', '-w', '1225411200']
    with pytest.raises(SystemExit):
        main(args)
    captured = capsys.readouterr()
    assert "Cannot wait for a timestamp in the past (1225411200)" in captured.err

def test_merge_command(parser):
    args = parser.parse_args(['merge'])
    assert args.command == 'merge'
    assert args.base.endswith('base_file.txt')
    assert args.extra.endswith('extra_file.txt')
    assert args.output.endswith('out_file.txt')

def test_cov_command_error(parser, capsys):
    with pytest.raises(SystemExit):
        # Should fail without required arguments
        parser.parse_args(['cov'])
    captured = capsys.readouterr()
    assert captured.err.startswith("usage:")

def test_cov_conflicting_flags(parser, capsys):
    with pytest.raises(SystemExit):
        parser.parse_args(['cov', '-c', 'output.txt', '-uc', 'alsooutput.txt'])
    captured = capsys.readouterr()
    assert captured.err.startswith("usage:")

def test_cov_command(parser):
    fixtures_path = Path("tests/data")
    map_file_arg = Path(fixtures_path / "map_file.txt")
    ip_file_arg = Path(fixtures_path / "ip_list.txt")
    args = ["cov", str(map_file_arg), str(ip_file_arg), "-oc", "outputfile.txt"]
    parsed_args = parser.parse_args(args)
    assert parsed_args.map.name == str(map_file_arg)
    assert parsed_args.list.name == str(ip_file_arg)
    assert parsed_args.output_covered == "outputfile.txt"

def test_help(capsys):
    with pytest.raises(SystemExit) as e:
        main([])
    assert e.value.code == "Please provide a command."
    captured = capsys.readouterr()
    assert captured.out.startswith("usage:")

def test_invalid_command(parser, capsys):
    with pytest.raises(SystemExit):
        parser.parse_args(['invalid'])
    captured = capsys.readouterr()
    assert "invalid choice: 'invalid'" in captured.err

def test_version_flag(parser, capsys):
    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(['--version'])
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "version" in captured.out
