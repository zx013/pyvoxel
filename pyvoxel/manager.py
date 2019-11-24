# -*- coding: utf-8 -*-
import importlib
import os

from pyvoxel.pattern.singleton import Singleton
from pyvoxel.log import Log

class ManagerBase(Singleton):
    def __init__(self):
        self._instance = {}
        self._plugin_dir = 'plugins'

    def auto_load(self):
        plugin_list = self.scan_plugin()
        for plugin in plugin_list:
            pass

    def scan_plugin(self):
        if not os.path.isdir(self._plugin_dir):
            Log.warning('{plugin_dir} not exist'.format(plugin_dir=self._plugin_dir))
            return []
        return [name for name in os.listdir(self._plugin_dir) if not name.startswith('__')]

    def load_plugin(self, name):
        '''
        插件文件名需要小写，加载插件时忽略大小写
        '''
        name_lower = name.lower()
        if not os.path.isdir(os.path.join(self._plugin_dir, name_lower)):
            Log.warning('Plugin <{name}> not exist'.format(name=name))
            return False

        try:
            if name_lower in self._instance:
                Log.debug('Reload plugin <{name}>'.format(name=name))
                instance = self._instance[name_lower]
                if hasattr(instance, 'reload'):
                    instance.reload()
                    Log.debug('Plugin <{name}> loaded'.format(name=name))
                    return True
                else:
                    Log.debug('Plugin <{name}> has no reload'.format(name=name))
                    return False
            else:
                Log.debug('Load plugin <{name}>'.format(name=name))
                
                plugin = importlib.import_module('{plugin_dir}.{name}'.format(plugin_dir=self._plugin_dir, name=name_lower)) #导入模块
                plugin = getattr(plugin, name_lower)
                for class_name in dir(plugin): #传入的可能是小写字母
                    if class_name.startswith('__') and class_name.endswith('__'):
                        continue
                    if class_name.lower() == name_lower:
                        instance = getattr(plugin, class_name)
                        break
                else:
                    instance = getattr(plugin, name) #获取模块中的类
                self._instance[name_lower] = instance
                Log.debug('Plugin <{name}> loaded'.format(name=name))
                return True
        except Exception as ex:
            Log.error('Plugin <{name}> load failed - {ex}'.format(name=name, ex=ex))

    #实例化插件
    def instant(self, name):
        name_lower = name.lower()
        if name_lower not in self._instance:
            return None
        instance = self._instance[name_lower]
        return instance()


Manager = ManagerBase()


if __name__ == '__main__':
    plugins = Manager.scan_plugin()
    Manager.load_plugin('TestPlugin')
    Manager.load_plugin('TestPlugin')
    Manager.load_plugin('testplugin')
    Manager.load_plugin('TestPlugin_no')
    
    print(Manager.instant('TestPlugin').test())
