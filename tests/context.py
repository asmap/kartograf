import csv
import json
import os
from pathlib import Path

from types import SimpleNamespace
from kartograf.context import Context

TEST_ARGS = SimpleNamespace(**{
    "wait": None,
    "reproduce": None,
    "irr": False,
    "routeviews": False,
    "max_encode": 33521664,
    "debug": False,
    "cleanup": False,
    "epoch": None
})


def load_rpki_csv_to_json(self, csv_path):
    '''
    Loads a fixtures CSV file into a rpki_raw.json file in the "tests/out/" directory.
    '''
    rpki_data = []
    with open(csv_path, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            vrps = [{"prefix": row["prefix"], "asid": row["asid"], "maxlen": row["maxlen"]}]
            del row["prefix"]
            del row["asid"]
            del row["maxlen"]
            row["vrps"] = vrps
            rpki_data.append(row)

    output_path = Path(self.out_dir_rpki) / 'rpki_raw.json'
    with open(output_path, 'w') as jsonfile:
        json.dump(rpki_data, jsonfile, indent=2)


def create_test_context(tmp_path, epoch):
    current_path = Path.cwd()
    fixtures_path = Path(__file__).parent / "data"
    os.chdir(tmp_path)  # Use temporary directory

    TEST_ARGS.epoch = epoch
    context = Context(TEST_ARGS)
    context.data_dir = Path(tmp_path) / "data" / context.epoch_dir
    context.data_dir_rpki = Path(context.data_dir) / "rpki"
    context.out_dir = Path(tmp_path) / "out" / context.epoch_dir
    context.out_dir_rpki = Path(context.out_dir) / "rpki"

    Path.mkdir(context.data_dir_rpki, exist_ok=True, parents=True)
    Path.mkdir(context.out_dir_rpki, exist_ok=True, parents=True)

    load_rpki_csv_to_json(context, fixtures_path / "rpki_raw.csv")
    os.chdir(current_path)
    return context
