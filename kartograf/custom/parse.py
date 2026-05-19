from pathlib import Path

from kartograf.bogon import (
    is_bogon_pfx,
    is_bogon_asn,
    is_out_of_encoding_range,
)
from kartograf.timed import timed
from kartograf.util import parse_pfx


@timed
def parse_custom_source(context):
    raw_file = Path(context.data_dir_custom) / "custom_source.txt"
    clean_file = Path(context.out_dir_custom) / "custom_clean.txt"
    seen_prefixes = set()
    written_lines = 0

    with open(raw_file, 'r') as raw, open(clean_file, 'w') as clean:
        for line in raw:
            line = line.strip()
            if not line:
                continue

            parts = line.split()
            if len(parts) != 2:
                if context.debug_log:
                    with open(context.debug_log, 'a') as logs:
                        logs.write(f"Custom: parser encountered a malformed line: {line}\n")
                continue

            prefix, asn = parts
            prefix = parse_pfx(prefix)
            asn = asn.upper()
            if not asn.startswith("AS"):
                asn = f"AS{asn}"

            if context.max_encode and is_out_of_encoding_range(asn, context.max_encode):
                continue

            if not prefix or is_bogon_pfx(prefix) or is_bogon_asn(asn):
                if context.debug_log:
                    with open(context.debug_log, 'a') as logs:
                        logs.write(f"Custom: parser encountered an invalid entry: {line}\n")
                continue

            # If the user-provided dump contains multiple entries for the same
            # prefix, keep the first occurrence. This matches how the
            # routeviews parser picks the first origin on multi-origin routes.
            if prefix in seen_prefixes:
                if context.debug_log:
                    with open(context.debug_log, 'a') as logs:
                        logs.write(f"Custom: parser encountered duplicate prefix: {prefix}\n")
                continue
            seen_prefixes.add(prefix)

            clean.write(f"{prefix} {asn}\n")
            written_lines += 1

    print("Entries after cleanup:", written_lines)
