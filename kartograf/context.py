from datetime import datetime
import os
import sys
import time


class Context:
    '''Keeps the context information of the current run'''
    def __init__(self, args):
        self.args = args

        # The epoch is used to keep artifacts seperated for each run. This
        # makes cleanup and debugging easier.
        if args.wait:
            utc_time_now = args.wait
        else:
            utc_time_now = time.time()
        # Uncomment this random fixed date for testing purposes
        # time_now = datetime(2008, 10, 31)

        self.reproduce = self.args.reproduce is not None
        if self.reproduce:
            items = os.listdir(self.args.reproduce)
            source_folders = []
            for folder in items:
                full_path = os.path.join(self.args.reproduce, folder)
                if os.path.isdir(full_path):
                    source_folders.append(folder)
            # We override the args because we are reproducing and only where we
            # have data we try to use is, the actual args passed don't matter.
            self.args.irr = 'irr' in source_folders
            self.args.routeviews = 'collectors' in source_folders

            repro_epoch = datetime.utcfromtimestamp(int(self.args.epoch))

            # When we reproduce we are not really using the data from that
            # epoch, so better to signal that data is coming from a
            # reproduction run.
            self.epoch = self.args.epoch
            self.epoch_dir = "r" + self.args.epoch
            self.epoch_datetime = repro_epoch
        else:
            self.epoch = str(int(utc_time_now))
            self.epoch_dir = str(int(utc_time_now))
            self.epoch_datetime = datetime.utcfromtimestamp(int(utc_time_now))

        cwd = os.getcwd()
        # Data dir
        if self.reproduce:
            if not self.args.reproduce.endswith('/'):
                self.args.reproduce += '/'
            self.data_dir = self.args.reproduce
        else:
            self.data_dir = f"{cwd}/data/{self.epoch_dir}/"
        self.data_dir_irr = f"{self.data_dir}irr/"
        self.data_dir_rpki = f"{self.data_dir}rpki/"
        self.data_dir_collectors = f"{self.data_dir}collectors/"
        # Out dir
        self.out_dir = f"{cwd}/out/{self.epoch_dir}/"
        self.out_dir_irr = f"{self.out_dir}irr/"
        self.out_dir_rpki = f"{self.out_dir}rpki/"
        self.out_dir_collectors = f"{self.out_dir}collectors/"

        if os.path.exists(self.data_dir) and not self.reproduce:
            print("Not so fast, a folder with that epoch already exists.")
            sys.exit()

        # We skip creating the folders if we are reproducing a run.
        if not self.reproduce:
            os.makedirs(self.data_dir_rpki)
            if self.args.irr:
                os.makedirs(self.data_dir_irr)
            if self.args.routeviews:
                os.makedirs(self.data_dir_collectors)
        os.makedirs(self.out_dir_rpki)
        if self.args.irr:
            os.makedirs(self.out_dir_irr)
        if self.args.routeviews:
            os.makedirs(self.out_dir_collectors)

        self.final_result_file = f"{self.out_dir}final_result.txt"
