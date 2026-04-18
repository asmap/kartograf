import json

import pytest

from kartograf.rpki.normalize import normalize_rpki_json


def test_normalize_legacy_filters_and_orders(tmp_path):
    input_path = tmp_path / "legacy.json"
    output_path = tmp_path / "normalized.json"

    legacy_payload = [
        {
            "type": "roa",
            "validation": "OK",
            "valid_until": 100,
            "vrps": [
                {"prefix": "2.2.2.0/24", "asid": 64500, "maxlen": 24},
                {"prefix": "1.1.1.0/24", "asid": 13335, "maxlen": 24},
            ],
        },
        {
            "type": "roa",
            "validation": "FAIL",
            "valid_until": 100,
            "vrps": [{"prefix": "3.3.3.0/24", "asid": 64501, "maxlen": 24}],
        },
        {
            "type": "manifest",
            "validation": "OK",
            "valid_until": 100,
            "vrps": [{"prefix": "4.4.4.0/24", "asid": 64502, "maxlen": 24}],
        },
    ]

    with open(input_path, "w", encoding="utf-8") as f:
        json.dump(legacy_payload, f)

    count = normalize_rpki_json(input_path, output_path)

    with open(output_path, "r", encoding="utf-8") as f:
        normalized = json.load(f)

    assert count == 2
    assert normalized == [
        {"prefix": "1.1.1.0/24", "asn": 13335, "expires": 100},
        {"prefix": "2.2.2.0/24", "asn": 64500, "expires": 100},
    ]


def test_normalize_legacy_prefers_expires_when_present(tmp_path):
    input_path = tmp_path / "legacy_with_expires.json"
    output_path = tmp_path / "normalized.json"

    legacy_payload = [
        {
            "type": "roa",
            "validation": "OK",
            "valid_until": 999,
            "expires": 123,
            "vrps": [
                {"prefix": "1.1.1.0/24", "asid": 13335, "maxlen": 24},
            ],
        }
    ]

    with open(input_path, "w", encoding="utf-8") as f:
        json.dump(legacy_payload, f)

    count = normalize_rpki_json(input_path, output_path)

    with open(output_path, "r", encoding="utf-8") as f:
        normalized = json.load(f)

    assert count == 1
    assert normalized == [
        {"prefix": "1.1.1.0/24", "asn": 13335, "expires": 123},
    ]


def test_normalize_threaded_supports_expiry_alias(tmp_path):
    input_path = tmp_path / "threaded.json"
    output_path = tmp_path / "normalized.json"

    threaded_payload = {
        "roas": [
            {"prefix": "9.9.9.0/24", "asn": 19281, "expiry": 222},
            {"prefix": "8.8.8.0/24", "asn": 15169, "expires": 333},
        ]
    }

    with open(input_path, "w", encoding="utf-8") as f:
        json.dump(threaded_payload, f)

    count = normalize_rpki_json(input_path, output_path)

    with open(output_path, "r", encoding="utf-8") as f:
        normalized = json.load(f)

    assert count == 2
    assert normalized == [
        {"prefix": "8.8.8.0/24", "asn": 15169, "expires": 333},
        {"prefix": "9.9.9.0/24", "asn": 19281, "expires": 222},
    ]


def test_normalize_rejects_unknown_root_json(tmp_path):
    input_path = tmp_path / "invalid.json"
    output_path = tmp_path / "normalized.json"

    input_path.write_text('"unexpected"', encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported RPKI JSON format"):
        normalize_rpki_json(input_path, output_path)


def test_normalize_skips_non_string_prefix_values(tmp_path):
    input_path = tmp_path / "legacy_bad_prefix.json"
    output_path = tmp_path / "normalized.json"

    payload = [
        {
            "type": "roa",
            "validation": "OK",
            "valid_until": 100,
            "vrps": [
                {"prefix": None, "asid": 64500, "maxlen": 24},
                {"prefix": 123, "asid": 64501, "maxlen": 24},
                {"prefix": "1.1.1.0/24", "asid": 13335, "maxlen": 24},
            ],
        }
    ]

    with open(input_path, "w", encoding="utf-8") as f:
        json.dump(payload, f)

    count = normalize_rpki_json(input_path, output_path)

    with open(output_path, "r", encoding="utf-8") as f:
        normalized = json.load(f)

    assert count == 1
    assert normalized == [{"prefix": "1.1.1.0/24", "asn": 13335, "expires": 100}]
