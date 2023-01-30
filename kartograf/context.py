import os
import sys


class Context:
    '''Keeps the context information of the current run'''
    def __init__(self, time_now):
        self.epoch = time_now.strftime("%Y-%m-%d_%H-%M")

        cwd = os.getcwd()
        self.data_dir = f"{cwd}/data/{self.epoch}/"
        self.data_dir_irr = f"{self.data_dir}irr/"
        self.data_dir_rpki = f"{self.data_dir}rpki/"
        self.data_dir_collectors = f"{self.data_dir}collectors/"
        self.out_dir = f"{cwd}/out/{self.epoch}/"
        self.out_dir_irr = f"{self.out_dir}irr/"
        self.out_dir_rpki = f"{self.out_dir}rpki/"
        self.out_dir_collectors = f"{self.out_dir}collectors/"

        if os.path.exists(self.data_dir) or os.path.exists(self.data_dir):
            print("Not so fast, a folder with that epoch already exists.")
            sys.exit()

        os.makedirs(self.data_dir_irr)
        os.makedirs(self.data_dir_rpki)
        os.makedirs(self.data_dir_collectors)
        os.makedirs(self.out_dir_irr)
        os.makedirs(self.out_dir_rpki)
        os.makedirs(self.out_dir_collectors)
