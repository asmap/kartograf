import pytest
from kartograf.rpki.fetch import validate_rpki_db
from .context import create_test_context


def test_no_rpki_files_exits(tmp_path, capsys):
    """
    When the RPKI cache directory contains no .roa files,
    validate_rpki_db should print an error and call sys.exit().
    """
    epoch = "999999999"
    context = create_test_context(tmp_path, epoch)

    with pytest.raises(SystemExit):
        validate_rpki_db(context)

    captured = capsys.readouterr()
    assert "No RPKI files found! Exiting." in captured.out
