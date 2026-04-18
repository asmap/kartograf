import subprocess
import sys
import json
import os

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
import requests
from tqdm import tqdm

from kartograf.rpki.normalize import normalize_rpki_json
from kartograf.timed import timed
from kartograf.util import (
    KartografConfigurationError,
    calculate_sha256,
    calculate_sha256_directory,
    get_rpki_thread_count,
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

DEFAULT_RPKI_FETCH_TIMEOUT_SECONDS = 1800
DEFAULT_RPKI_LEGACY_BATCH_TIMEOUT_SECONDS = 900
DEFAULT_RPKI_THREADED_TIMEOUT_SECONDS = 1800

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


def _get_timeout_seconds(env_var, default_seconds):
    configured_value = os.getenv(env_var)
    if not configured_value:
        return default_seconds

    try:
        return max(1, int(configured_value))
    except ValueError:
        return default_seconds


def _iter_concatenated_json_objects(payload):
    decoder = json.JSONDecoder()
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise KartografConfigurationError(
            "rpki-client legacy validation produced non-UTF-8 JSON output."
        ) from exc
    index = 0
    text_length = len(text)

    while index < text_length:
        while index < text_length and text[index].isspace():
            index += 1
        if index >= text_length:
            break

        try:
            parsed, index = decoder.raw_decode(text, index)
        except json.JSONDecodeError as exc:
            raise KartografConfigurationError(
                "rpki-client legacy validation produced malformed concatenated JSON output."
            ) from exc
        yield parsed


def _iter_bounded_legacy_batch_results(executor, process_files_batch, batches, max_in_flight):
    batches_iter = iter(batches)
    in_flight = set()

    for _ in range(max_in_flight):
        try:
            in_flight.add(executor.submit(process_files_batch, next(batches_iter)))
        except StopIteration:
            break

    while in_flight:
        done, in_flight = wait(in_flight, return_when=FIRST_COMPLETED)

        for completed in done:
            yield completed.result()

            try:
                in_flight.add(executor.submit(process_files_batch, next(batches_iter)))
            except StopIteration:
                pass


def _run_legacy_validation_to_temp(context, tal_options, files, temp_path):
    batch_timeout = _get_timeout_seconds(
        "KARTOGRAF_RPKI_LEGACY_BATCH_TIMEOUT_SECONDS",
        DEFAULT_RPKI_LEGACY_BATCH_TIMEOUT_SECONDS,
    )

    def process_files_batch(batch):
        try:
            run_args = [
                "rpki-client",
                "-j",
                "-n",
                "-d",
                context.data_dir_rpki_cache,
                "-P",
                context.epoch,
            ] + tal_options + ["-f"] + batch

            if context.debug_log:
                with open(context.debug_log, "a", encoding="utf-8") as logs:
                    return subprocess.run(
                        run_args,
                        stdout=subprocess.PIPE,
                        stderr=logs,
                        check=False,
                        timeout=batch_timeout,
                    )

            return subprocess.run(
                run_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=batch_timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise KartografConfigurationError(
                "rpki-client legacy validation timed out after "
                f"{batch_timeout}s for a validation batch."
            ) from exc

    batch_size = 250
    batches = []
    for i in range(0, len(files), batch_size):
        batches.append([str(f) for f in files[i:i + batch_size]])

    with open(temp_path, "w", encoding="utf-8") as temp_out:
        temp_out.write("[")
        first_item = True

        if batches:
            workers = get_rpki_thread_count()
            with ThreadPoolExecutor(max_workers=workers) as executor:
                for result in tqdm(
                    _iter_bounded_legacy_batch_results(executor, process_files_batch, batches, workers),
                    total=len(batches),
                ):

                    if result.returncode != 0:
                        raise KartografConfigurationError(
                            f"rpki-client legacy validation failed with exit code {result.returncode}."
                        )

                    if not result.stdout:
                        continue

                    for parsed in _iter_concatenated_json_objects(result.stdout):
                        if not first_item:
                            temp_out.write(",")
                        temp_out.write(json.dumps(parsed, separators=(",", ":")))
                        first_item = False

        temp_out.write("]")


def _run_threaded_validation_to_temp(context, tal_options, temp_path):
    threads = get_rpki_thread_count()
    print(f"Using threaded rpki-client validation with {threads} worker(s).")
    run_timeout = _get_timeout_seconds(
        "KARTOGRAF_RPKI_THREADED_TIMEOUT_SECONDS",
        DEFAULT_RPKI_THREADED_TIMEOUT_SECONDS,
    )

    run_args = [
        "rpki-client",
        "-j",
        "-n",
        "-d",
        context.data_dir_rpki_cache,
        "-P",
        context.epoch,
    ] + tal_options + ["-p", str(threads)]

    try:
        with open(temp_path, "w", encoding="utf-8") as temp_out:
            if context.debug_log:
                with open(context.debug_log, "a", encoding="utf-8") as logs:
                    result = subprocess.run(
                        run_args,
                        stdout=temp_out,
                        stderr=logs,
                        check=False,
                        text=True,
                        timeout=run_timeout,
                    )
            else:
                result = subprocess.run(
                    run_args,
                    stdout=temp_out,
                    stderr=subprocess.DEVNULL,
                    check=False,
                    text=True,
                    timeout=run_timeout,
                )
    except subprocess.TimeoutExpired as exc:
        raise KartografConfigurationError(
            "rpki-client threaded validation timed out after "
            f"{run_timeout}s."
        ) from exc

    if result.returncode != 0:
        raise KartografConfigurationError(
            f"rpki-client threaded validation failed with exit code {result.returncode}."
        )


@timed
def fetch_rpki_db(context):
    # Download TALs and presist them in the RPKI data folder
    download_rir_tals(context)
    tal_options = [item for path in data_tals(context) for item in ('-t', path)]
    run_args = ["rpki-client", "-d", context.data_dir_rpki_cache] + tal_options
    print("Downloading RPKI Data, this may take a while.")
    fetch_timeout = _get_timeout_seconds(
        "KARTOGRAF_RPKI_FETCH_TIMEOUT_SECONDS",
        DEFAULT_RPKI_FETCH_TIMEOUT_SECONDS,
    )

    if context.stable_repos:
        for url in STABLE_REPO_URLS:
            run_args += ["-H", url]
        print("Using only stable RPKI repositories.")

    try:
        if context.debug_log:
            with open(context.debug_log, 'a') as logs:
                logs.write("=== RPKI Download ===\n")
                logs.flush()  # Without this the line above is not appearing first in the logs
                result = subprocess.run(run_args,
                                        stdout=logs,
                                        stderr=logs,
                                        check=False,
                                        timeout=fetch_timeout)
        else:
            result = subprocess.run(run_args,
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL,
                                    check=False,
                                    timeout=fetch_timeout)
    except subprocess.TimeoutExpired as exc:
        raise KartografConfigurationError(
            f"rpki-client data fetch timed out after {fetch_timeout}s."
        ) from exc

    if result.returncode != 0:
        raise KartografConfigurationError(
            f"rpki-client data fetch failed with exit code {result.returncode}."
        )

    print(f"Downloaded RPKI Data, hash sum: {calculate_sha256_directory(context.data_dir_rpki_cache)}")


@timed
def validate_rpki_db(context):
    backend = getattr(context, "rpki_backend", "legacy")
    if backend not in {"legacy", "threaded"}:
        raise KartografConfigurationError(
            f"Unsupported RPKI backend '{backend}'. Use 'legacy' or 'threaded'."
        )

    files = []
    if backend == "legacy":
        files = [path for path in Path(context.data_dir_rpki_cache).rglob('*')
                 if path.is_file() and ((path.suffix == ".roa")
                                        or (path.name == ".roa"))]

        print(f"{len(files)} raw RPKI ROA files found.")
    rpki_raw_file = 'rpki_raw.json'
    result_path = Path(context.out_dir_rpki) / rpki_raw_file
    temp_path = Path(context.out_dir_rpki) / "rpki_temp.json"

    tal_options = [item for path in data_tals(context) for item in ('-t', path)]

    if context.debug_log:
        with open(context.debug_log, 'a') as logs:
            logs.write("\n\n=== RPKI Validation ===\n")

    if backend == "legacy":
        _run_legacy_validation_to_temp(context, tal_options, files, temp_path)
    else:
        _run_threaded_validation_to_temp(context, tal_options, temp_path)

    records_count = normalize_rpki_json(temp_path, result_path)
    context.cleanup_out_files.append(temp_path)

    print(
        f"{records_count} RPKI ROA records normalized\n"
        f"Saved to: {result_path.name}\n"
        f"File hash: {calculate_sha256(result_path)}"
    )
