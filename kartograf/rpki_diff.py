#!/usr/bin/env python3
"""
RPKI Cache Diff Tool for ASmap collaborative launches.

Compares RPKI data between participants at three levels:
1. Cache-level: per-repo directory hash comparison
2. ROA-level: compare rpki_raw.json to find which ROAs differ
3. Map-level: compare rpki_final.txt to show prefix/ASN impact

Usage:
  # Compare two participants' data directories
  python3 rpki_diff.py compare <dir_a> <dir_b> --names alice bob

  # Parse cache hashes from collaborative launch logs
  python3 rpki_diff.py parse-hashes <logfile>

  # Compare rpki_raw.json files
  python3 rpki_diff.py compare-roas <json_a> <json_b> --names alice bob

  # Compare rpki_final.txt files
  python3 rpki_diff.py compare-maps <map_a> <map_b> --names alice bob
"""

import argparse
import hashlib
import json
import os
import sys
from collections import defaultdict
from pathlib import Path


def calculate_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def calculate_dir_hash(dirpath):
    """Hash all files in a directory (sorted) to get a deterministic hash."""
    h = hashlib.sha256()
    for root, dirs, files in sorted(os.walk(dirpath)):
        for fname in sorted(files):
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, dirpath)
            h.update(rel.encode())
            h.update(calculate_sha256(fpath).encode())
    return h.hexdigest()


# --- Cache-level comparison ---

def compare_cache_dirs(dir_a, dir_b, name_a="A", name_b="B"):
    """Compare two RPKI cache directories repo-by-repo."""
    repos_a = {p.name: p for p in Path(dir_a).iterdir() if p.is_dir()}
    repos_b = {p.name: p for p in Path(dir_b).iterdir() if p.is_dir()}

    all_repos = sorted(set(repos_a.keys()) | set(repos_b.keys()))

    print(f"{'Repo':<45} {'Files A':>8} {'Files B':>8} {'Match':>6}")
    print("-" * 75)

    matching = 0
    differing = 0
    only_a = 0
    only_b = 0

    for repo in all_repos:
        in_a = repo in repos_a
        in_b = repo in repos_b

        if in_a and in_b:
            files_a = list(repos_a[repo].rglob('*'))
            files_a = [f for f in files_a if f.is_file()]
            files_b = list(repos_b[repo].rglob('*'))
            files_b = [f for f in files_b if f.is_file()]

            hash_a = calculate_dir_hash(repos_a[repo])
            hash_b = calculate_dir_hash(repos_b[repo])

            match = hash_a == hash_b
            status = "YES" if match else "NO"
            if match:
                matching += 1
            else:
                differing += 1

            print(f"{repo:<45} {len(files_a):>8} {len(files_b):>8} {status:>6}")

            if not match:
                # Show file-level diff
                names_a = {f.relative_to(repos_a[repo]) for f in files_a}
                names_b = {f.relative_to(repos_b[repo]) for f in files_b}
                only_in_a = names_a - names_b
                only_in_b = names_b - names_a
                common = names_a & names_b

                changed = 0
                for fname in common:
                    fa = repos_a[repo] / fname
                    fb = repos_b[repo] / fname
                    if calculate_sha256(fa) != calculate_sha256(fb):
                        changed += 1

                print(f"  -> only in {name_a}: {len(only_in_a)}, "
                      f"only in {name_b}: {len(only_in_b)}, "
                      f"content differs: {changed}")

        elif in_a:
            files_a = list(repos_a[repo].rglob('*'))
            files_a = [f for f in files_a if f.is_file()]
            print(f"{repo:<45} {len(files_a):>8} {'—':>8} {'ONLY_A':>6}")
            only_a += 1
        else:
            files_b = list(repos_b[repo].rglob('*'))
            files_b = [f for f in files_b if f.is_file()]
            print(f"{repo:<45} {'—':>8} {len(files_b):>8} {'ONLY_B':>6}")
            only_b += 1

    print("-" * 75)
    print(f"Matching: {matching}  Differing: {differing}  "
          f"Only in {name_a}: {only_a}  Only in {name_b}: {only_b}")

    return differing + only_a + only_b


# --- ROA-level comparison ---

