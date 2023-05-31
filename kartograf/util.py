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
