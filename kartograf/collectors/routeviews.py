from datetime import timedelta
from pathlib import Path
import gzip
import shutil
import sys
import tempfile
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


def _get_gzip_mtime(url):
    """Download a gzip file to a temp path and return its header mtime."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".gz")
    try:
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()
        for chunk in response.iter_content(chunk_size=8192):
            tmp.write(chunk)
        tmp.close()
        with gzip.open(tmp.name, 'rb') as f:
            f.read(1)  # header is parsed on first read
            return f.mtime
    finally:
        Path(tmp.name).unlink(missing_ok=True)


def _pick_pfx2as_files(html):
    """Return all pfx2as.gz filenames from the directory listing, in order."""
    soup = BeautifulSoup(html, 'html.parser')
    files = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.endswith(".pfx2as.gz"):
            files.append(href)
    return files


def latest_link(base, epoch_datetime):
    """Find the latest pfx2as file that existed at or before the epoch.

    Downloads the latest file and checks its gzip header timestamp.
    If it was created after the epoch, falls back to the previous file.
    """
    epoch_ts = int(epoch_datetime.timestamp())
    ym = year_and_month(epoch_datetime)
    url = base + ym

    result = _pick_valid_file(url, epoch_ts)
    if result:
        return result

    print(f"No valid pfx2as.gz files at {url}. Trying the previous month.")

    last_month = epoch_datetime - timedelta(days=epoch_datetime.day)
    fallback_url = base + year_and_month(last_month)

    result = _pick_valid_file(fallback_url, epoch_ts)
    if result:
        return result

    print(f"The page at {fallback_url} also has no pfx2as.gz files. "
          f"Download of Routeviews pfx2as data failed.")
    sys.exit()


def _pick_valid_file(base_url, epoch_ts):
    """Pick the latest pfx2as file whose gzip mtime is <= epoch_ts.

    Fetches the directory listing, then checks files from newest to oldest.
    """
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            response = requests.get(base_url, timeout=600)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            if attempt < RETRY_ATTEMPTS:
                print(f"Request to {base_url} failed ({e}), "
                      f"retrying in {RETRY_DELAY}s "
                      f"(attempt {attempt}/{RETRY_ATTEMPTS})...")
                time.sleep(RETRY_DELAY)
            else:
                raise

    files = _pick_pfx2as_files(response.text)
    if not files:
        return None

    # Check from newest to oldest
    for filename in reversed(files):
        file_url = base_url + filename
        mtime = _get_gzip_mtime(file_url)
        if mtime and mtime > epoch_ts:
            print(f"Skipping {filename} (gzip mtime {mtime} > epoch {epoch_ts})")
            continue
        return file_url

    return None


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
