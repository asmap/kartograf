import json
import os
import pytest

from kartograf.rpki.parse import parse_rpki
from kartograf.util import KartografConfigurationError
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
    assert "Invalids found: 0" in captured.out
    assert "Incompletes: 0" in captured.out

def test_roa_incompletes(tmp_path, capsys):
    '''
    Test that the ROA file has missing entries.
    The data is mocked here and written to a json file.
    '''
    epoch = "111111112"
    context = create_test_context(tmp_path, epoch)
    test_data = [
        {
            "prefix": "192.0.2.0/24",
            "asn": "64496",
        },
        {
            "prefix": "198.51.100.0/24",
            "expires": "1234567890",
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


def test_roa_invalid_and_incomplete_counters(tmp_path, capsys):
    epoch = "111111113"
    context = create_test_context(tmp_path, epoch)
    test_data = [
        {
            "prefix": "1.1.1.0/24",
            "asn": 13335,
            "expires": 1234567890,
        },
        {
            "prefix": "10.0.0.0/8",
            "asn": 13335,
            "expires": 1234567890,
        },
        {
            "prefix": "2.2.2.0/24",
            "asn": "not_an_int",
            "expires": 1234567890,
        },
    ]

    with open(os.path.join(context.out_dir_rpki, "rpki_raw.json"), "w") as f:
        json.dump(test_data, f)

    parse_rpki(context)

    final_path = os.path.join(context.out_dir_rpki, "rpki_final.txt")
    with open(final_path, "r") as f:
        final_lines = [line.strip() for line in f.readlines()]

    captured = capsys.readouterr()
    assert final_lines == ["1.1.1.0/24 AS13335"]
    assert "Invalids found: 1" in captured.out
    assert "Incompletes: 1" in captured.out


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
    '''When expires match, strict parity fallback selects lowest ASN.'''
    epoch = "111111111"
    context = create_test_context(tmp_path, epoch)
    setup_test_data(context)
    parse_rpki(context)

    final_path = os.path.join(context.out_dir_rpki, "rpki_final.txt")
    with open(final_path, "r") as f:
        entries = [line.strip() for line in f.readlines()]

    assert "102.0.100.0/24 AS11103" in entries, "ROA with lower ASN should be selected when expires match"
    assert not any("102.0.100.0/24 AS11104" in e for e in entries), "ROA with higher ASN should not be selected when expires match"


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


def test_parse_rpki_accepts_threaded_context(tmp_path):
    epoch = "111111114"
    context = create_test_context(tmp_path, epoch)
    context.rpki_backend = "threaded"
    setup_test_data(context)

    parse_rpki(context)

    final_path = os.path.join(context.out_dir_rpki, "rpki_final.txt")
    assert os.path.exists(final_path)


def test_parse_rpki_rejects_truncated_json(tmp_path):
    epoch = "111111115"
    context = create_test_context(tmp_path, epoch)

    raw_path = os.path.join(context.out_dir_rpki, "rpki_raw.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write('[{"prefix":"1.1.1.0/24","asn":13335,"expires":1234567890}')

    with pytest.raises(KartografConfigurationError, match="Malformed or truncated rpki_raw.json"):
        parse_rpki(context)


def test_parse_rpki_handles_non_string_prefix_values(tmp_path, capsys):
    epoch = "111111116"
    context = create_test_context(tmp_path, epoch)

    test_data = [
        {"prefix": None, "asn": 64496, "expires": 1},
        {"prefix": 123, "asn": 64497, "expires": 1},
        {"prefix": "1.1.1.0/24", "asn": 13335, "expires": 1},
    ]

    with open(os.path.join(context.out_dir_rpki, "rpki_raw.json"), "w", encoding="utf-8") as f:
        json.dump(test_data, f)

    parse_rpki(context)

    final_path = os.path.join(context.out_dir_rpki, "rpki_final.txt")
    with open(final_path, "r", encoding="utf-8") as f:
        final_lines = [line.strip() for line in f.readlines()]

    captured = capsys.readouterr()
    assert final_lines == ["1.1.1.0/24 AS13335"]
    assert "Invalids found: 2" in captured.out
