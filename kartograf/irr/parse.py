import codecs
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Dict

from kartograf.bogon import (
    is_bogon_pfx,
    is_bogon_asn,
    is_out_of_encoding_range,
)
from kartograf.timed import timed
from kartograf.util import parse_pfx, rir_from_str


@timed
def parse_irr(context):
    irr_res = Path(context.out_dir_irr) / "irr_final.txt"

    irr_files = [path for path in Path(context.out_dir_irr).rglob('*')
                 if os.path.isfile(path)
                 and (os.path.splitext(path)[1] != ".gz")]

    output_cache: Dict[str, str] = {}

    for file in irr_files:
        print(f"Parsing {file}")
        # We need to know the RIR of the file to check if it is equal to the
        # source later
        rir = rir_from_str(str(file))

        with codecs.open(file, 'r', encoding='ISO-8859-1') as f:
            lines = f.readlines()

        entry_list = []
        current_entry = {}

        # Parse the RPSL objects in the IRR DB into Python Dicts
        for line in lines:
            if line == '\n':
                entry_list.append(current_entry)
                current_entry = {}
            else:
                if ":" in line:
                    k, v = line.strip().split(':', 1)
                    current_entry[k.strip()] = v.strip()

        for entry in entry_list:
            is_complete = all(k in entry for k in ("origin", "source", "last-modified"))
            has_route = any(k in entry for k in ("route", "route6"))
            if is_complete and has_route:
                # Some RIRs mirror some other RIRs in their DBs, ignore the
                # mirrored entries
                if entry["source"] == rir:
                    # Sometimes there are comments in the origin field, remove
                    # these
                    origin = entry["origin"].split(" #", 1)[0].upper()
                    if "route" in entry:
                        route = entry["route"]
                    elif "route6" in entry:
                        route = entry["route6"]
                    else:
                        continue

                    route = parse_pfx(route)

                    last_modified = datetime.strptime(entry["last-modified"], '%Y-%m-%dT%H:%M:%SZ')
                    last_modified = last_modified.replace(tzinfo=timezone.utc)
                    last_modified = last_modified.timestamp()

                    # Bogon prefixes and ASNs are excluded since they can not
                    # be used for routing.
                    if not route or is_bogon_pfx(route) or is_bogon_asn(origin):
                        if context.debug_log:
                            with open(context.debug_log, 'a') as logs:
                                logs.write(f"IRR: parser encountered an invalid route: {route}")
                        continue

                    if context.max_encode and is_out_of_encoding_range(origin, context.max_encode):
                        continue

                    # There are dublicates and multiple entries for some
                    # prefixes in the IRR DBs, so we need to deal with them
                    # here.
                    if output_cache.get(route):
                        [old_origin, old_last_modified] = output_cache[route]

                        # If there are two entries for the same prefix, we
                        # prefer the one with the newer last-modified date.
                        if int(last_modified) > int(old_last_modified):
                            output_cache[route] = [origin, last_modified]

                        # If the last-modified date is the same, we use the
                        # lower ASN as a deterministic tie-breaker.
                        if int(last_modified) == int(old_last_modified):
                            if int(origin[2:]) < int(old_origin[2:]):
                                output_cache[route] = [origin, last_modified]

                    else:
                        output_cache[route] = [origin, last_modified]

    print("Found valid, unique entries:", len(output_cache))

    with open(irr_res, "a+") as irr:
        for route, [origin, _] in output_cache.items():
            line_out = f"{route} {origin}\n"
            irr.write(line_out)