def load_roas(filepath):
    """Load rpki_raw.json and index by hash_id."""
    with open(filepath) as f:
        data = json.load(f)
    by_hash = {}
    for roa in data:
        hid = roa.get("hash_id", "")
        by_hash[hid] = roa
    return by_hash, data


def compare_roas(file_a, file_b, name_a="A", name_b="B"):
    """Compare two rpki_raw.json files at the ROA level."""
    roas_a, data_a = load_roas(file_a)
    roas_b, data_b = load_roas(file_b)

    ids_a = set(roas_a.keys())
    ids_b = set(roas_b.keys())

    only_a = ids_a - ids_b
    only_b = ids_b - ids_a
    common = ids_a & ids_b

    # Check for content differences in common ROAs
    content_diff = 0
    vrp_diffs = []
    for hid in common:
        if roas_a[hid] != roas_b[hid]:
            content_diff += 1
            vrp_diffs.append((hid, roas_a[hid], roas_b[hid]))

    print(f"=== ROA Comparison: {name_a} vs {name_b} ===\n")
    print(f"Total ROAs in {name_a}: {len(data_a):,}")
    print(f"Total ROAs in {name_b}: {len(data_b):,}")
    print(f"Common (by hash_id):    {len(common):,}")
    print(f"Only in {name_a}:            {len(only_a):,}")
    print(f"Only in {name_b}:            {len(only_b):,}")
    print(f"Content differs:        {content_diff:,}")

    # Analyze VRPs in ROAs that are only in A or B
    prefixes_only_a = set()
    prefixes_only_b = set()
    asns_only_a = set()
    asns_only_b = set()

    for hid in only_a:
        roa = roas_a[hid]
        for vrp in roa.get("vrps", []):
            prefixes_only_a.add(vrp.get("prefix", ""))
            asns_only_a.add(vrp.get("asid", 0))

    for hid in only_b:
        roa = roas_b[hid]
        for vrp in roa.get("vrps", []):
            prefixes_only_b.add(vrp.get("prefix", ""))
            asns_only_b.add(vrp.get("asid", 0))

    if only_a or only_b:
        print(f"\n--- VRP Impact ---")
        print(f"Unique prefixes only in {name_a}: {len(prefixes_only_a):,}")
        print(f"Unique prefixes only in {name_b}: {len(prefixes_only_b):,}")
        print(f"Unique ASNs only in {name_a}:     {len(asns_only_a):,}")
        print(f"Unique ASNs only in {name_b}:     {len(asns_only_b):,}")

    # Show sample differences
    if only_a:
        print(f"\nSample ROAs only in {name_a} (first 5):")
        for hid in list(only_a)[:5]:
            roa = roas_a[hid]
            vrps = roa.get("vrps", [])
            print(f"  hash_id: {hid[:16]}... "
                  f"vrps: {len(vrps)} "
                  f"valid_until: {roa.get('valid_until', '?')}")

    if only_b:
        print(f"\nSample ROAs only in {name_b} (first 5):")
        for hid in list(only_b)[:5]:
            roa = roas_b[hid]
            vrps = roa.get("vrps", [])
            print(f"  hash_id: {hid[:16]}... "
                  f"vrps: {len(vrps)} "
                  f"valid_until: {roa.get('valid_until', '?')}")

    return {
        "only_a": len(only_a),
        "only_b": len(only_b),
        "content_diff": content_diff,
        "prefixes_only_a": len(prefixes_only_a),
        "prefixes_only_b": len(prefixes_only_b),
    }


# --- Map-level comparison ---

def load_map(filepath):
    """Load rpki_final.txt into a dict of prefix -> ASN."""
    mapping = {}
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                mapping[parts[0]] = parts[1]
    return mapping


