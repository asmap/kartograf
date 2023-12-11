from datetime import datetime, timedelta
import gzip
import shutil
import sys

from bs4 import BeautifulSoup
import requests

from kartograf.timed import timed

# Routeviews Prefix to AS mappings Dataset for IPv4 and IPv6
# https://www.caida.org/catalog/datasets/routeviews-prefix2as/
PFX2AS_V4 = "https://publicdata.caida.org/datasets/routing/routeviews-prefix2as/"
PFX2AS_V6 = "https://publicdata.caida.org/datasets/routing/routeviews6-prefix2as/"


def latest_link(base):
    now = datetime.now()
    ym = year_and_month(now)
    url = base + ym

    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        print(f"The page at {url} couldn't be fetched. "
              f"Trying the previous month.")

        last_month = now - timedelta(days=now.day)
        ym = year_and_month(last_month)
        url = base + ym

        try:
            response = requests.get(url)
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            print(f"The page at {url} couldn't be fetched. "
                  f"Download of Routeviews pfx2as data failed.")
            sys.exit()

    soup = BeautifulSoup(response.text, 'html.parser')

    links = [a["href"] for a in soup.find_all("a", href=True)]

    for link in links:
        if link.endswith(".pfx2as.gz"):
            latest = link

    return url + latest


def year_and_month(now):
    year = now.year
    month = str(now.month).zfill(2)
    return f'{year}/{month}/'


def download(url, file):
    print(f'Downloading {url}')
    gz_file = file + ".gz"

    response = requests.get(url, stream=True, timeout=300)
    with open(gz_file, 'wb') as gz:
        for chunk in response.iter_content(chunk_size=8192):
            gz.write(chunk)


def extract(file, context):
    gz_file = context.data_dir_collectors + file + ".gz"
    file = context.out_dir_collectors + file

    print(f'Unzipping {gz_file}')
    with gzip.open(gz_file, 'rb') as f_in:
        with open(file, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

    print(f'Formatting {file}')
    with open(file, "r") as read:
        lines = read.readlines()

    with open(file, "w") as write:
        for line in lines:
            fragments = line.strip().split()
            formatted = f'{fragments[0]}/{fragments[1]} AS{fragments[2]}'
            write.write(formatted + '\n')


@timed
def fetch_routeviews_pfx2as(context):
    path = context.data_dir_collectors
    v4_file = f'{path}routeviews_pfx2asn_ip4.txt'
    v6_file = f'{path}routeviews_pfx2asn_ip6.txt'

    download(latest_link(PFX2AS_V4), v4_file)
    download(latest_link(PFX2AS_V6), v6_file)


def extract_routeviews_pfx2as(context):
    v4_file_name = 'routeviews_pfx2asn_ip4.txt'
    v6_file_name = 'routeviews_pfx2asn_ip6.txt'

    extract(v4_file_name, context)
    extract(v6_file_name, context)

    v4_file = context.out_dir_collectors + v4_file_name
    v6_file = context.out_dir_collectors + v6_file_name
    out_file = f'{context.out_dir_collectors}pfx2asn.txt'

    with open(v4_file, 'r') as v4, \
            open(v6_file, 'r') as v6, \
            open(out_file, 'w') as out:
        out.write(v4.read())
        out.write(v6.read())
