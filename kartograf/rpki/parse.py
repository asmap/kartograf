from pathlib import Path
from typing import Dict, Tuple

import ijson
from ijson.common import IncompleteJSONError, JSONError

from kartograf.bogon import (
    is_bogon_pfx,
    is_bogon_asn,
    is_out_of_encoding_range,
)
from kartograf.timed import timed
from kartograf.util import KartografConfigurationError, parse_pfx


@timed
def parse_rpki(context):
    raw_input = Path(context.out_dir_rpki) / "rpki_raw.json"
    rpki_res = Path(context.out_dir_rpki) / "rpki_final.txt"

    output_cache: Dict[str, Tuple[int, int]] = {}

    dups_count = 0
    out_count = 0
    invalids = 0
    incompletes = 0
    total_records = 0

    print("Parsing normalized ROA records")

    try:
        with open(raw_input, "rb") as dump:
            for roa in ijson.items(dump, "item"):
                total_records += 1

                if not isinstance(roa, dict):
                    incompletes += 1
                    continue

                key_list = ["prefix", "asn", "expires"]
                if not all(key in roa for key in key_list):
                    incompletes += 1
                    continue

                prefix = parse_pfx(roa["prefix"])
                if not prefix:
                    if context.debug_log:
                        with open(context.debug_log, 'a') as logs:
                            logs.write(f"Could not parse prefix from line: {roa['prefix']}\n")
                    invalids += 1
                    continue

                try:
                    asn = int(roa["asn"])
                    expires = int(roa["expires"])
                except (TypeError, ValueError):
                    incompletes += 1
                    continue

                # Bogon prefixes and ASNs are excluded since they can not
                # be used for routing.
                if is_bogon_pfx(prefix) or is_bogon_asn(asn):
                    if context.debug_log:
                        with open(context.debug_log, 'a') as logs:
                            logs.write(f"RPKI: parser encountered an invalid IP network: {prefix}\n")
                    invalids += 1
                    continue

                if context.max_encode and is_out_of_encoding_range(asn, context.max_encode):
                    continue

                # Multiple ROAs for the same prefix are possible and we need
                # deterministic tie-breaking that works for both legacy and
                # threaded backends.
                if prefix in output_cache:
                    dups_count += 1
                    old_asn, old_expires = output_cache[prefix]

                    if expires > old_expires:
                        output_cache[prefix] = (asn, expires)
                    elif expires == old_expires and asn < old_asn:
                        output_cache[prefix] = (asn, expires)
                else:
                    output_cache[prefix] = (asn, expires)
    except (JSONError, IncompleteJSONError) as exc:
        raise KartografConfigurationError(
            "Malformed or truncated rpki_raw.json detected. "
            "Re-run validation to regenerate normalized RPKI data."
        ) from exc

    with open(rpki_res, "w") as asmap:
        for prefix, (asn, _) in sorted(output_cache.items()):
            line_out = f"{prefix} AS{asn}"

            asmap.write(line_out + '\n')
            out_count += 1

    context.cleanup_out_files.append(raw_input)

    print(f'Total records processed: {total_records}')
    print(f'Result entries written: {out_count}')
    print(f'Duplicates found: {dups_count}')
    print(f'Invalids found: {invalids}')
    print(f'Incompletes: {incompletes}')
