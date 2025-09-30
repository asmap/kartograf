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


@timed
def fetch_irr(context):
    max_retries = 5
    retry_delay = 2  # Seconds

    for url in IRR_FILE_ADDRESSES:
        file_name = url.rsplit('/', maxsplit=1)[-1]
        local_file_path = Path(context.data_dir_irr) / file_name
        attempt = 0

        print("Downloading " + file_name)
        while attempt < max_retries:
            try:
                response = requests.get(url, stream=True, timeout=(15, 120))
                response.raise_for_status()  # Raise exception for HTTP errors
                with open(local_file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"file hash: {calculate_sha256(local_file_path)}")
                break
            except (requests.RequestException, ConnectionError) as e:
                print(f"Connection issue while downloading {file_name}: {e}. Retrying... (Attempt {attempt + 1}/{max_retries})")
                attempt += 1
                time.sleep(retry_delay)

        if attempt == max_retries:
            raise Exception(f"Fatal: Failed to download {file_name} after {max_retries} attempts.")


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
