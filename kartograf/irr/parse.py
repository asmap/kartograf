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

    context.cleanup_out_files += irr_files
    output_cache: Dict[str, str] = {}

    for file in irr_files:
        # We need to know the RIR of the file to check if it is equal to the
        # source later
        rir = rir_from_str(str(file))

        with codecs.open(file, 'r', encoding='ISO-8859-1') as f:
            lines = f.readlines()

        entry_list = []
        current_entry = {}
        prev_count = len(output_cache)

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
            is_complete = all(k in entry for k in ("origin", "source"))
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

                    parsed_route = parse_pfx(route)
                    if not parsed_route:
                        if context.debug_log:
                            with open(context.debug_log, 'a') as logs:
                                logs.write(f"Could not parse prefix from line: {route}")
                        continue

                    # AFRINIC and LACNIC appear to not use last modified anymore
                    last_modified = entry.get("last-modified", "2009-01-03T19:15:05Z")
                    last_modified = datetime.strptime(last_modified, '%Y-%m-%dT%H:%M:%SZ')
                    last_modified = last_modified.replace(tzinfo=timezone.utc)
                    last_modified = last_modified.timestamp()

                    # Bogon prefixes and ASNs are excluded since they can not
                    # be used for routing.
                    if is_bogon_pfx(parsed_route) or is_bogon_asn(origin):
                        if context.debug_log:
                            with open(context.debug_log, 'a') as logs:
                                logs.write(f"IRR: parser encountered an invalid route: {parsed_route}\n")
                        continue

                    if context.max_encode and is_out_of_encoding_range(origin, context.max_encode):
                        continue

                    # There are duplicates and multiple entries for some
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

        print(f"Parsed {file.name}, found: {len(output_cache) - prev_count}")

    print("Found valid, unique entries:", len(output_cache))

    with open(irr_res, "a+") as irr:
        for route, [origin, _] in output_cache.items():
            line_out = f"{route} {origin}\n"
            irr.write(line_out)
