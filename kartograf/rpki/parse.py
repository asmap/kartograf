import json
from typing import Dict

from kartograf.bogon import is_bogon_pfx, is_bogon_asn
from kartograf.timed import timed


@timed
def parse_rpki(context):
    raw_input = f"{context.out_dir_rpki}rpki_raw.json"
    rpki_res = f"{context.out_dir_rpki}rpki_final.txt"

    output_cache: Dict[str, [str, str]] = {}

    dups_count = 0
    out_count = 0
    invalids = 0
    incompletes = 0

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

            # We are only interested in valid ROAs
            if roa['type'] != "roa" or roa['validation'] != "OK":
                invalids += 1
                continue

            valid_until = roa['valid_until']

            for vrp in roa['vrps']:
                prefix = vrp['prefix']
                asn = vrp['asid']

                # Bogon prefixes and ASNs are excluded since they can not
                # be used for routing.
                if is_bogon_pfx(prefix) or is_bogon_asn(asn):
                    continue

                # Duplicates are possible and need to be filtered out
                if output_cache.get(prefix):
                    dups_count += 1
                    # If the new ASN is from a ROA that is valid for longer,
                    # we override the old entry with it
                    [old_asn, old_valid_until] = output_cache[prefix]
                    if int(valid_until) > int(old_valid_until):
                        output_cache[prefix] = [asn, valid_until]
                else:
                    # No duplicate, add to cache
                    output_cache[prefix] = [asn, valid_until]

    with open(rpki_res, "w") as asmap:
        for prefix, [asn, _] in output_cache.items():
            line_out = f"{prefix} AS{asn}"

            asmap.write(line_out + '\n')
            out_count += 1

    print(f'Output: {out_count}')
    print(f'Duplicates: {dups_count}')
    print(f'Invalids: {invalids}')
    print(f'Incompletes: {incompletes}')
