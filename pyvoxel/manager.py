# -*- coding: utf-8 -*-
"""插件管理模块."""
import importlib
import os

from pyvoxel.pattern.singleton import Singleton
from pyvoxel.log import Log


class ManagerBase(Singleton):
    """插件管理."""

    _instance = {}
    _plugin_dir = 'plugins'  # 用户的插件目录

    _base_plugins = set()  # 默认插件列表
    _plugins = set()  # 自定义插件列表

    def __init__(self):
        """初始化时扫描插件目录."""
        self.auto_scan()

    @property
    def plugins(self):
        """所有的插件."""
        return self.plugins_loaded | self.plugins_unload

    @property
    def plugins_loaded(self):
        """已加载的插件."""
        return set(self._instance)

    @property
    def plugins_unload(self):
        """未加载的插件."""
        return self._base_plugins | self._plugins

    def auto_scan(self):
        """自动扫描目录."""
        plugins_loaded = {plugin.lower() for plugin in self.plugins_loaded}

        # 获取默认插件
        from pyvoxel import plugins
        base_plugin_dir = os.path.dirname(plugins.__file__)
        base_plugins = self.scan_plugin(base_plugin_dir)
        for plugin in base_plugins:
            if plugin.lower() in plugins_loaded:
                continue
            self._base_plugins.add(plugin)

        # 用户插件
        plugins = self.scan_plugin(self._plugin_dir)
        for plugin in plugins:
            if plugin.lower() in plugins_loaded:
                continue
            self._plugins.add(plugin)

    def auto_load(self):
        """自动加载所有插件，先加载默认插件，再加载用户插件，有名称相同的则覆盖."""
        # 被覆盖的插件不重复加载
        for name in self.plugins_unload:
            self.load_plugin(name)

    def scan_plugin(self, plugin_dir):
        """扫描目录下的所有插件."""
        if not os.path.isdir(plugin_dir):
            Log.warning('{plugin_dir} not exist'.format(plugin_dir=plugin_dir))
            return set()
        return {name for name in os.listdir(plugin_dir) if not name.startswith('__')}

    def _load_plugin(self, name, isbase=False):
        """加载插件，插件文件名和目录需要小写，加载插件时名称忽略大小写，最好使用插件主类的名称."""
        name_lower = name.lower()
        if not os.path.isdir(os.path.join(self._plugin_dir, name_lower)):
            Log.warning('Plugin <{name}> not exist'.format(name=name))
            return False

        try:
            Log.debug('Load plugin <{name}>'.format(name=name))

            if isbase:
                plugin = importlib.import_module('pyvoxel.{plugin_dir}.{name}.{name}'.format(plugin_dir=self._plugin_dir, name=name_lower))  # 导入默认模块
            else:
                plugin = importlib.import_module('{plugin_dir}.{name}.{name}'.format(plugin_dir=self._plugin_dir, name=name_lower))  # 导入模块
            for class_name in dir(plugin):  # 传入的可能是小写字母，与对应类名称不同
                if class_name.startswith('__') and class_name.endswith('__'):
                    continue
                if class_name.lower() == name_lower:
                    break
            else:
                class_name = name
            instance = getattr(plugin, class_name)  # 获取模块中的类
            if class_name in self._instance:
                del self._instance[class_name]

            if name in self._base_plugins:  # 有重复插件需要同时删除
                self._base_plugins.remove(name)
            if name in self._plugins:
                self._plugins.remove(name)
            self._instance[class_name] = instance
            Log.debug('Plugin <{name} - {path}> loaded'.format(name=name, path=instance.__module__.split('.', 1)[0]))
            return True
        except Exception as ex:
            Log.error('Plugin <{name}> load failed - {ex}'.format(name=name, ex=ex))
            return False

    def load_plugin(self, name):
        """加载插件."""
        if name in self._plugins:
            if self._load_plugin(name, isbase=False):  # 加载失败则加载默认的
                return True
        if name in self._base_plugins:
            return self._load_plugin(name, isbase=True)
        return False

    def __call__(self, name):
        """实例化插件."""
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
