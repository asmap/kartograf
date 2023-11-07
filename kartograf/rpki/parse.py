import json
from typing import Set, Dict

from kartograf.bogon import is_bogon_pfx, is_bogon_asn
from kartograf.timed import timed


@timed
def parse_rpki(context):
    raw_input = f"{context.out_dir_rpki}rpki_raw.json"
    rpki_res = f"{context.out_dir_rpki}rpki_final.txt"

    aki_cache: Set[str] = set()
    output_cache: Dict[str, str] = {}

    dups_count = 0
    out_count = 0
    invalids = 0
    incompletes = 0

    with open(rpki_res, "w") as asmap:
        with open(raw_input, "r") as dump:
            data = json.loads(dump.read())
            print(f'Parsing {len(data)} ROAs')

            for roa in data:
                # Sometimes ROAs are incomplete and we have to skip them
                key_list = ['type', 'validation', 'aki', 'ski', 'vrps']
                if not all(key in roa for key in key_list):
                    incompletes += 1
                    continue

                # We are only interested in valid ROAs
                if roa['type'] != "roa" or roa['validation'] != "OK":
                    invalids += 1
                    continue

                # We are only interested in the edges, kick out RIRs here so
                # we are only left with LIRs
                if roa['aki'] in aki_cache:
                    continue

                aki_cache.add(roa['ski'])

                for vrp in roa['vrps']:
                    if output_cache.get(vrp['prefix']):
                        dups_count += 1
                        continue
                    else:
                        output_cache[vrp['prefix']] = vrp['asid']

                    prefix = vrp['prefix']
                    asn = vrp['asid']
                    # Bogon prefixes and ASNs are excluded since they can not
                    # be used for routing.
                    if is_bogon_pfx(prefix) or is_bogon_asn(asn):
                        continue
                    line_out = f"{prefix} AS{asn}"

                    asmap.write(line_out + '\n')
                    out_count += 1

    print(f'Output: {out_count}')
    print(f'Duplicates: {dups_count}')
    print(f'Invalids: {invalids}')
    print(f'Incompletes: {incompletes}')
