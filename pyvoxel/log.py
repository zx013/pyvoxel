# -*- coding: utf-8 -*-
"""日志."""
import logging
import traceback
from pyvoxel.pattern.singleton import Singleton


class LogBase(logging.Logger, Singleton):
    """自定义日志格式."""

    def __init__(self, name, level=logging.DEBUG):
        """初始化日志格式."""
        self.name = name
        self.level = level
        self.formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(module)s -> %(funcName)s (%(lineno)d) : %(message)s', '%Y-%m-%d %H:%M:%S')

        super(LogBase, self).__init__(name=self.name, level=self.level)
        self.__setSteamHandler__()

    def __setSteamHandler__(self):
        """日志打印到控制台."""
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(self.formatter)
        self.addHandler(stream_handler)

    def exception(self):
        """出现异常时将异常信息记录到日志."""
        self.critical('\n' + traceback.format_exc())


Log = LogBase(name='voxel', level=logging.DEBUG)


if __name__ == '__main__':
    def log_test():
        """log_test."""
        Log.debug('Debug')
    log_test()
    Log.error('Error')
