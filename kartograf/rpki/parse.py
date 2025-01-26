import json
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
    raw_input = f"{context.out_dir_rpki}rpki_raw.json"
    rpki_res = f"{context.out_dir_rpki}rpki_final.txt"

    output_cache: Dict[str, [str, str]] = {}

    dups_count = 0
    out_count = 0
    invalids = 0
    incompletes = 0
    not_roas = 0

    with open(raw_input, "r") as dump:
        data = json.loads(dump.read())
        print(f'Parsing {len(data)} ROAs')

        for roa in data:
            # Sometimes ROAs are incomplete and we have to skip them
            key_list = [
                'type',
                'validation',
                'aki',
                'ski',
                'vrps',
                'valid_until'
            ]
            if not all(key in roa for key in key_list):
                incompletes += 1
                continue

            # We are only interested in ROAs
            if roa['type'] != "roa":
                not_roas += 1
                continue

            # We are only interested in valid ROAs
            if roa['validation'] != "OK":
                invalids += 1
                continue

            valid_until = roa['valid_until']
            valid_since = roa['valid_since']

            for vrp in roa['vrps']:
                asn = vrp['asid']
                prefix = parse_pfx(vrp['prefix'])

                # Bogon prefixes and ASNs are excluded since they can not
                # be used for routing.
                if not prefix or is_bogon_pfx(prefix) or is_bogon_asn(asn):
                    if context.debug_log:
                        with open(context.debug_log, 'a') as logs:
                            logs.write(f"RPKI: parser encountered an invalid IP network: {prefix}")
                    continue

                if context.max_encode and is_out_of_encoding_range(asn, context.max_encode):
                    continue

                # Multiple ROAs for the same prefix are possible and we need
                # to decide if we update the entry or not
                if output_cache.get(prefix):
                    dups_count += 1
                    # If the new ASN is from a ROA that is valid for longer,
                    # we override the old entry with it
                    [old_asn, old_valid_until, old_valid_since] = output_cache[prefix]
                    if int(valid_until) > int(old_valid_until):
                        output_cache[prefix] = [asn, valid_until, valid_since]
                    # If the entries have the same validity period, we need to
                    # choose a different tie breaker
                    if int(valid_until) == int(old_valid_until):
                        # Prefer the ROA that was announced last
                        if int(valid_since) > int(old_valid_since):
                            output_cache[prefix] = [asn, valid_until, valid_since]
                        # If the ROAs were also announced at the same time, we
                        # fall back to using the lower ASN just to be
                        # deterministic
                        if int(valid_since) == int(old_valid_since):
                            if int(asn) < int(old_asn):
                                output_cache[prefix] = [asn, valid_until, valid_since]
                else:
                    # No duplicate, add to cache
                    output_cache[prefix] = [asn, valid_until, valid_since]

    with open(rpki_res, "w") as asmap:
        for prefix, [asn, _, _] in output_cache.items():
            line_out = f"{prefix} AS{asn}"

            asmap.write(line_out + '\n')
            out_count += 1

    print(f'Result entries written: {out_count}')
    print(f'Duplicates found: {dups_count}')
    print(f'Invalids found: {invalids}')
    print(f'Incompletes: {incompletes}')
    print(f'Non-ROA files: {not_roas}')
