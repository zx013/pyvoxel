# -*- coding: utf-8 -*-
"""测试插件01."""
from pyvoxel.plugin import Plugin


class TestPlugin01(Plugin):
    """测试插件01."""

    def test(self):
        """测试函数."""
        return 'test01 base'
