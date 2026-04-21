from concurrent.futures import ThreadPoolExecutor, as_completed
import gzip
import shutil
from pathlib import Path

from kartograf.timed import timed
from kartograf.util import calculate_sha256, download_with_retries

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

    print(f"Starting download: {file_name}")
    try:
        download_with_retries(url, timeout=(15, 120), max_retries=5,
                              retry_delay=2, stream=True,
                              dest_path=local_file_path)
        file_hash = calculate_sha256(local_file_path)
        print(f"Downloaded {file_name}, file hash: {file_hash}")
        return {'status': 'success'}
    except Exception as e:
        print(f"✗ Error: Failed to download {file_name}: {e}")
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
