import hashlib
import re
import subprocess
import time


def calculate_sha256(file_path):
    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as file:
        for byte_block in iter(lambda: file.read(4096), b""):
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

            if version_number < 8.4:
                raise Exception("Error: rpki-client version 8.4 or higher is "
                                "required.")
            elif version_number >= 9.0:
                print("Warning: Kartograf has not been tested with "
                      "rpki-client version 9 or higher.")
            else:
                print(f"Using rpki-client version {version}.")
        else:
            raise Exception(exception_msg)

    except subprocess.CalledProcessError:
        raise Exception(exception_msg)


def wait_for_launch(wait):
    wait = int(wait)

    while True:
        current_time = time.time()

        if current_time >= wait:
            break

        time.sleep(1)
