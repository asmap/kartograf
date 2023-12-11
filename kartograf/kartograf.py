import datetime
from datetime import timezone
import shutil
import time

from kartograf.context import Context
from kartograf.coverage import coverage
from kartograf.collectors.routeviews import extract_routeviews_pfx2as, fetch_routeviews_pfx2as
from kartograf.collectors.parse import parse_routeviews_pfx2as
from kartograf.irr.fetch import extract_irr, fetch_irr
from kartograf.irr.parse import parse_irr
from kartograf.merge import merge_irr, merge_pfx2as, general_merge
from kartograf.rpki.fetch import fetch_rpki_db, validate_rpki_db
from kartograf.rpki.parse import parse_rpki
from kartograf.sort import sort_result_by_pfx
from kartograf.util import (
    calculate_sha256,
    check_compatibility,
    print_section_header,
    wait_for_launch
)


class Kartograf:
    @staticmethod
    def map(args):
        print_section_header("Start Kartograf")
        check_compatibility()

        if args.wait:
            wait_epoch = datetime.datetime.utcfromtimestamp(int(args.wait))
            utc_wait_epoch = wait_epoch.replace(tzinfo=timezone.utc)
            local_wait_epoch = utc_wait_epoch.astimezone()
            print(f"Coordinated launch mode: Waiting until {args.wait} "
                  f"({local_wait_epoch.strftime('%Y-%m-%d %H:%M:%S %Z')}) to "
                  "launch mapping process.")
            wait_for_launch(args.wait)

        # This is used to measure the overall runtime of the program
        start_time = time.time()

        context = Context(args)
        utc_datetime = context.epoch_datetime.replace(tzinfo=timezone.utc)
        local_datetime = utc_datetime.astimezone()
        print(f"The epoch for this run is: {context.epoch} "
              f"({utc_datetime.strftime('%Y-%m-%d %H:%M:%S %Z')}, "
              f"local: {local_datetime.strftime('%Y-%m-%d %H:%M:%S %Z')})")

        if context.reproduce:
            repro_path = context.args.reproduce
            print(f"This is a reproduction run based on the data in "
                  f"{repro_path}")

        # Fetch everthing that we need to fetch first
        if not context.reproduce:
            print_section_header("Fetching RPKI")
            fetch_rpki_db(context)

            if context.args.irr:
                print_section_header("Fetching IRR")
                fetch_irr(context)

            if context.args.routeviews:
                print_section_header("Fetching Routeviews pfx2as")
                fetch_routeviews_pfx2as(context)

        print_section_header("Validating RPKI")
        validate_rpki_db(context)

        print_section_header("Parsing RPKI")
        parse_rpki(context)

        if context.args.irr:
            print_section_header("Parsing IRR")
            extract_irr(context)
            parse_irr(context)

            print_section_header("Merging RPKI and IRR data")
            merge_irr(context)

        if context.args.routeviews:
            print_section_header("Parsing Routeviews pfx2as")
            extract_routeviews_pfx2as(context)
            parse_routeviews_pfx2as(context)

            print_section_header("Merging Routeviews and base data")
            merge_pfx2as(context)

        print_section_header("Sorting results")
        sort_result_by_pfx(context)

        print_section_header("Finishing Kartograf")

        if context.args.cleanup:
            shutil.rmtree(context.data_dir)
            print("Cache directory cleaned")

        result_hash = calculate_sha256(context.final_result_file)
        print(f"The SHA-256 hash of the result file is: {result_hash}")

        end_time = time.time()
        total_time = end_time - start_time
        print("Total runtime:", str(datetime.timedelta(seconds=total_time)))

    @staticmethod
    def cov(args):
        coverage(args.map, args.list)

    @staticmethod
    def merge(args):
        general_merge(args.base, args.extra, None, args.output)
