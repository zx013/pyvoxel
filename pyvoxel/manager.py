# -*- coding: utf-8 -*-
import importlib
import os

from pyvoxel.pattern.singleton import Singleton
from pyvoxel.log import Log


class ManagerBase(Singleton):
    def __init__(self):
        self._instance = {}
        self._plugin_dir = 'plugins' #用户的插件目录

    def auto_load(self):
        '''
        自动加载所有插件，先加载默认插件，再加载用户插件，有名称相同的则覆盖
        '''
        #获取默认插件
        from pyvoxel import plugins
        base_plugin_dir = os.path.dirname(plugins.__file__)
        base_plugin_list = self.scan_plugin(base_plugin_dir)
        
        #用户插件
        plugin_list = self.scan_plugin(self._plugin_dir)

        #被覆盖的插件不重复加载
        for base_plugin_name in base_plugin_list - plugin_list:
            self.load_plugin(base_plugin_name, isbase=True)

        for plugin_name in plugin_list:
            if not self.load_plugin(plugin_name, isbase=False): #加载失败则加载默认的
                if plugin_name in base_plugin_list:
                    self.load_plugin(plugin_name, isbase=True)

    def scan_plugin(self, plugin_dir):
        '''
        扫描目录下的所有插件
        '''
        if not os.path.isdir(plugin_dir):
            Log.warning('{plugin_dir} not exist'.format(plugin_dir=plugin_dir))
            return set()
        return {name for name in os.listdir(plugin_dir) if not name.startswith('__')}

    def load_plugin(self, name, isbase=False):
        '''
        加载插件，插件文件名和目录需要小写，加载插件时名称忽略大小写，最好使用插件主类的名称
        '''
        name_lower = name.lower()
        if not os.path.isdir(os.path.join(self._plugin_dir, name_lower)):
            Log.warning('Plugin <{name}> not exist'.format(name=name))
            return False

        try:
            Log.debug('Load plugin <{name}>'.format(name=name))
            
            if isbase:
                plugin = importlib.import_module('pyvoxel.{plugin_dir}.{name}.{name}'.format(plugin_dir=self._plugin_dir, name=name_lower)) #导入默认模块
            else:
                plugin = importlib.import_module('{plugin_dir}.{name}.{name}'.format(plugin_dir=self._plugin_dir, name=name_lower)) #导入模块
            for class_name in dir(plugin): #传入的可能是小写字母，与对应类名称不同
                if class_name.startswith('__') and class_name.endswith('__'):
                    continue
                if class_name.lower() == name_lower:
                    break
            else:
                class_name = name
            instance = getattr(plugin, class_name) #获取模块中的类
            if class_name in self._instance:
                del self._instance[class_name]
            self._instance[class_name] = instance
            Log.debug('Plugin <{name} - {path}> loaded'.format(name=name, path=instance.__module__.split('.', 1)[0]))
            return True
        except Exception as ex:
            Log.error('Plugin <{name}> load failed - {ex}'.format(name=name, ex=ex))
            return False

    def get_plugins(self):
        return set(self._instance.keys())

    #实例化插件
    def __call__(self, name):
        if name not in self._instance:
            Log.warning('Plugin <{name}> not exist'.format(name=name))
            return None
        instance = self._instance[name]
        return instance()


Manager = ManagerBase()


if __name__ == '__main__':
    Manager.auto_load()
    Manager.load_plugin('TestPlugin_no')
    
    print(Manager('TestPlugin01').test())
