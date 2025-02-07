import csv
import json
import os
import shutil
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

def irr_fixtures():
    return [ "irr_ripe.txt" ]


def load_rpki_csv_to_json(context, fixtures_path):
    '''
    Loads a fixtures CSV file into a rpki_raw.json file in the "tests/out/" directory.
    '''
    csv_path = fixtures_path / "rpki_raw.csv"
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

    output_path = Path(context.out_dir_rpki) / 'rpki_raw.json'
    with open(output_path, 'w') as jsonfile:
        json.dump(rpki_data, jsonfile, indent=2)

def load_irr_fixtures(context, fixtures_path):
    for file in irr_fixtures():
        shutil.copy2(Path(fixtures_path) / file, context.out_dir_irr)

def create_test_context(tmp_path, epoch):
    current_path = Path.cwd()
    fixtures_path = Path(__file__).parent / "data"
    os.chdir(tmp_path)  # Use temporary directory

    TEST_ARGS.epoch = epoch
    context = Context(TEST_ARGS)
    context.data_dir = Path(tmp_path) / "data" / context.epoch_dir
    context.data_dir_rpki = Path(context.data_dir) / "rpki"
    context.data_dir_irr = Path(context.data_dir) / "irr"
    context.out_dir = Path(tmp_path) / "out" / context.epoch_dir
    context.out_dir_rpki = Path(context.out_dir) / "rpki"
    context.out_dir_irr = Path(context.out_dir) / "irr"

    for p in [context.data_dir_rpki, context.data_dir_irr, context.out_dir_rpki, context.out_dir_irr]:
        Path.mkdir(p, exist_ok=True, parents=True)

    load_rpki_csv_to_json(context, fixtures_path)
    load_irr_fixtures(context, fixtures_path)
    os.chdir(current_path)
    return context
