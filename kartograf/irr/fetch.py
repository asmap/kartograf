from ftplib import FTP
import gzip
import shutil
import time
from pathlib import Path

from kartograf.timed import timed
from kartograf.util import calculate_sha256

IRR_FILE_ADDRESSES = [
    # AFRINIC
    "ftp.afrinic.net/pub/dbase/afrinic.db.gz",
    # APNIC
    "ftp.apnic.net/pub/apnic/whois/apnic.db.route.gz",
    "ftp.apnic.net/pub/apnic/whois/apnic.db.route6.gz",
    # ARIN
    "ftp.arin.net/pub/rr/arin.db.gz",
    # LACNIC
    "ftp.lacnic.net/lacnic/irr/lacnic.db.gz",
    # RIPE
    "ftp.ripe.net/ripe/dbase/split/ripe.db.route.gz",
    "ftp.ripe.net/ripe/dbase/split/ripe.db.route6.gz",
]


@timed
def fetch_irr(context):
    max_retries = 5
    retry_delay = 2  # Seconds

    for ftp_file in IRR_FILE_ADDRESSES:
        host, ftp_file_path = ftp_file.split("/", 1)
        path, file_name = ftp_file_path.rsplit("/", 1)

        local_file_path = Path(context.data_dir_irr) / file_name
        attempt = 0

        print("Downloading " + file_name)
        while attempt < max_retries:
            try:
                with FTP(host) as ftp:
                    ftp.login()
                    ftp.cwd(path)

                    with open(local_file_path, 'wb') as f:
                        ftp.retrbinary("RETR " + file_name, f.write)

                    print(f"Downloaded {file_name}, file hash: {calculate_sha256(local_file_path)}")
                    break

            except ConnectionRefusedError:
                print(f"Connection refused by host {host}. Retrying... (Attempt {attempt + 1}/{max_retries})")
                attempt += 1
                time.sleep(retry_delay)

            except EOFError:
                print(f"Connection lost while downloading {file_name}. Retrying... (Attempt {attempt + 1}/{max_retries})")
                attempt += 1
                time.sleep(retry_delay)

        if attempt == max_retries:
            raise Exception(f"Fatal: Failed to download {file_name} after {max_retries} attempts.")


def extract_irr(context):
    for ftp_file in IRR_FILE_ADDRESSES:
        _, ftp_file_path = ftp_file.split("/", 1)
        _, file_name = ftp_file_path.rsplit("/", 1)
        local_file_path = Path(context.data_dir_irr) / file_name
        extracted_file_path = Path(context.out_dir_irr) / file_name.rstrip(".gz")

        print("Extracting " + file_name)
        with gzip.open(local_file_path, 'rb') as r:
            with open(extracted_file_path, 'wb') as w:
                shutil.copyfileobj(r, w)
