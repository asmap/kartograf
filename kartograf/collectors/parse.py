from kartograf.bogon import (
    is_bogon_pfx,
    is_bogon_asn,
    is_out_of_encoding_range,
)
from kartograf.timed import timed
from kartograf.util import format_pfx


@timed
def parse_routeviews_pfx2as(context):
    raw_file = f'{context.out_dir_collectors}pfx2asn.txt'
    clean_file = f'{context.out_dir_collectors}pfx2asn_clean.txt'

    print("Cleaning " + raw_file)
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
                prefix = format_pfx(prefix)
                asn = asn.upper().rstrip('\n')

                if context.max_encode and is_out_of_encoding_range(asn, context.max_encode):
                    continue

                if not prefix or is_bogon_pfx(prefix) or is_bogon_asn(asn):
                    continue

                clean.write(f"{prefix} {asn}\n")
                continue

            # If the line contains a mulit-origin route (signified by the _)
            # then we use the first origin as CAIDA orders the origins
            # automatically in the order of corrence and the first one should
            # be the one we prefer.
            line = line.split("_")[0]

            # TODO: Deal with AS-SETs in a better way, including multimap
            #
            # For now we also just choose the first AS out of an AS-SET
            line = line.split(",")[0]

            # Bogon prefixes and ASNs are excluded since they can not be used
            # for routing.
            prefix, asn = line.split(" ")
            prefix = format_pfx(prefix)
            asn = asn.upper().rstrip('\n')

            if not prefix or is_bogon_pfx(prefix) or is_bogon_asn(asn):
                continue

            if context.max_encode and is_out_of_encoding_range(asn, context.max_encode):
                continue

            clean.write(f"{prefix} {asn}\n")
