import subprocess

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from threading import Lock
from pathlib import Path
from tqdm import tqdm

from kartograf.timed import timed
from kartograf.util import (
    calculate_sha256,
    calculate_sha256_directory,
)


@timed
def fetch_rpki_db(context):
    print("Downloading RPKI Data, this may take a while.")
    if context.debug_log:
        with open(context.debug_log, 'a') as logs:
            logs.write("=== RPKI Download ===\n")
            logs.flush()  # Without this the line above is not appearing first in the logs
            subprocess.run(["rpki-client",
                            "-d", context.data_dir_rpki_cache
                            ],
                           stdout=logs,
                           stderr=logs,
                           check=False)
    else:
        subprocess.run(["rpki-client",
                        "-d", context.data_dir_rpki_cache
                        ],
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

    debug_file_lock = Lock()

    if context.debug_log:
        with open(context.debug_log, 'a') as logs:
            logs.write("\n\n=== RPKI Validation ===\n")

    def process_files_batch(batch):
        result = subprocess.run(["rpki-client",
                                 "-j",
                                 "-n",
                                 "-d",
                                 context.data_dir_rpki_cache,
                                 "-P",
                                 context.epoch,
                                 ] +
                                 ["-f"] + batch,  # -f has to be last
                                 capture_output=True,
                                 check=False)

        if result.stderr and context.debug_log:
            stderr_output = result.stderr.decode()
            with debug_file_lock:
                with open(context.debug_log, 'a') as logs:
                    logs.write(stderr_output)
        return result.stdout

    total = len(files)
    batch_size = 250
    batches = []
    for i in range(0, total, batch_size):
        batch = [str(f) for f in files[i:i + batch_size]]
        batches.append(batch)

    total_batches = len(batches)
    results = []
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_files_batch, batch) for batch in batches]
        for future in tqdm(as_completed(futures), total=total_batches):
            result = future.result()
            if result:
                normalized = result.replace(b"\n}\n{\n\t", b"\n},\n{\n").decode('utf-8').strip()
                results.append(normalized)
        results_json = json.loads("[" + ",".join(results) + "]")
        s = sorted(results_json, key=lambda result: result["hash_id"])

        with open(result_path, 'w') as f:
            json.dump(s, f)

    print(f"{len(results_json)} RKPI ROAs validated and saved to {result_path}, file hash: {calculate_sha256(result_path)}")
