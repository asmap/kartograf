import json
import os
import pytest

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
    The fixtures file should output 8 entries, with 5 duplicates, 1 not-ROA,
    1 invalid entry and 2 entries pruned because they sit inside
    2602:fd60::/44 which maps to the same ASN.
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

    assert len(final_lines) == 8, "Should have written 8 entries"
    assert "2602:fd60::/44 AS396503" in final_lines
    assert "2602:fd60:e::/48 AS396503" not in final_lines
    assert "2602:fd60:7::/48 AS396503" not in final_lines
    assert "2602:fd60:11::/48 AS49134" in final_lines
    assert "Result entries written: 8" in captured.out
    assert "Redundant entries pruned: 2" in captured.out
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
    valid = {
            "type": "roa",
            "validation": "OK",
            "aki": "some-aki",
            "ski": "some-ski",
            "vrps": [{"prefix": "192.0.1.0/24", "asid": "64495", "maxlen": "24"}],
            "valid_until": "1234567890",
            "valid_since": "1234567880"
        }

    incompletes = [
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
        json.dump(incompletes + [valid], f)

    parse_rpki(context)

    # Check that rpki_final.txt was created
    final_path = os.path.join(context.out_dir_rpki, "rpki_final.txt")
    assert os.path.exists(final_path), "rpki_final.txt should exist"

    # Count entries in final output
    with open(final_path, "r") as f:
        final_lines = f.readlines()

    assert len(final_lines) == 1, "Only 1 row should be written"
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

def test_no_valid_output_exits(tmp_path, capsys):
    """
    When all ROAs in the input are filtered out (e.g. all incomplete
    or all failed validation), parse_rpki should exit with code 1.
    """
    epoch = "111111113"
    context = create_test_context(tmp_path, epoch)

    # Every ROA is missing required keys — all get classified as "incomplete"
    test_data = [
        {
            "type": "roa",
            "validation": "OK",
        },
        {
            "type": "roa",
            "validation": "OK",
        },
        {
            "type": "roa",
            "validation": "Failed"
        },
    ]

    with open(os.path.join(context.out_dir_rpki, "rpki_raw.json"), "w") as f:
        json.dump(test_data, f)

    with pytest.raises(SystemExit) as exc_info:
        parse_rpki(context)

    captured = capsys.readouterr()
    assert "No valid RPKI assignments found! Exiting." in captured.out
    assert exc_info.value.code == 1
