from functools import partial
import hashlib
import ipaddress
import os
import re
import subprocess
import time

RPKI_VERSION = 9.3


def calculate_sha256(file_path):
    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as file:
        for byte_block in iter(lambda: file.read(4096), b""):
            sha256_hash.update(byte_block)

    return sha256_hash.hexdigest()


def calculate_sha256_directory(directory_path):
    sha256_hash = hashlib.sha256()

    for root, _dirs, files in os.walk(directory_path):
        for file in sorted(files):
            file_path = os.path.join(root, file)
            with open(file_path, "rb") as f:
                read_block = partial(f.read, 4096)
                for byte_block in iter(read_block, b""):
                    sha256_hash.update(byte_block)

    return sha256_hash.hexdigest()


def print_section_header(name):
    print()
    print("-" * 3 + f" {name} " + "-" * 3)
    print()


def rir_from_str(maybe_rir):
    maybe_rir = maybe_rir.lower()
    if "arin" in maybe_rir:
        return "ARIN"
    if "ripe" in maybe_rir:
        return "RIPE"
    if "lacnic" in maybe_rir:
        return "LACNIC"
    if "afrinic" in maybe_rir:
        return "AFRINIC"
    if "apnic" in maybe_rir:
        return "APNIC"

    raise Exception("No RIR found in String")


def get_rpki_local_version():
    """Return the rpki-client version in the user's path"""
    try:
        result = subprocess.run(
            ["rpki-client", "-V"], capture_output=True, text=True, check=True
        )

        # On OpenBSD the result should include 'rpki-client', everywhere else
        # it should be 'rpki-client-portable'.
        version_match = re.search(
            r"rpki-client(?:-portable)? (\d+\.\d+)", result.stderr
        )
        if version_match:
            version = version_match.group(1)
            return float(version)
        return None

    except FileNotFoundError:
        return None


def check_compatibility():
    local_version = get_rpki_local_version()
    latest_version = RPKI_VERSION

    if local_version is None:
        raise RuntimeError("Could not determine rpki-client version. Is it installed?")
    if local_version < 8.4:
        raise Exception("Error: rpki-client version 8.4 or higher is required.")

    if local_version == latest_version:
        print(f"Using rpki-client version {local_version} (recommended).")
    elif local_version > latest_version:
        print(
            "Warning: This kartograf version has not been tested with "
            f"rpki-client versions higher than {latest_version}."
        )
    else:
        print(
            f"Using rpki-client version {local_version}. Please beware that running with the latest tested version ({latest_version}) is recommend."
        )


def wait_for_launch(wait):
    wait = int(wait)

    while True:
        current_time = time.time()

        if current_time >= wait:
            print("\nStarting...")
            break

        remaining = wait - current_time
        days, remainder = divmod(remaining, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours, minutes, seconds = (
            int(days),
            int(hours),
            int(minutes),
            int(seconds),
        )

        # Print the countdown, using '\r' to remain on the same line
        print(
            f"Countdown:{'' if days <= 0 else ' ' + str(days) + ' day(s),'}"
            f"{'' if hours <= 0 else ' ' + str(hours) + ' hour(s),'}"
            f"{'' if minutes <= 0 else ' ' + str(minutes) + ' minute(s),'}"
            f" {seconds} second(s)".ljust(80),
            end="\r",
        )

        time.sleep(1)


def format_pfx(pfx):
    """
    We have seen some formatting issues like leading zeros in the prefix,
    which can cause problems.
    """
    try:
        if "/" in pfx:
            formatted_pfx = str(ipaddress.ip_network(pfx))
            return f"{formatted_pfx}"
        return str(ipaddress.ip_address(pfx))
    except ValueError:
        return pfx
