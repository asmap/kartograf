#!/usr/bin/env python3
"""
Analysis script to compare RPKI, IRR, and Routeviews data contributions.
Shows how much additional IP network data each source adds to the final dataset.
"""

import ipaddress
from pathlib import Path
import sys
from typing import Set, Dict
import argparse

def load_networks_from_file(file_path: Path) -> Set[str]:
    """Load IP networks from a file, returning a set of prefixes."""
    networks = set()
    if not file_path.exists():
        print(f"Warning: File {file_path} does not exist")
        return networks

    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and ' ' in line:
                prefix = line.split()[0]
                try:
                    ipaddress.ip_network(prefix)
                    networks.add(prefix)
                except ValueError:
                    print(f"Invalid prefix: {prefix}")
                    continue
    return networks

def calculate_coverage_stats(base_networks: Set[str], additional_networks: Set[str]) -> Dict[str, int]:
    """Calculate statistics about how much additional data a source provides."""
    total_additional = len(additional_networks)
    unique_to_additional = len(additional_networks - base_networks)
    overlapping = len(additional_networks & base_networks)

    return {
        'total_additional': total_additional,
        'unique_to_additional': unique_to_additional,
        'overlapping': overlapping,
        'percentage_unique': (unique_to_additional / total_additional * 100) if total_additional > 0 else 0
    }

def analyze_data_contributions(out_dir: Path) -> None:
    """Analyze the data contributions from different sources."""

    rpki_file = out_dir / "rpki" / "rpki_final.txt"
    irr_file = out_dir / "irr" / "irr_final.txt"
    routeviews_file = out_dir / "collectors" / "pfx2asn_clean.txt"

    rpki_irr_merged = out_dir / "merged_file_rpki_irr.txt"
    rpki_irr_rv_merged = out_dir / "merged_file_rpki_irr_rv.txt"

    print("=== RPKI, IRR, and Routeviews Data Analysis ===\n")

    # Load base RPKI data
    print("Loading RPKI data...")
    rpki_networks = load_networks_from_file(rpki_file)
    print(f"RPKI networks loaded: {len(rpki_networks)}")

    # Load IRR data
    print("Loading IRR data...")
    irr_networks = load_networks_from_file(irr_file)
    print(f"IRR networks loaded: {len(irr_networks)}")

    # Load Routeviews data
    print("Loading Routeviews data...")
    routeviews_networks = load_networks_from_file(routeviews_file)
    print(f"Routeviews networks loaded: {len(routeviews_networks)}")

    print("\n" + "="*60)

    # Analyze IRR contribution to RPKI base
    if len(irr_networks) > 0:
        print("\n1. IRR data, relative to RPKI base:")
        print("-" * 50)
        irr_stats = calculate_coverage_stats(rpki_networks, irr_networks)

        print(f"Total IRR networks: {irr_stats['total_additional']:,}")
        print(f"IRR networks already in RPKI: {irr_stats['overlapping']:,}")
        print(f"Unique IRR networks: {irr_stats['unique_to_additional']:,}")
        print(f"Percentage of IRR data that is unique: {irr_stats['percentage_unique']:.2f}%")

        # Check merged file
        if rpki_irr_merged.exists():
            merged_networks = load_networks_from_file(rpki_irr_merged)
            total_after_irr = len(merged_networks)
            added_by_irr = total_after_irr - len(rpki_networks)
            print("* After merge *")
            print(f"Total networks after IRR merge: {total_after_irr:,}")
            print(f"Net networks added by IRR: {added_by_irr:,}")
            if len(rpki_networks) > 0:
                print(f"IRR increased dataset by: {(added_by_irr / len(rpki_networks) * 100):.2f}%")

    # Analyze Routeviews contribution
    if len(routeviews_networks) > 0:
        print("\n2. Routeviews data, relative to RPKI + IRR base:")
        print("-" * 50)
        rv_stats = calculate_coverage_stats(merged_networks, routeviews_networks)

        print(f"Total Routeviews networks: {rv_stats['total_additional']:,}")
        print(f"Routeviews networks already in RPKI+IRR: {rv_stats['overlapping']:,}")
        print(f"Unique Routeviews networks (added to base): {rv_stats['unique_to_additional']:,}")
        print(f"Percentage of Routeviews data that is unique: {rv_stats['percentage_unique']:.2f}%")

    # Analyze combined contribution if all three sources are used
    if rpki_irr_rv_merged.exists():
        print("\n3. Combined data (RPKI + IRR + Routeviews):")
        print("-" * 50)
        final_networks = load_networks_from_file(rpki_irr_rv_merged)
        total_final = len(final_networks)
        total_added = total_final - len(rpki_networks)

        print(f"RPKI base networks: {len(rpki_networks):,}")
        print(f"Final combined networks: {total_final:,}")
        print(f"Total networks added by IRR + Routeviews: {total_added:,}")
        if len(rpki_networks) > 0:
            print(f"Combined sources increased dataset by: {(total_added / len(rpki_networks) * 100):.2f}%")

    # Cross-source analysis
    if len(irr_networks) > 0 and len(routeviews_networks) > 0:
        print("\n4. Cross-Source Analysis:")
        print("-" * 50)
        irr_rv_overlap = len(irr_networks & routeviews_networks)
        irr_only = len(irr_networks - routeviews_networks - rpki_networks)
        rv_only = len(routeviews_networks - irr_networks - rpki_networks)

        print(f"Networks common to IRR and Routeviews: {irr_rv_overlap:,}")
        print(f"Networks unique to IRR (not in RPKI or Routeviews): {irr_only:,}")
        print(f"Networks unique to Routeviews (not in RPKI or IRR): {rv_only:,}")
        print("\n")

def main():
    parser = argparse.ArgumentParser(description='Analyze RPKI, IRR, and Routeviews data contributions')
    parser.add_argument('--out-dir', type=Path, default=Path('.'),
                        help='Base directory containing the kartograf output directories (default: current directory)')

    args = parser.parse_args()

    if not args.out_dir.exists():
        print(f"Error: Data directory {args.out_dir} does not exist")
        return 1

    analyze_data_contributions(args.out_dir)
    return 0

if __name__ == "__main__":
    sys.exit(main())
