import hashlib

def calculate_sha256(file_path):
    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)

    return sha256_hash.hexdigest()

def print_section_header(name):
    print()
    print("-" * 3 + f" {name} " + "-" * 3)
    print()


def rir_from_str(s):
    sl = s.lower()
    if "arin" in sl:
        return "ARIN"
    if "ripe" in sl:
        return "RIPE"
    if "lacnic" in sl:
        return "LACNIC"
    if "afrinic" in sl:
        return "AFRINIC"
    if "apnic" in sl:
        return "APNIC"

    raise Exception("No RIR found in String")
