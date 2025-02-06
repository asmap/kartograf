import subprocess
import sys

from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from pathlib import Path
import requests
from tqdm import tqdm

from kartograf.timed import timed
from kartograf.util import (
    calculate_sha256,
    calculate_sha256_directory,
)

TAL_URLS = {
    "afrinic": "http://rpki.afrinic.net/tal/afrinic.tal",
    "apnic": "https://tal.apnic.net/tal-archive/apnic-rfc7730-https.tal",
    "arin": "https://www.arin.net/resources/manage/rpki/arin.tal",
    "lacnic": "https://www.lacnic.net/rpki/lacnic.tal",
    "ripe": "https://tal.rpki.ripe.net/ripe-ncc.tal"
}


def download_rir_tals(context):
    tals = []

    for rir, url in TAL_URLS.items():
        try:
            response = requests.get(url, timeout=600)
            response.raise_for_status()

            tal_path = Path(context.data_dir_rpki_tals) / f"{rir}.tal"
            with open(tal_path, 'wb') as file:
                file.write(response.content)

            print(f"Downloaded TAL for {rir.upper()} to {tal_path}, file hash: {calculate_sha256(tal_path)}")
            tals.append(tal_path)

        except requests.RequestException as e:
            print(f"Error downloading TAL for {rir.upper()}: {e}")
            sys.exit(1)


def data_tals(context):
    tal_paths = list(Path(context.data_dir_rpki_tals).rglob('*.tal'))
    # We need to have 5 TALs, one from each RIR
    if len(tal_paths) == 5:
        return tal_paths

    print("Not all 5 TALs could be downloaded.")
    sys.exit(1)


@timed
def fetch_rpki_db(context):
    # Download TALs and presist them in the RPKI data folder
    download_rir_tals(context)
    tal_options = [item for path in data_tals(context) for item in ('-t', path)]
    print("Downloading RPKI Data, this may take a while.")
    if context.debug_log:
        with open(context.debug_log, 'a') as logs:
            logs.write("=== RPKI Download ===\n")
            logs.flush()  # Without this the line above is not appearing first in the logs
            subprocess.run(["rpki-client",
                            "-d", context.data_dir_rpki_cache
                            ] + tal_options,
                           stdout=logs,
                           stderr=logs,
                           check=False)
    else:
        subprocess.run(["rpki-client",
                        "-d", context.data_dir_rpki_cache
                        ] + tal_options,
                       capture_output=True,
                       check=False)

    print(f"Downloaded RPKI Data, hash sum: {calculate_sha256_directory(context.data_dir_rpki_cache)}")


@timed
def validate_rpki_db(context):
    print("Validating RPKI ROAs")
    files = [path for path in Path(context.data_dir_rpki_cache).rglob('*')
             if path.is_file() and ((path.suffix == ".roa")
                                    or (path.name == ".roa"))]

    print(f"{len(files)} raw RKPI ROA files found.")
    rpki_raw_file = 'rpki_raw.json'
    result_path = Path(context.out_dir_rpki) / rpki_raw_file

    tal_options = [item for path in data_tals(context) for item in ('-t', path)]

    debug_file_lock = Lock()

    if context.debug_log:
        with open(context.debug_log, 'a') as logs:
            logs.write("\n\n=== RPKI Validation ===\n")

    def process_file(file):
        result = subprocess.run(["rpki-client",
                                 "-j",
                                 "-n",
                                 "-d",
                                 context.data_dir_rpki_cache,
                                 "-P",
                                 context.epoch,
                                 ] + tal_options +
                                 ["-f", file],  # -f has to be last
                                 capture_output=True,
                                 check=False)

        if result.stderr and context.debug_log:
            stderr_output = result.stderr.decode()
            with debug_file_lock:
                with open(context.debug_log, 'a') as logs:
                    logs.write(f'\nfile: {file}\n')
                    logs.write(stderr_output)
        return result.stdout

    with ThreadPoolExecutor() as executor:
        results = list(tqdm(executor.map(process_file, files), total=len(files)))

    json_results = [result.decode() for result in results if result]

    with open(result_path, "w") as res_file:
        res_file.write("[")
        res_file.write(",".join(json_results))
        res_file.write("]")

    print(f"{len(json_results)} RKPI ROAs validated and saved to {result_path}, file hash: {calculate_sha256(result_path)}")
