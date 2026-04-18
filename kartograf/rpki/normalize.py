import json
from pathlib import Path
from typing import Iterator, NamedTuple

import ijson

from kartograf.util import parse_pfx


class NormalizedROA(NamedTuple):
    prefix: str
    asn: int
    expires: int


def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _detect_root_json_type(input_path: Path) -> str:
    with open(input_path, "rb") as src:
        while True:
            char = src.read(1)
            if not char:
                return ""
            if not char.isspace():
                return char.decode("utf-8", errors="ignore")


def _normalize_legacy_roa(roa: dict) -> Iterator[NormalizedROA]:
    if roa.get("type") != "roa" or roa.get("validation") != "OK":
        return

    # Legacy objects can include both valid_until and expires.
    # Prefer expires when available to match threaded output semantics.
    expires = _safe_int(roa.get("expires", roa.get("valid_until")))
    if expires is None:
        return

    for vrp in roa.get("vrps", []):
        prefix_raw = vrp.get("prefix")
        if not isinstance(prefix_raw, str):
            continue

        prefix = parse_pfx(prefix_raw)
        asn = _safe_int(vrp.get("asid"))
        if prefix and asn is not None:
            yield NormalizedROA(prefix=prefix, asn=asn, expires=expires)


def _normalize_threaded_roa(roa: dict) -> Iterator[NormalizedROA]:
    prefix_raw = roa.get("prefix")
    if not isinstance(prefix_raw, str):
        return

    prefix = parse_pfx(prefix_raw)
    asn = _safe_int(roa.get("asn"))
    expires = _safe_int(roa.get("expires", roa.get("expiry")))

    if prefix and asn is not None and expires is not None:
        yield NormalizedROA(prefix=prefix, asn=asn, expires=expires)


def iter_normalized_roas(input_path: Path) -> Iterator[NormalizedROA]:
    root_type = _detect_root_json_type(input_path)
    if root_type == "[":
        with open(input_path, "rb") as src:
            for roa in ijson.items(src, "item"):
                yield from _normalize_legacy_roa(roa)
        return

    if root_type == "{":
        with open(input_path, "rb") as src:
            for roa in ijson.items(src, "roas.item"):
                yield from _normalize_threaded_roa(roa)
        return

    raise ValueError(f"Unsupported RPKI JSON format in {input_path}")


def normalize_rpki_json(input_path: Path, output_path: Path) -> int:
    normalized = sorted(iter_normalized_roas(input_path), key=lambda roa: (roa.prefix, roa.asn, roa.expires))

    with open(output_path, "w", encoding="utf-8") as out:
        out.write("[")
        for idx, roa in enumerate(normalized):
            if idx > 0:
                out.write(",")
            out.write(
                json.dumps(
                    {"prefix": roa.prefix, "asn": roa.asn, "expires": roa.expires},
                    separators=(",", ":"),
                )
            )
        out.write("]")

    return len(normalized)