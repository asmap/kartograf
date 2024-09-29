from concurrent.futures import ThreadPoolExecutor
import asyncio
import os
import pathlib
import requests
import subprocess
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


def download_rir_tals(context, silent=False):
    tals = []

    for rir, url in TAL_URLS.items():
        try:
            response = requests.get(url)
            response.raise_for_status()

            tal_path = os.path.join(context.data_dir_rpki_tals, f"{rir}.tal")
            with open(tal_path, 'wb') as file:
                file.write(response.content)

            if not silent:
                print(f"Downloaded TAL for {rir.upper()} to {tal_path}, file hash: {calculate_sha256(tal_path)}")
            tals.append(tal_path)

        except requests.RequestException as e:
            print(f"Error downloading TAL for {rir.upper()}: {e}")
            exit(1)


def data_tals(context):
    tal_paths = [path for path in pathlib.Path(context.data_dir_rpki_tals).rglob('*.tal')]
    # We need to have 5 TALs, one from each RIR
    if len(tal_paths) == 5:
        return tal_paths
    else:
        print("Not all 5 TALs could be downloaded.")
        exit(1)


async def warmup_rpki_cache(context):
    download_rir_tals(context, silent=True)
    tal_options = [item for path in data_tals(context) for item in ('-t', path)]
    return await asyncio.create_subprocess_exec(
        "rpki-client",
        "-d", context.data_dir_rpki_cache,
        *tal_options,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL
    )


@timed
def fetch_rpki_db(context):
    # Download TALs and presist them in the RPKI data folder
    download_rir_tals(context)
    tal_options = [item for path in data_tals(context) for item in ('-t', path)]
    print("Downloading RPKI Data, this may take a while.")
    subprocess.run(["rpki-client",
                    "-d", context.data_dir_rpki_cache
                    ] + tal_options,
                   capture_output=True)

    print(f"Downloaded RPKI Data, hash sum: {calculate_sha256_directory(context.data_dir_rpki_cache)}")


@timed
def validate_rpki_db(context):
    print("Validating RPKI ROAs")
    files = [path for path in pathlib.Path(context.data_dir_rpki_cache).rglob('*')
             if path.is_file() and ((path.suffix == ".roa")
                                    or (path.name == ".roa"))]

    print(f"{len(files)} raw RKPI ROA files found.")
    rpki_raw_file = 'rpki_raw.json'
    result_path = f"{context.out_dir_rpki}{rpki_raw_file}"

    tal_options = [item for path in data_tals(context) for item in ('-t', path)]

    def process_file(file):
        return subprocess.run(["rpki-client",
                               "-j",
                               "-n",
                               "-d",
                               context.data_dir_rpki_cache,
                               "-P",
                               context.epoch,
                               ] + tal_options +
                              ["-f", file],  # -f has to be last
                              capture_output=True).stdout

    with ThreadPoolExecutor() as executor:
        results = list(tqdm(executor.map(process_file, files), total=len(files)))

    json_results = [result.decode() for result in results if result]

    with open(result_path, "w") as res_file:
        res_file.write("[")
        res_file.write(",".join(json_results))
        res_file.write("]")

    print(f"{len(json_results)} RKPI ROAs validated and saved to {result_path}, file hash: {calculate_sha256(result_path)}")
