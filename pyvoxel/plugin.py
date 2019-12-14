# -*- coding: utf-8 -*-
"""插件的基类."""


class Plugin(object):
    """定义插件的基础属性和函数."""

    def reload(self):
        """重新加载插件."""
        pass

    def start(self):
        """启动插件."""
        pass

    def stop(self):
        """停止插件."""
        pass
