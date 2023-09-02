import os
import sys


class Context:
    '''Keeps the context information of the current run'''
    def __init__(self, time_now, args):
        self.args = args

        self.reproduce = self.args.reproduce is not None
        if self.reproduce:
            items = os.listdir(self.args.reproduce)
            source_folders = [folder for folder in items if os.path.isdir(os.path.join(self.args.reproduce, folder))]
            # We override the args because we are reproducing and only where we
            # have data we try to use is, the actual args passed don't matter.
            self.args.irr = 'irr' in source_folders
            self.args.routeviews = 'collectors' in source_folders

        # When we reproduce we are not really using the data from that epoch,
        # so better to signal that data is coming from a reproduction run.
        epoch_prefix = "r" if self.reproduce else ""
        self.epoch = epoch_prefix + time_now.strftime("%Y-%m-%d_%H-%M")

        cwd = os.getcwd()
        # Data dir
        if self.reproduce:
            if not self.args.reproduce.endswith('/'):
                self.args.reproduce += '/'
            self.data_dir = self.args.reproduce
        else:
            self.data_dir = f"{cwd}/data/{self.epoch}/"
        self.data_dir_irr = f"{self.data_dir}irr/"
        self.data_dir_rpki = f"{self.data_dir}rpki/"
        self.data_dir_collectors = f"{self.data_dir}collectors/"
        # Out dir
        self.out_dir = f"{cwd}/out/{self.epoch}/"
        self.out_dir_irr = f"{self.out_dir}irr/"
        self.out_dir_rpki = f"{self.out_dir}rpki/"
        self.out_dir_collectors = f"{self.out_dir}collectors/"

        if os.path.exists(self.data_dir) and not self.reproduce:
            print("Not so fast, a folder with that epoch already exists.")
            sys.exit()

        # We skip creating the folders if we are reproducing a run.
        if not self.reproduce:
            os.makedirs(self.data_dir_irr)
            os.makedirs(self.data_dir_rpki)
            os.makedirs(self.data_dir_collectors)
        os.makedirs(self.out_dir_irr)
        os.makedirs(self.out_dir_rpki)
        os.makedirs(self.out_dir_collectors)

        self.final_result_file = f"{self.out_dir}final_result.txt"
