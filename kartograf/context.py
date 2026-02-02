from datetime import datetime, UTC
from pathlib import Path
import sys
import time


class Context:
    '''Keeps the context information of the current run'''
    def __init__(self, args):
        self.args = args

        # The epoch is used to keep artifacts separated for each run. This
        # makes cleanup and debugging easier.
        if self.args.wait:
            self.epoch = self.args.wait
        elif self.args.epoch:
            self.epoch = self.args.epoch
        else:
            self.epoch = str(int(time.time()))

        self.reproduce = self.args.reproduce is not None
        if self.reproduce:
            data_path = Path(self.args.reproduce)
            # in the data path, get the names of directories in the given path
            source_folders = [ p.name for p in data_path.glob('*') if Path.is_dir(p) ]
            # We override the args because we are reproducing and only where we
            # have data we try to use is, the actual args passed don't matter.
            self.args.irr = 'irr' in source_folders
            self.args.routeviews = 'collectors' in source_folders

        self._set_epoch_dirs()

        cwd = Path.cwd()
        # Data dir
        if self.reproduce:
            if not self.args.reproduce.endswith('/'):
                self.args.reproduce += '/'
            abs_path = Path(self.args.reproduce).absolute()
            self.data_dir = str(abs_path)
        else:
            abs_path = (Path("data") / self.epoch_dir).absolute()
            self.data_dir = str(abs_path)

        if Path(self.data_dir).exists() and not self.reproduce:
            print("Not so fast, a folder with that epoch already exists.")
            sys.exit()

        self.data_dir_irr = str(Path(self.data_dir) / "irr")
        self.data_dir_rpki_cache = str(Path(self.data_dir) / "rpki" / "cache")
        self.data_dir_rpki_tals = str(Path(self.data_dir) / "rpki" / "tals")
        self.data_dir_collectors = str(Path(self.data_dir) / "collectors")
        # Out dir
        self.out_dir = str(cwd / "out" / self.epoch_dir)
        self.out_dir_irr = str(Path(self.out_dir) / "irr")
        self.out_dir_rpki = str(Path(self.out_dir) / "rpki")
        self.out_dir_collectors = str(Path(self.out_dir) / "collectors")

        self.stable_repos = False
        if self.args.stable_repos:
            self.stable_repos = True

        self.cleanup_out_files = []

        # We skip creating the folders if we are reproducing a run.
        if not self.reproduce:
            Path(self.data_dir_rpki_cache).mkdir(parents=True)
            Path(self.data_dir_rpki_tals).mkdir(parents=True)
            if self.args.irr:
                Path(self.data_dir_irr).mkdir(parents=True)
            if self.args.routeviews:
                Path(self.data_dir_collectors).mkdir(parents=True)
        Path(self.out_dir_rpki).mkdir(parents=True)
        if self.args.irr:
            Path(self.out_dir_irr).mkdir(parents=True)
        if self.args.routeviews:
            Path(self.out_dir_collectors).mkdir(parents=True)

        self.final_result_file = str(Path(self.out_dir) / "final_result.txt")

        self.max_encode = self.args.max_encode

        if self.args.debug:
            self.debug_log = str(Path(self.out_dir) / "debug.log")
        else:
            self.debug_log = ""


    def _set_epoch_dirs(self):
        '''
        If doing a reproduction run, we will prepend the directory name with a "r"
        to separate it from the original run directory.
        '''
        if self.reproduce and self.epoch:
            # both reproduce and epoch args are set: this is a reproduction run
            repro_epoch = datetime.fromtimestamp(int(self.args.epoch), UTC)
            self.epoch_dir = "r" + self.epoch
            self.epoch_datetime = repro_epoch
        else:
            self.epoch_dir = self.epoch
            self.epoch_datetime = datetime.fromtimestamp(int(self.epoch), UTC)
