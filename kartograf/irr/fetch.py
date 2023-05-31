from ftplib import FTP
import gzip
import shutil

from kartograf.timed import timed

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
    for ftp_file in IRR_FILE_ADDRESSES:
        host, ftp_file_path = ftp_file.split("/", 1)
        path, file_name = ftp_file_path.rsplit("/", 1)
        ftp = FTP(host)
        ftp.login()
        ftp.cwd(path)

        print("Downloading " + file_name)
        local_file_path = context.data_dir_irr + file_name

        try:
            with open(local_file_path, 'wb') as f:
                ftp.retrbinary("RETR " + file_name, f.write)
        except EOFError:
            pass

        ftp.close()

        if file_name.endswith(".gz"):
            print("Extracting " + file_name)
            with gzip.open(local_file_path, 'rb') as r:
                extracted_file_path = local_file_path.rstrip(".gz")
                with open(extracted_file_path, 'wb') as w:
                    shutil.copyfileobj(r, w)
