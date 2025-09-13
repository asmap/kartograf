from pathlib import Path

from kartograf.bogon import (
    is_bogon_pfx,
    is_bogon_asn,
    is_out_of_encoding_range,
)
from kartograf.timed import timed
from kartograf.util import parse_pfx


@timed
def parse_routeviews_pfx2as(context):
    raw_file = Path(context.out_dir_collectors) / "pfx2asn.txt"
    clean_file = Path(context.out_dir_collectors) / "pfx2asn_clean.txt"
    context.cleanup_out_files.append(raw_file)
    written_lines = 0

    print("Cleaning " + str(raw_file))
    with open(raw_file, 'r') as raw, open(clean_file, 'w') as clean:
        lines = raw.readlines()
        for line in lines:
            # CAIDA PFX2AS files can contain multi-origin routes as well as
            # AS-SETs as the origin of the prefix. If neither are the case, we
            # can just use the line as is.
            # https://publicdata.caida.org/datasets/routing/routeviews-prefix2as/README.txt
            if ',' not in line and '_' not in line:
                # Still need to check for bogons
                prefix, asn = line.split(" ")
                prefix = parse_pfx(prefix)
                asn = asn.upper().rstrip('\n')

                if context.max_encode and is_out_of_encoding_range(asn, context.max_encode):
                    continue

                if not prefix or is_bogon_pfx(prefix) or is_bogon_asn(asn):
                    if context.debug_log:
                        with open(context.debug_log, 'a') as logs:
                            logs.write(f"Routeviews: parser encountered an invalid IP network: {prefix}")
                    continue

                clean.write(f"{prefix} {asn}\n")
                written_lines += 1
                continue

            # If the line contains a multi-origin route (signified by the _)
            # then we use the first origin as CAIDA orders the origins
            # automatically in the order of occurrence and the first one should
            # be the one we prefer.
            line = line.split("_")[0]

            # TODO: Deal with AS-SETs in a better way, including multimap
            #
            # For now we also just choose the first AS out of an AS-SET
            line = line.split(",")[0]

            # Bogon prefixes and ASNs are excluded since they can not be used
            # for routing.
            prefix, asn = line.split(" ")
            prefix = parse_pfx(prefix)
            asn = asn.upper().rstrip('\n')

            if not prefix:
                continue
            if is_bogon_pfx(prefix) or is_bogon_asn(asn):
                if context.debug_log:
                    with open(context.debug_log, 'a') as logs:
                        logs.write(f"Routeviews: parser encountered an invalid IP network: {prefix}")
                continue

            if context.max_encode and is_out_of_encoding_range(asn, context.max_encode):
                continue

            clean.write(f"{prefix} {asn}\n")
            written_lines += 1

    print("Entries after cleanup:", written_lines)
