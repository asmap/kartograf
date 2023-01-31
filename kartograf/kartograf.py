import datetime
import shutil
import time

from kartograf.context import Context
from kartograf.coverage import coverage
from kartograf.collectors.routeviews import fetch_routeviews_pfx2as
from kartograf.irr.fetch import fetch_irr
from kartograf.irr.parse import parse_irr
from kartograf.merge import merge_irr, merge_pfx2as, general_merge
from kartograf.rpki.fetch import fetch_rpki_db
from kartograf.rpki.parse import parse_rpki
from kartograf.util import print_section_header


class Kartograf:
    @staticmethod
    def map(args):
        print_section_header("Start Kartograf")
        # This is used to measure the overall runtime of the program
        start_time = time.time()

        # The epoch is used to keep artifacts seperated for each run. This
        # makes cleanup and debugging easier.
        epoch = datetime.datetime.now()
        # epoch = datetime.datetime(2008, 10, 31)  # Random fixed date for testing
        context = Context(epoch)
        print(f"The epoch for this run is: {context.epoch}")

        print_section_header("RPKI")
        fetch_rpki_db(context)
        parse_rpki(context)

        if args.irr:
            print_section_header("IRR")
            fetch_irr(context)
            parse_irr(context)

            print_section_header("Merging RPKI and IRR data")
            merge_irr(context)

        if args.routeviews:
            print_section_header("Routeviews pfx2as")
            fetch_routeviews_pfx2as(context)

            print_section_header("Merging Routeviews and base data")
            merge_pfx2as(context)

        print_section_header("Finishing Kartograf")

        if args.cleanup:
            shutil.rmtree(context.data_dir)
            print("Cache directory cleaned")

        end_time = time.time()
        total_time = end_time - start_time
        print("Total runtime:", str(datetime.timedelta(seconds=total_time)))

    @staticmethod
    def cov(args):
        coverage(args.map, args.list)


    @staticmethod
    def merge(args):
        general_merge(args.base, args.extra, None, args.output)
