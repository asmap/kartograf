import codecs
import os
import pathlib

from kartograf.bogon import is_bogon_pfx, is_bogon_asn
from kartograf.timed import timed
from kartograf.util import rir_from_str


@timed
def parse_irr(context):
    irr_res = f"{context.out_dir_irr}irr_final.txt"

    irr_files = [path for path in pathlib.Path(context.data_dir_irr).rglob('*')
                 if os.path.isfile(path)
                 and (os.path.splitext(path)[1] != ".gz")]

    all_rir_list = []

    for file in irr_files:
        print(f"Parsing {file}")
        # We need to know the RIR of the file to check if it is equal to the
        # source later
        rir = rir_from_str(str(file))

        with codecs.open(file, 'r', encoding='ISO-8859-1') as f:
            lines = f.readlines()

        entry_list = []
        current_entry = dict()
        result = []

        # Parse the RPSL objects in the IRR DB into Python Dicts
        for line in lines:
            if line == '\n':
                entry_list.append(current_entry)
                current_entry = dict()
            else:
                if ":" in line:
                    k, v = line.strip().split(':', 1)
                    current_entry[k.strip()] = v.strip()

        for entry in entry_list:
            # if "route" and "origin" and "source" in entry:
            if all(k in entry for k in ("origin", "source")) and any(k in entry for k in ("route", "route6")):
                # Some RIRs mirror some other RIRs in their DBs, ignore the
                # mirrored entries
                if entry["source"] == rir:
                    # Sometimes there are comments in the origin field, remove
                    # these
                    origin = entry["origin"].split(" #", 1)[0]
                    if "route" in entry:
                        route = entry["route"]
                    elif "route6" in entry:
                        route = entry["route6"]
                    else:
                        continue

                    # Bogon prefixes and ASNs are excluded since they can not
                    # be used for routing.
                    if is_bogon_pfx(route) or is_bogon_asn(origin):
                        continue

                    result.append(f'{route} {origin}')

        print("Found valid entries:", len(result))

        all_rir_list += result

    # There are some dublicates. Unclear why but it's only a small number.
    uniq_rir_list = set(all_rir_list)

    with open(irr_res, "a+") as irr:
        for r in uniq_rir_list:
            irr.write(r + "\n")
