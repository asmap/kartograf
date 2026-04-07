from datetime import datetime, timedelta
from pathlib import Path
import gzip
import shutil
import sys
import time

from bs4 import BeautifulSoup
import requests

from kartograf.timed import timed
from kartograf.util import calculate_sha256

# Routeviews Prefix to AS mappings Dataset for IPv4 and IPv6
# https://www.caida.org/catalog/datasets/routeviews-prefix2as/
PFX2AS_V4 = "https://publicdata.caida.org/datasets/routing/routeviews-prefix2as/"
PFX2AS_V6 = "https://publicdata.caida.org/datasets/routing/routeviews6-prefix2as/"

RETRY_ATTEMPTS = 3
RETRY_DELAY = 10


def _try_fetch_latest(base_url):
    """Fetch directory listing and return the latest pfx2as file.

    Returns the full URL on success, None if the page exists but contains
    no pfx2as.gz files.  Raises on request failures so the caller can retry.
    """
    response = requests.get(base_url, timeout=600)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    latest = _pick_latest_pfx2as(response.text)
    if latest:
        return base_url + latest
    return None


def _fetch_with_retry(base_url):
    """Call _try_fetch_latest with retries for request failures only."""
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            return _try_fetch_latest(base_url)
        except requests.exceptions.RequestException as e:
            if attempt < RETRY_ATTEMPTS:
                print(f"Request to {base_url} failed ({e}), "
                      f"retrying in {RETRY_DELAY}s "
                      f"(attempt {attempt}/{RETRY_ATTEMPTS})...")
                time.sleep(RETRY_DELAY)
            else:
                raise


def latest_link(base, epoch_datetime):
    ym = year_and_month(epoch_datetime)
    url = base + ym

    result = _fetch_with_retry(url)
    if result:
        return result

    print(f"No pfx2as.gz files at {url}. Trying the previous month.")

    last_month = epoch_datetime - timedelta(days=epoch_datetime.day)
    fallback_url = base + year_and_month(last_month)

    result = _fetch_with_retry(fallback_url)
    if result:
        return result

    print(f"The page at {fallback_url} also has no pfx2as.gz files. "
          f"Download of Routeviews pfx2as data failed.")
    sys.exit()


def _pick_latest_pfx2as(html):
    soup = BeautifulSoup(html, 'html.parser')
    links = [a["href"] for a in soup.find_all("a", href=True)]
    latest = ""
    for link in links:
        if link.endswith(".pfx2as.gz"):
            latest = link
    return latest


def year_and_month(now):
    year = now.year
    month = str(now.month).zfill(2)
    return f'{year}/{month}/'


def download(url, file):
    print(f'Downloading from {url}')

    response = requests.get(url, stream=True, timeout=300)
    with open(file, 'wb') as gz:
        for chunk in response.iter_content(chunk_size=8192):
            gz.write(chunk)


def extract(file, context):
    gz_file = Path(context.data_dir_collectors) / (file + ".gz")
    file = Path(context.out_dir_collectors) / file

    print(f'Extracting {gz_file.name}')
    with gzip.open(gz_file, 'rb') as f_in:
        with open(file, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

    with open(file, "r") as read:
        lines = read.readlines()

    with open(file, "w") as write:
        for line in lines:
            fragments = line.strip().split()
            formatted = f'{fragments[0]}/{fragments[1]} AS{fragments[2]}'
            write.write(formatted + '\n')


def resolve_routeviews_urls(context):
    """Resolve RouteViews download URLs early so all participants in a
    coordinated launch see the same CAIDA directory state."""
    epoch_dt = context.epoch_datetime
    context.routeviews_v4_url = latest_link(PFX2AS_V4, epoch_dt)
    context.routeviews_v6_url = latest_link(PFX2AS_V6, epoch_dt)
    print(f"Resolved RouteViews URLs:\n  v4: {context.routeviews_v4_url}"
          f"\n  v6: {context.routeviews_v6_url}")


@timed
def fetch_routeviews_pfx2as(context):
    path = Path(context.data_dir_collectors)
    v4_file_gz = path / "routeviews_pfx2asn_ip4.txt.gz"
    v6_file_gz = path / "routeviews_pfx2asn_ip6.txt.gz"

    download(context.routeviews_v4_url, v4_file_gz)
    print(f"Downloaded {v4_file_gz.name}, file hash: {calculate_sha256(v4_file_gz)}")
    download(context.routeviews_v6_url, v6_file_gz)
    print(f"Downloaded {v6_file_gz.name}, file hash: {calculate_sha256(v6_file_gz)}")


def extract_routeviews_pfx2as(context):
    v4_file_name = 'routeviews_pfx2asn_ip4.txt'
    v6_file_name = 'routeviews_pfx2asn_ip6.txt'

    extract(v4_file_name, context)
    extract(v6_file_name, context)

    v4_file = Path(context.out_dir_collectors) / v4_file_name
    v6_file = Path(context.out_dir_collectors) / v6_file_name
    out_file = Path(context.out_dir_collectors) / "pfx2asn.txt"

    context.cleanup_out_files += [v4_file, v6_file, out_file]

    with open(v4_file, 'r') as v4, \
            open(v6_file, 'r') as v6, \
            open(out_file, 'w') as out:
        out.write(v4.read())
        out.write(v6.read())
