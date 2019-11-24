# -*- coding: utf-8 -*-
import importlib

from pyvoxel.pattern.singleton import Singleton
from pyvoxel.log import Log

class ManagerBase(Singleton):
    def __init__(self):
        self._instance = {}

    def load_plugin(self, name):
        try:
            if name in self._instance:
                Log.debug('Reload plugin <{name}>'.format(name=name))
                instance = self._instance[name]
                if hasattr(instance, 'reload'):
                    instance.reload()
                    Log.debug('Plugin <{name}> loaded'.format(name=name))
                else:
                    Log.debug('Plugin <{name}> has no reload'.format(name=name))
            else:
                Log.debug('Load plugin <{name}>'.format(name=name))
                plugin = importlib.import_module('plugins.{name}'.format(name=name.lower())) #导入模块
                plugin = getattr(plugin, name.lower())
                instance = getattr(plugin, name) #获取模块中的类
                self._instance[name] = instance
                Log.debug('Plugin <{name}> loaded'.format(name=name))
        except Exception as ex:
            Log.error('Plugin <{name}> load failed - {ex}'.format(name=name, ex=ex))


Manager = ManagerBase()


if __name__ == '__main__':
    Manager.load_plugin('TestPlugin')
    Manager.load_plugin('TestPlugin')
