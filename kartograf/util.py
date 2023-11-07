import hashlib


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
