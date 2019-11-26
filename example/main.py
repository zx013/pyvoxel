# -*- coding: utf-8 -*-
from pyvoxel.log import Log
from pyvoxel.manager import Manager

if __name__ == '__main__':
    def log_test():
        Log.debug('Debug')
    log_test()
    Log.error('Error')
    p = Manager.auto_load()
    print(p)
