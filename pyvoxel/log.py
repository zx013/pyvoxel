# -*- coding: utf-8 -*-
import logging
from singleton import Singleton

class LogBase(logging.Logger, Singleton):
    def __init__(self, name, level=logging.DEBUG):
        self.name = name
        self.level = level
        self.formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(module)s -> %(funcName)s (%(lineno)d) : %(message)s', '%Y-%m-%d %H:%M:%S')

        super(LogBase, self).__init__(name=self.name, level=self.level)
        self.__setSteamHandler__()

    def __setSteamHandler__(self):
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(self.formatter)
        self.addHandler(stream_handler)

Log = LogBase(name='voxel', level=logging.DEBUG)


if __name__ == '__main__':
    def log_test():
        Log.debug('Debug')
    log_test()
    Log.error('Error')
