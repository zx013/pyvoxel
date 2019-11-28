# -*- coding: utf-8 -*-
from pyvoxel.log import Log

#类中attr属性改变时触发on_attr事件
class Property(object):
    def __setattr__(self, name, value):
        ovalue = getattr(self, name, None)
        self.__dict__[name] = value

        try:
            self._do_on_func(name, ovalue, value)
        except Exception as ex:
            Log.error(ex)


    def _do_on_func(self, name, ovalue, value):
        #调用on_函数
        if not hasattr(self, 'on_' + name):
            return None
        on_func = getattr(self, 'on_' + name)
        on_func(ovalue, value)
        
        #调用事件


if __name__ == '__main__':
    class TestProperty(Property):
        def on_test(self, old, new):
            print(old, new)

    p = TestProperty()
    p.test = 1