def compare_maps(file_a, file_b, name_a="A", name_b="B"):
    """Compare two rpki_final.txt files showing prefix/ASN impact."""
    map_a = load_map(file_a)
    map_b = load_map(file_b)

    pfx_a = set(map_a.keys())
    pfx_b = set(map_b.keys())

    only_a = pfx_a - pfx_b
    only_b = pfx_b - pfx_a
    common = pfx_a & pfx_b

    reassigned = {}
    for pfx in common:
        if map_a[pfx] != map_b[pfx]:
            reassigned[pfx] = (map_a[pfx], map_b[pfx])

    print(f"=== RPKI Map Comparison: {name_a} vs {name_b} ===\n")
    print(f"Prefixes in {name_a}: {len(map_a):,}")
    print(f"Prefixes in {name_b}: {len(map_b):,}")
    print(f"Common prefixes:    {len(common):,}")
    print(f"Only in {name_a}:        {len(only_a):,}")
    print(f"Only in {name_b}:        {len(only_b):,}")
    print(f"Reassigned (different ASN): {len(reassigned):,}")

    total_diff = len(only_a) + len(only_b) + len(reassigned)
    total = len(pfx_a | pfx_b)
    if total > 0:
        pct = (total_diff / total) * 100
        print(f"\nDivergence: {total_diff:,} / {total:,} prefixes ({pct:.2f}%)")

    # Analyze reassignments
    if reassigned:
        from collections import Counter
        asn_changes = Counter()
        for pfx, (asn_a, asn_b) in reassigned.items():
            asn_changes[(asn_a, asn_b)] += 1

        print(f"\nTop ASN reassignments ({name_a} -> {name_b}):")
        for (old, new), count in asn_changes.most_common(10):
            print(f"  {old} -> {new}: {count:,} prefixes")

    # Show samples
    if only_a:
        print(f"\nSample prefixes only in {name_a} (first 10):")
        for pfx in sorted(only_a)[:10]:
            print(f"  {pfx} {map_a[pfx]}")

    if only_b:
        print(f"\nSample prefixes only in {name_b} (first 10):")
        for pfx in sorted(only_b)[:10]:
            print(f"  {pfx} {map_b[pfx]}")

    return {
        "only_a": len(only_a),
        "only_b": len(only_b),
        "reassigned": len(reassigned),
        "total_diff": total_diff,
    }


# --- Parse hashes from collaborative launch logs ---

def parse_cache_hashes(text):
    """Parse per-repo cache hashes from the one-liner output participants post."""
    repos = {}
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('$') or line.startswith('CACHE='):
            continue
        parts = line.split('\t')
        if len(parts) >= 3:
            repo = parts[0].strip().lstrip('./')
            files_part = parts[1].strip()
            hash_part = parts[2].strip()
            files = int(files_part.split('=')[1]) if '=' in files_part else 0
            h = hash_part.split('=')[1] if '=' in hash_part else ""
            repos[repo] = {"files": files, "hash": h}
    return repos


def compare_participant_hashes(participants):
    """Compare cache hashes across multiple participants.

    participants: dict of {name: {repo: {files, hash}}}
    """
    all_repos = sorted(set(
        repo for p in participants.values() for repo in p.keys()
    ))
    names = list(participants.keys())

    print(f"=== Cache Hash Comparison ({len(names)} participants) ===\n")

    # Header
    header = f"{'Repo':<40}"
    for name in names:
        header += f" {name[:10]:>12}"
    print(header)
    print("-" * (40 + 13 * len(names)))

    divergent_repos = []

    for repo in all_repos:
        hashes = {}
        for name in names:
            if repo in participants[name]:
                h = participants[name][repo]["hash"]
                hashes[name] = h[:12] if h != "-" else "-"
            else:
                hashes[name] = "missing"

        unique_hashes = set(hashes.values()) - {"-", "missing"}
        is_divergent = len(unique_hashes) > 1

        row = f"{repo:<40}"
        for name in names:
            val = hashes[name]
            row += f" {val:>12}"
        if is_divergent:
            row += "  <-- DIFFERS"
            divergent_repos.append(repo)
        print(row)

    print(f"\nDivergent repos: {len(divergent_repos)} / {len(all_repos)}")
    for repo in divergent_repos:
        unique = set()
        for name in names:
            if repo in participants[name]:
                unique.add(participants[name][repo]["hash"][:24])
        print(f"  {repo}: {len(unique)} distinct hashes")

    return divergent_repos


# --- Full comparison of two data directories ---

