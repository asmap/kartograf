from datetime import datetime
from pathlib import Path
import sys
import time


CACHE_SYNC_DEFAULT = 10 * 60

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

        self.cache_sync_counter = 0
        self.last_loop_start_time = 0


    def _set_epoch_dirs(self):
        '''
        If doing a reproduction run, we will prepend the directory name with a "r"
        to separate it from the original run directory.
        '''
        if self.reproduce and self.epoch:
            # both reproduce and epoch args are set: this is a reproduction run
            repro_epoch = datetime.utcfromtimestamp(int(self.args.epoch))
            self.epoch_dir = "r" + self.epoch
            self.epoch_datetime = repro_epoch
        else:
            self.epoch_dir = self.epoch
            self.epoch_datetime = datetime.utcfromtimestamp(int(self.epoch))

    def sync_sleep(self, duration):
        print(f"(now sleeping {duration} seconds)")
        time.sleep(duration)

    def sync_run(self):
        self.cache_sync_counter += 1
        self.last_loop_start_time = int(time.time())
        print(f"RPKI sync #{self.cache_sync_counter}")

    def rpki_cache_sync(self):
        now = int(time.time())
        if self.cache_sync_counter > 0:
            print(f"...took {now - self.last_loop_start_time} seconds")
        if self.cache_sync_counter == 0:
            # Unconditionally run the first time.
            self.sync_run()
            return True
        if self.cache_sync_counter == 1 and not self.args.wait:
            # We don't do a collaborative run, so we just run once
            return False
        epoch = int(self.epoch)
        if now >= epoch + CACHE_SYNC_DEFAULT:
            return False
        if self.cache_sync_counter == 1:
            if now - self.last_loop_start_time > CACHE_SYNC_DEFAULT * 0.7:
                # We already took over 70% of the warmup time with the first
                # run. Trying a second run now might take too long. Wait until
                # warmup period expires and run one more time then.
                self.sync_sleep(epoch + CACHE_SYNC_DEFAULT - now)
                self.sync_run()
                return True
            # Otherwise run a second time immediately
            self.sync_run()
            return True
        if self.cache_sync_counter == 2:
            # We already ran twice, just do a third run when warm up
            # period expires.
            self.sync_sleep(epoch + CACHE_SYNC_DEFAULT - now)
            self.sync_run()
            return True

        # This should never be reached
        return False
