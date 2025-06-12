"""CLI functionality for Kartograf."""

import argparse
import os
import sys
import time
import kartograf
from kartograf.kartograf import Kartograf


def create_parser():
    parser = argparse.ArgumentParser()

    # Command which program Kartograf should run
    subparsers = parser.add_subparsers(dest="command")

    parser_map = subparsers.add_parser("map")

    # Write extended logging information to a debug.log file
    # TODO: This is always enabled for now but this should be changed when the
    # tool is more stable
    parser_map.add_argument("-d", "--debug", action="store_true", default=True)
    # Delete artifacts from building the requested map
    parser_map.add_argument("-c", "--cleanup", action="store_true", default=False)

    parser_map.add_argument("-irr", "--irr", action="store_true", default=False)
    parser_map.add_argument("-rv", "--routeviews", action="store_true", default=False)

    # Reproduce a map file from a previous run by using provided input files.
    # The input related arguments are ignored if this flag is set. All provided
    # input files will be used if they are present in the reproduce folder and
    # in the right format. The epoch argument is required for this to work.
    parser_map.add_argument("-r", "--reproduce", type=str, default=None)
    parser_map.add_argument("-t", "--epoch", type=str, default=None)

    # Waits until the provided epoch is reached before starting the map
    parser_map.add_argument("-w", "--wait", type=str, default=None)

    # Ignore ASNs too high to be compatible with the current asmap encoder
    # Set to 0 to disable
    parser_map.add_argument("-me", "--max_encode", type=int, default=33521664)

    # TODO:
    # Save the final output file in a different location that the default out
    # folder
    # parser_map.add_argument("-o", "--output", action="store_true", default=os.getcwd())

    # Use only a subset of known stable RPKI repositories instead of all sources
    parser_map.add_argument("-s", "--stable-repos", action="store_true", default=False,
                          help="Use only known stable RPKI repositories")

    # TODO:
    # Filter RPKI and IRR data by checking against RIPE RIS and Routeviews data
    # and removing all entries that have not been seen announced to those
    # services.
    # parser_map.add_argument("-f", "--announced_filter", action="store_true", default=False)

    # TODO:
    # Include multiple ASNs that validate correctly for the same prefix.
    # parser_map.add_argument("-m", "--multi_map", action="store_true", default=False)

    parser_merge = subparsers.add_parser("merge")

    parser_merge.add_argument("-b", "--base", default=f"{os.getcwd()}/base_file.txt")
    parser_merge.add_argument("-e", "--extra", default=f"{os.getcwd()}/extra_file.txt")
    parser_merge.add_argument("-o", "--output", default=f"{os.getcwd()}/out_file.txt")

    parser_cov = subparsers.add_parser("cov")

    # IP prefix to ASN map to be used for the coverage report.
    parser_cov.add_argument("map", type=argparse.FileType("r"))

    # List of IPs to be used for the coverage report.
    parser_cov.add_argument("list", type=argparse.FileType("r"))

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s (version {kartograf.__version__})",
    )

    return parser

def is_root():
    # Get current the Effective UID. On Unix systems the root user EUID is 0.
    return os.geteuid() == 0

def main(args=None):
    parser = create_parser()
    args = parser.parse_args(args)

    if is_root():
        sys.exit("Kartograf must be run as a non-root user.")

    if args.command == "map":
        if not args.reproduce and args.epoch:
            parser.error("--reproduce is required when --epoch is set.")
        elif not args.epoch and args.reproduce:
            parser.error("--epoch is required when --reproduce is set.")

        if args.wait and args.reproduce:
            parser.error("--reproduce is not compatible with --wait.")

        if args.wait and (int(args.wait) < time.time()):
            parser.error(f"Cannot wait for a timestamp in the past ({args.wait})")

    if args.command == "map":
        Kartograf.map(args)
    elif args.command == "cov":
        Kartograf.cov(args)
    elif args.command == "merge":
        Kartograf.merge(args)
    else:
        parser.print_help()
        sys.exit("Please provide a command.")