def compare_full(dir_a, dir_b, name_a="A", name_b="B"):
    """Run all three levels of comparison on two participant data dirs."""
    cache_a = Path(dir_a) / "rpki" / "cache"
    cache_b = Path(dir_b) / "rpki" / "cache"
    roa_a = Path(dir_a).parent / "out" / Path(dir_a).name / "rpki" / "rpki_raw.json"
    roa_b = Path(dir_b).parent / "out" / Path(dir_b).name / "rpki" / "rpki_raw.json"
    map_a = Path(dir_a).parent / "out" / Path(dir_a).name / "rpki" / "rpki_final.txt"
    map_b = Path(dir_b).parent / "out" / Path(dir_b).name / "rpki" / "rpki_final.txt"

    print("=" * 75)
    print(f"  RPKI Diff: {name_a} vs {name_b}")
    print("=" * 75)

    if cache_a.exists() and cache_b.exists():
        print(f"\n--- Level 1: Cache Directory Comparison ---\n")
        compare_cache_dirs(cache_a, cache_b, name_a, name_b)
    else:
        print(f"\nSkipping cache comparison (directories not found)")

    if roa_a.exists() and roa_b.exists():
        print(f"\n--- Level 2: ROA Comparison ---\n")
        compare_roas(roa_a, roa_b, name_a, name_b)
    else:
        # Try alternate paths
        for alt_a in Path(dir_a).rglob("rpki_raw.json"):
            for alt_b in Path(dir_b).rglob("rpki_raw.json"):
                print(f"\n--- Level 2: ROA Comparison ---\n")
                compare_roas(alt_a, alt_b, name_a, name_b)
                break
            break

    if map_a.exists() and map_b.exists():
        print(f"\n--- Level 3: Map Comparison ---\n")
        compare_maps(map_a, map_b, name_a, name_b)
    else:
        for alt_a in Path(dir_a).rglob("rpki_final.txt"):
            for alt_b in Path(dir_b).rglob("rpki_final.txt"):
                print(f"\n--- Level 3: Map Comparison ---\n")
                compare_maps(alt_a, alt_b, name_a, name_b)
                break
            break


def main():
    parser = argparse.ArgumentParser(
        description="RPKI Cache Diff Tool for ASmap collaborative launches"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # compare: full comparison of two data dirs
    p_compare = subparsers.add_parser("compare",
        help="Full comparison of two participant data directories")
    p_compare.add_argument("dir_a", help="Path to first participant's data dir")
    p_compare.add_argument("dir_b", help="Path to second participant's data dir")
    p_compare.add_argument("--names", nargs=2, default=["A", "B"],
        help="Names for the two participants")

    # compare-roas: compare rpki_raw.json files
    p_roas = subparsers.add_parser("compare-roas",
        help="Compare two rpki_raw.json files")
    p_roas.add_argument("json_a", help="First rpki_raw.json")
    p_roas.add_argument("json_b", help="Second rpki_raw.json")
    p_roas.add_argument("--names", nargs=2, default=["A", "B"])

    # compare-maps: compare rpki_final.txt files
    p_maps = subparsers.add_parser("compare-maps",
        help="Compare two rpki_final.txt files")
    p_maps.add_argument("map_a", help="First rpki_final.txt")
    p_maps.add_argument("map_b", help="Second rpki_final.txt")
    p_maps.add_argument("--names", nargs=2, default=["A", "B"])

    # parse-hashes: parse and compare cache hashes from logs
    p_hashes = subparsers.add_parser("parse-hashes",
        help="Parse and compare cache hash outputs from participants")
    p_hashes.add_argument("files", nargs='+',
        help="Files containing cache hash output (one per participant)")
    p_hashes.add_argument("--names", nargs='+',
        help="Names for each participant")

    args = parser.parse_args()

    if args.command == "compare":
        compare_full(args.dir_a, args.dir_b, *args.names)

    elif args.command == "compare-roas":
        compare_roas(args.json_a, args.json_b, *args.names)

    elif args.command == "compare-maps":
        compare_maps(args.map_a, args.map_b, *args.names)

    elif args.command == "parse-hashes":
        names = args.names or [Path(f).stem for f in args.files]
        participants = {}
        for name, filepath in zip(names, args.files):
            with open(filepath) as f:
                participants[name] = parse_cache_hashes(f.read())
        compare_participant_hashes(participants)


if __name__ == "__main__":
    main()
