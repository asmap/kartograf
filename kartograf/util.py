import asyncio
import hashlib
import ipaddress
import os
import re
import subprocess
import time


def calculate_sha256(file_path):
    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as file:
        for byte_block in iter(lambda: file.read(4096), b""):
            sha256_hash.update(byte_block)

    return sha256_hash.hexdigest()


def calculate_sha256_directory(directory_path):
    sha256_hash = hashlib.sha256()

    for root, dirs, files in os.walk(directory_path):
        for file in sorted(files):
            file_path = os.path.join(root, file)
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
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


def check_compatibility():
    exception_msg = "Could not determine rpki-client version. Is it installed?"

    try:
        result = subprocess.run(['rpki-client', '-V'],
                                capture_output=True,
                                text=True,
                                check=True)

        # On OpenBSD the result should include 'rpki-client', everywhere else
        # it should be 'rpki-client-portable'.
        version_match = re.search(r'rpki-client(?:-portable)? (\d+\.\d+)',
                                  result.stderr)
        if version_match:
            version = version_match.group(1)
            version_number = float(version)
            latest_version = 9.1

            if version_number < 8.4:
                raise Exception("Error: rpki-client version 8.4 or higher is "
                                "required.")
            elif version_number == latest_version:
                print(f"Using rpki-client version {version} (recommended).")
            elif version_number > latest_version:
                print("Warning: This kartograf version has not been tested with "
                      f"rpki-client versions higher than {latest_version}.")
            else:
                print(f"Using rpki-client version {version}. Please beware that running with the latest tested version ({latest_version}) is recommend.")

        else:
            raise Exception(exception_msg)

    except subprocess.CalledProcessError:
        raise Exception(exception_msg)


async def wait_for_launch(wait, warmup_function):
    wait = int(wait)
    warmup = None
    warmup_running = False
    cache_filled = False
    cache_msg = "Cache not filled."

    loop = asyncio.get_event_loop()

    while True:
        current_time = time.time()

        if current_time >= wait:
            print("\nStarting...")
            break

        remaining = wait - current_time
        days, remainder = divmod(remaining, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours, minutes, seconds = int(days), int(hours), int(minutes), int(seconds)

        # Print the countdown, using '\r' to remain on the same line
        print(f"Countdown:{'' if days <= 0 else ' ' + str(days) + ' day(s),'}"
              f"{'' if hours <= 0 else ' ' + str(hours) + ' hour(s),'}"
              f"{'' if minutes <= 0 else ' ' + str(minutes) + ' minute(s),'}"
              f" {seconds} second(s). {cache_msg}".ljust(80), end='\r')

        if warmup_running and warmup is not None:
            if warmup.returncode is not None:
                cache_msg = "Cache filled!"
                warmup_running = False

        if remaining < 1800 and not warmup_running and warmup is None:
            warmup = await warmup_function()
            warmup_running = True
            cache_msg = "Cache warming up!"

        await asyncio.sleep(1)


def format_pfx(pfx):
    """
    We have seen some formatting issues like leading zeros in the prefix,
    which can cause problems.
    """
    try:
        if '/' in pfx:
            formatted_pfx = str(ipaddress.ip_network(pfx))
            return f"{formatted_pfx}"
        else:
            return str(ipaddress.ip_address(pfx))
    except ValueError:
        return pfx
