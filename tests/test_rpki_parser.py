import json
import os

from kartograf.rpki.parse import parse_rpki
from .context import create_test_context, setup_test_data


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
    setup_test_data(context)
    parse_rpki(context)

    # Check that rpki_final.txt was created
    final_path = os.path.join(context.out_dir_rpki, "rpki_final.txt")
    assert os.path.exists(final_path), "rpki_final.txt should exist"

    # Count entries in final output
    with open(final_path, "r") as f:
        final_lines = [line.strip() for line in f.readlines()]

    captured = capsys.readouterr()

    assert len(final_lines) == 10, "Should have found 10 valid ROAs"
    assert "Result entries written: 10" in captured.out
    assert "Duplicates found: 5" in captured.out
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


def test_roa_valid_until_fallback(tmp_path):
    '''Test ROA selection falls back to later valid_until'''
    epoch = "111111111"
    context = create_test_context(tmp_path, epoch)
    setup_test_data(context)
    parse_rpki(context)

    final_path = os.path.join(context.out_dir_rpki, "rpki_final.txt")
    with open(final_path, "r") as f:
        entries = [line.strip() for line in f.readlines()]

    assert "101.0.1.0/24 AS11102" in entries, "ROA with later valid_until should be selected"
    assert not any("101.0.1.0/24 AS11101" in e for e in entries), "ROA with earlier valid_until should not be selected"


def test_roa_valid_since_fallback(tmp_path):
    '''Test ROA selection falls back to later valid_since when valid_until matches'''
    epoch = "111111111"
    context = create_test_context(tmp_path, epoch)
    setup_test_data(context)
    parse_rpki(context)

    final_path = os.path.join(context.out_dir_rpki, "rpki_final.txt")
    with open(final_path, "r") as f:
        entries = [line.strip() for line in f.readlines()]

    assert "102.0.100.0/24 AS11104" in entries, "ROA with later valid_since should be selected"
    assert not any("102.0.100.0/24 AS11103" in e for e in entries), "ROA with earlier valid_since should not be selected"


def test_roa_asn_fallback(tmp_path):
    '''Test ROA selection falls back to lower ASN when timestamps match'''
    epoch = "111111111"
    context = create_test_context(tmp_path, epoch)
    setup_test_data(context)
    parse_rpki(context)

    final_path = os.path.join(context.out_dir_rpki, "rpki_final.txt")
    with open(final_path, "r") as f:
        entries = [line.strip() for line in f.readlines()]

    assert "103.0.1.0/24 AS11105" in entries, "ROA with lower ASN should be selected"
    assert not any("103.0.1.0/24 AS11106" in e for e in entries), "ROA with higher ASN should not be selected"
