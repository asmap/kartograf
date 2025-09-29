import json
from pathlib import Path
from typing import Dict

from kartograf.bogon import (
    is_bogon_pfx,
    is_bogon_asn,
    is_out_of_encoding_range,
)
from kartograf.timed import timed
from kartograf.util import parse_pfx


@timed
def parse_rpki(context):
    raw_input = Path(context.out_dir_rpki) / "rpki_raw.json"
    rpki_res = Path(context.out_dir_rpki) / "rpki_final.txt"

    output_cache: Dict[str, [str, str]] = {}

    dups_count = 0
    out_count = 0

    with open(raw_input, "r") as dump:
        data = json.loads(dump.read())
        print(f'Parsing {data["metadata"]["roas"]} ROAs')

        for roa in data["roas"]:
            asn = roa['asn']
            expiry = roa['expires']
            prefix = parse_pfx(roa['prefix'])

            # Bogon prefixes and ASNs are excluded since they can not
            # be used for routing.
            if not prefix or is_bogon_pfx(prefix) or is_bogon_asn(asn):
                if context.debug_log:
                    with open(context.debug_log, 'a') as logs:
                        logs.write(f"RPKI: parser encountered an invalid entry: {prefix} with ASN {asn}\n")
                continue

            if context.max_encode and is_out_of_encoding_range(asn, context.max_encode):
                continue

            # Multiple ROAs for the same prefix are possible and we need
            # to decide if we update the entry or not
            if output_cache.get(prefix):
                dups_count += 1
                # If the new ASN is from a ROA that is valid for longer,
                # we override the old entry with it
                [old_asn, old_expiry] = output_cache[prefix]
                if expiry > old_expiry:
                    output_cache[prefix] = [asn, expiry]
                # If the entries have the same validity period, we need to
                # choose a different tie breaker
                if expiry == old_expiry:
                    if int(asn) < int(old_asn):
                        output_cache[prefix] = [asn, expiry]
            else:
                # No duplicate, add to cache
                output_cache[prefix] = [asn, expiry]

    with open(rpki_res, "w") as asmap:
        for prefix, [asn, _] in output_cache.items():
            line_out = f"{prefix} AS{asn}"

            asmap.write(line_out + '\n')
            out_count += 1

    context.cleanup_out_files.append(raw_input)

    print(f'Result entries written: {out_count}')
    print(f'Duplicates found: {dups_count}')
