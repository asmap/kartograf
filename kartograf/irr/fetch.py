from concurrent.futures import ThreadPoolExecutor, as_completed
import gzip
import shutil
import time
from pathlib import Path
import requests

from kartograf.timed import timed
from kartograf.util import calculate_sha256

IRR_FILE_ADDRESSES = [
    # AFRINIC
    "https://ftp.afrinic.net/pub/dbase/afrinic.db.gz",
    # APNIC
    "https://ftp.apnic.net/pub/apnic/whois/apnic.db.route.gz",
    "https://ftp.apnic.net/pub/apnic/whois/apnic.db.route6.gz",
    # ARIN
    "https://ftp.arin.net/pub/rr/arin.db.gz",
    # LACNIC
    "https://ftp.lacnic.net/lacnic/irr/lacnic.db.gz",
    # RIPE
    "https://ftp.ripe.net/ripe/dbase/split/ripe.db.route.gz",
    "https://ftp.ripe.net/ripe/dbase/split/ripe.db.route6.gz",
]

def download_single_irr_file(url, context):
    """Download a single IRR file with retry logic"""
    file_name = url.rsplit('/', maxsplit=1)[-1]
    local_file_path = Path(context.data_dir_irr) / file_name
    attempt = 0
    max_retries = 5
    retry_delay = 2

    print(f"Starting download: {file_name}")
    while attempt < max_retries:
        try:
            response = requests.get(url, stream=True, timeout=(15, 120))
            response.raise_for_status()
            with open(local_file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            file_hash = calculate_sha256(local_file_path)
            print(f"Downloaded {file_name}, file hash: {file_hash}")
            return {'status': 'success'}
        except (requests.RequestException, ConnectionError) as e:
            print(f"Connection issue while downloading {file_name}: {e}. Retrying... (Attempt {attempt + 1}/{max_retries})")
            attempt += 1
            if attempt < max_retries:
                time.sleep(retry_delay)

    error_msg = f"Error: Failed to download {file_name} after {max_retries} attempts."
    print(f"✗ {error_msg}")
    return {'status': 'failed'}


@timed
def fetch_irr(context, max_concurrent=8):
    """Fetch IRR databases concurrently"""
    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        future_to_url = {
            executor.submit(download_single_irr_file, url, context): url
            for url in IRR_FILE_ADDRESSES
        }

        for future in as_completed(future_to_url):
            result = future.result()
            if result['status'] == 'failed':
                raise Exception("Failed to download all required IRR database(s).")

    print("All IRR databases downloaded successfully.")


def extract_irr(context):
    print("Extracting IRR DBs")
    for file in IRR_FILE_ADDRESSES:
        _, file_path = file.split("/", 1)
        _, file_name = file_path.rsplit("/", 1)
        local_file_path = Path(context.data_dir_irr) / file_name
        extracted_file_path = Path(context.out_dir_irr) / file_name.rstrip(".gz")

        with gzip.open(local_file_path, 'rb') as r:
            with open(extracted_file_path, 'wb') as w:
                shutil.copyfileobj(r, w)
