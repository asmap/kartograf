import subprocess
import sys

from threading import Lock
from pathlib import Path
import requests

from kartograf.timed import timed
from kartograf.util import (
    calculate_sha256,
    calculate_sha256_directory,
    get_threads,
)

TAL_URLS = {
    "afrinic": "http://rpki.afrinic.net/tal/afrinic.tal",
    "apnic": "https://tal.apnic.net/tal-archive/apnic-rfc7730-https.tal",
    "arin": "https://www.arin.net/resources/manage/rpki/arin.tal",
    "lacnic": "https://www.lacnic.net/rpki/lacnic.tal",
    "ripe": "https://tal.rpki.ripe.net/ripe-ncc.tal"
}

STABLE_REPO_URLS = [
    "rpki.arin.net",
    "rpki-rps.arin.net",
    "rpki.ripe.net",
    "rsync.paas.rpki.ripe.net",
    "rpki.apnic.net",
    "repository.lacnic.net",
    "rpki.afrinic.net",
    "rpki-repo.registro.br",
    "rpki-rsync.us-east-2.amazonaws.com",
    "rpki-repository.nic.ad.jp",
    "rpkica.twnic.tw",
    "rpki.cnnic.cn",
    "repo-rpki.idnic.net"
]

def download_rir_tals(context):
    tals = []

    for rir, url in TAL_URLS.items():
        try:
            response = requests.get(url, timeout=600)
            response.raise_for_status()

            tal_path = Path(context.data_dir_rpki_tals) / f"{rir}.tal"
            with open(tal_path, 'wb') as file:
                file.write(response.content)

            print(f"Downloaded TAL for {rir.upper()} to {tal_path.name}, file hash: {calculate_sha256(tal_path)}")
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
    run_args = ["rpki-client", "-d", context.data_dir_rpki_cache] + tal_options
    print("Downloading RPKI Data, this may take a while.")

    if context.stable_repos:
        for url in STABLE_REPO_URLS:
            run_args += ["-H", url]
        print("Using only stable RPKI repositories.")

    if context.debug_log:
        with open(context.debug_log, 'a') as logs:
            logs.write("=== RPKI Download ===\n")
            logs.flush()  # Without this the line above is not appearing first in the logs
            subprocess.run(run_args,
                           stdout=logs,
                           stderr=logs,
                           check=False)
    else:
        subprocess.run(run_args,
                       capture_output=True,
                       check=False)

    print(f"Downloaded RPKI Data, hash sum: {calculate_sha256_directory(context.data_dir_rpki_cache)}")


@timed
def validate_rpki_db(context):
    print("Validating RPKI ROAs")
    rpki_raw_file = 'rpki_raw.json'
    result_path = Path(context.out_dir_rpki) / rpki_raw_file

    tal_options = [item for path in data_tals(context) for item in ('-t', path)]
    threads = get_threads()

    debug_file_lock = Lock()

    if context.debug_log:
        with open(context.debug_log, 'a') as logs:
            logs.write("\n\n=== RPKI Validation ===\n")

    def process_rpki_cache():
        result = subprocess.run(["rpki-client",
                                 "-j",
                                 "-n",
                                 "-d",
                                 context.data_dir_rpki_cache,
                                 f"-p {threads}",
                                 "-P",
                                 context.epoch,
                                 ] + tal_options + [context.out_dir_rpki],
                                 capture_output=True,
                                 check=False)

        if context.debug_log:
            with debug_file_lock:
                with open(context.debug_log, 'a') as logs:
                    if result.stderr:
                        std_err = result.stderr.decode()
                        logs.write(std_err)
                    if result.stdout:
                        logs.write("\n== RPKI Validation Summary ==\n")
                        std_output = result.stdout.decode()
                        for line in std_output:
                            logs.write(line)
        return result.stdout

    process_rpki_cache()
    default_out_dir = Path(context.out_dir_rpki) / "json"
    default_out_dir.rename(result_path)

    print(f"RKPI ROAs validated and saved to {result_path}, file hash: {calculate_sha256(result_path)}")
