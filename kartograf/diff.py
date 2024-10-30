def diff(f1, f2, out_file):
    '''
    Compare two ASMap files, and write out changes to an out_file.
    Prints the size of each type of change (assigned, reassigned, or unassigned).
    '''
    f1_dict = dict()
    with open(f1, "r") as f:
        for line in f:
            pfx, asn = line.split()
            f1_dict[pfx] = asn

    f2_dict = dict()
    with open(f2, "r") as f:
        for line in f:
            pfx, asn = line.split()
            f2_dict[pfx] = asn

    k1 = f1_dict.keys()
    k2 = f2_dict.keys()

    left = set(k1) - set(k2)
    right = set(k2) - set(k1)
    overlap = set(k1) & set(k2)

    changes = []
    for network in overlap:
        asn1 = f1_dict[network]
        asn2 = f2_dict[network]
        if asn1 != asn2:
            changes.append(f"{network} reassigned from {asn1} to {asn2}\n")

    removed = []
    for network in left:
        removed.append(f"{network} unassigned from {f1_dict[network]} \n")

    added = []
    for network in right:
        added.append(f"{network} assigned to {f2_dict[network]}\n")

    with open(out_file, "w") as f:
        f.writelines(changes + removed + added)
        f.close()

    print(f"Wrote to {out_file}\n")
    print(f"Changes: {len(changes)}")
    print(f"Removed: {len(removed)}")
    print(f"Added:   {len(added)}")

