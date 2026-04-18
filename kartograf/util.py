from functools import partial
import hashlib
import ipaddress
import os
import re
import subprocess
import time

RPKI_VERSION = "9.7"
RPKI_MAX_THREADS = 8


class KartografConfigurationError(Exception):
    """Raised when runtime configuration is invalid for map generation."""


def _version_to_tuple(version):
    if isinstance(version, tuple):
        if len(version) < 2:
            return None
        try:
            return int(version[0]), int(version[1])
        except (TypeError, ValueError):
            return None

    if isinstance(version, str):
        match = re.search(r"(\d+)\.(\d+)", version)
        if not match:
            return None
        return int(match.group(1)), int(match.group(2))

    if isinstance(version, (int, float)):
        match = re.search(r"(\d+)\.(\d+)", str(version))
        if not match:
            return int(version), 0
        return int(match.group(1)), int(match.group(2))

    return None


def _format_version(version_tuple):
    major, minor = version_tuple
    return f"{major}.{minor}"


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
            return version_match.group(1)
        return None

    except FileNotFoundError:
        return None


def check_compatibility(rpki_backend="legacy"):
    if rpki_backend not in {"legacy", "threaded"}:
        raise KartografConfigurationError(
            f"Unknown RPKI backend '{rpki_backend}'. Use 'legacy' or 'threaded'."
        )

    local_version_raw = get_rpki_local_version()
    local_version = _version_to_tuple(local_version_raw)
    latest_version = _version_to_tuple(RPKI_VERSION)

    if local_version is None:
        raise KartografConfigurationError(
            "Could not determine rpki-client version. Is it installed?"
        )
    if local_version < (8, 4):
        raise KartografConfigurationError(
            "rpki-client version 8.4 or higher is required."
        )

    if rpki_backend == "threaded" and local_version < (9, 6):
        raise KartografConfigurationError(
            "--rpki-backend threaded requires rpki-client version 9.6 or higher. "
            "No automatic fallback to legacy backend is performed."
        )

    print(f"Selected RPKI backend: {rpki_backend}")

    if rpki_backend == "legacy" and local_version >= (9, 6):
        print(
            "Notice: rpki-client 9.6+ detected, but using 'legacy' backend "
            "for deterministic hashing. '--rpki-backend threaded' enables "
            "the experimental threaded validation path."
        )

    if local_version == latest_version:
        print(
            "Using rpki-client version "
            f"{_format_version(local_version)} (recommended)."
        )
    elif local_version > latest_version:
        print(
            "Warning: This kartograf version has not been tested with "
            f"rpki-client versions higher than {_format_version(latest_version)}."
        )
    else:
        print(
            "Using rpki-client version "
            f"{_format_version(local_version)}. Please beware that running "
            "with the latest tested version "
            f"({_format_version(latest_version)}) is recommended."
        )


def get_rpki_thread_count(max_threads=RPKI_MAX_THREADS):
    effective_max = max_threads
    env_max_threads = os.getenv("RPKI_MAX_THREADS")
    if env_max_threads:
        try:
            effective_max = min(max_threads, int(env_max_threads))
        except ValueError:
            # Ignore malformed overrides and fall back to configured defaults.
            pass

    effective_max = max(1, effective_max)
    cpu_count = os.cpu_count() or 1
    return max(1, min(cpu_count, effective_max))


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


def parse_pfx(pfx):
    """
    Attempt to format an IP network or address.
    If invalid, return None.
    """
    if is_valid_pfx(pfx):
        if "/" in pfx:
            formatted_pfx = str(ipaddress.ip_network(pfx))
            return f"{formatted_pfx}"
        return str(ipaddress.ip_address(pfx))
    return None


def is_valid_pfx(pfx):
    """
    Check whether the IP network or address provided is valid.
    """
    try:
        if "/" in pfx:
            ipaddress.ip_network(pfx)
            return True
        ipaddress.ip_address(pfx)
        return True
    except ValueError:
        return False


def get_root_network(pfx):
    """
    Extract the top-level network from an IPv4 or IPv6 address.
    Returns the value as an integer.
    """
    network = parse_pfx(pfx)
    if network:
        v = ipaddress.ip_network(network).version
        if v == 4:
            return int(network.split(".", maxsplit=1)[0])

        root_net = network.split(":", maxsplit=1)[0]
        if root_net:
            return int(root_net, 16)
    return None
