from datetime import datetime
import os
import sys
import time


class Context:
    '''Keeps the context information of the current run'''
    def __init__(self, args):
        self.args = args

        # The epoch is used to keep artifacts separated for each run. This
        # makes cleanup and debugging easier.
        if args.wait:
            self.epoch = args.wait
        elif self.args.epoch:
            self.epoch = self.args.epoch
        else:
            self.epoch = str(int(time.time()))

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

        self._set_epoch_dirs()

        cwd = os.getcwd()
        # Data dir
        if self.reproduce:
            if not self.args.reproduce.endswith('/'):
                self.args.reproduce += '/'
            self.data_dir = self.args.reproduce
        else:
            self.data_dir = os.path.join(cwd, "data", self.epoch_dir)

        if os.path.exists(self.data_dir) and not self.reproduce:
            print("Not so fast, a folder with that epoch already exists.")
            sys.exit()

        self.data_dir_irr = os.path.join(self.data_dir, "irr")
        self.data_dir_rpki_cache = os.path.join(self.data_dir, "rpki/cache")
        self.data_dir_rpki_tals = os.path.join(self.data_dir, "rpki/tals")
        self.data_dir_collectors = os.path.join(self.data_dir, "collectors")
        # Out dir
        self.out_dir = os.path.join(cwd,"out", self.epoch_dir)
        self.out_dir_irr = os.path.join(self.out_dir, "irr")
        self.out_dir_rpki = os.path.join(self.out_dir, "rpki")
        self.out_dir_collectors = os.path.join(self.out_dir, "collectors")

        # We skip creating the folders if we are reproducing a run.
        if not self.reproduce:
            os.makedirs(self.data_dir_rpki_cache)
            os.makedirs(self.data_dir_rpki_tals)
            if self.args.irr:
                os.makedirs(self.data_dir_irr)
            if self.args.routeviews:
                os.makedirs(self.data_dir_collectors)
        os.makedirs(self.out_dir_rpki)
        if self.args.irr:
            os.makedirs(self.out_dir_irr)
        if self.args.routeviews:
            os.makedirs(self.out_dir_collectors)

        self.final_result_file = os.path.join(self.out_dir, "final_result.txt")

        self.max_encode = self.args.max_encode

        if self.args.debug:
            self.debug_log = os.path.join(self.out_dir, "debug.log")
        else:
            self.debug_log = ""


    def _set_epoch_dirs(self):
        '''
        If doing a reproduction run, we will prepend the directory name with a "r"
        to separate it from the original run directory.
        '''
        if self.reproduce and self.args.epoch:
            # both reproduce and epoch args are set: this is a reproduction run
            repro_epoch = datetime.utcfromtimestamp(int(self.args.epoch))
            self.epoch_dir = "r" + self.epoch
            self.epoch_datetime = repro_epoch
        else:
            self.epoch_dir = self.epoch
            self.epoch_datetime = datetime.utcfromtimestamp(int(self.epoch))
