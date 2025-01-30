import json
import os

from kartograf.rpki.parse import parse_rpki
from .context import create_test_context
from .util.helpers import flatten


def prefixes_from_vrps(vrps):
    pfxs = []
    for items in vrps:
        if 'prefix' in items.keys():
            pfxs.append(items['prefix'])
    return pfxs


def test_roa_validations(tmp_path, capsys):
    '''
    The ROA validation informs the user of invalids, incompletes, not-ROAs etc
    but not data is returned to that effect, so we test stdout's messages.
    We assert on the length of the output file, and assert on duplicates.
    The fixtures file should output 7 entries, with 2 duplicates, 1 not-ROA, and
    1 invalid entry.
    '''
    epoch = "111111111"
    context = create_test_context(tmp_path, epoch)
    parse_rpki(context)

    # Check that rpki_final.txt was created
    final_path = os.path.join(context.out_dir_rpki, "rpki_final.txt")
    assert os.path.exists(final_path), "rpki_final.txt should exist"

    # Read the raw JSON to compare counts
    with open(os.path.join(context.out_dir_rpki, "rpki_raw.json"), "r") as f:
        raw_data = json.load(f)

    # Count entries in final output
    with open(final_path, "r") as f:
        final_lines = f.readlines()

    # Count of duplicates should be the count of final output minus the count
    # of unique prefixes in the raw data
    prefixes = [prefixes_from_vrps(roa['vrps']) for roa in raw_data]
    duplicates = len(set(flatten(prefixes))) - len(final_lines)

    captured = capsys.readouterr()
    assert len(final_lines) == 7, "Should have found 7 valid ROAs"
    assert duplicates == 2, "Should have found 2 duplicates"
    assert "Result entries written: 7" in captured.out
    assert "Duplicates found: 2" in captured.out
    assert "Invalids found: 1" in captured.out
    assert "Incompletes: 0" in captured.out
    assert "Non-ROA files: 1" in captured.out

def test_roa_incompletes(tmp_path, capsys):
    '''
    Test that the ROA file has missing entries.
    The data is mocked here and written to a json file.
    '''
    epoch = "111111112"
    context = create_test_context(tmp_path, epoch)
    test_data = [
        {
            "type": "roa",
            "validation": "OK",
            "ski": "some-ski",
            "vrps": [{"prefix": "192.0.2.0/24", "asid": "64496", "maxlen": "24"}],
            "valid_until": "1234567890",
            "valid_since": "1234567880"
        },
        {
            "type": "roa",
            "validation": "OK",
            "ski": "some-ski",
            "vrps": [{"prefix": "198.51.100.0/24", "asid": "64497", "maxlen": "24"}],
            "valid_until": "1234567890",
            "valid_since": "1234567880"
        }
    ]

    # Write test data to rpki_raw.json
    with open(os.path.join(context.out_dir_rpki, "rpki_raw.json"), "w") as f:
        json.dump(test_data, f)

    parse_rpki(context)

    # Check that rpki_final.txt was created
    final_path = os.path.join(context.out_dir_rpki, "rpki_final.txt")
    assert os.path.exists(final_path), "rpki_final.txt should exist"

    # Count entries in final output
    with open(final_path, "r") as f:
        final_lines = f.readlines()

    assert len(final_lines) == 0, "No rows should be written"
    captured = capsys.readouterr()
    assert "Incompletes: 2" in captured.out
