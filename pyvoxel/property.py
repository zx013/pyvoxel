# -*- coding: utf-8 -*-
from pyvoxel.log import Log
import traceback

global a
#类中attr属性改变时触发on_attr事件
class Property(object):
    def __getattribute__(self, name):
        if name in ('__dict__', '__on_func__'):
            return object.__getattribute__(self, name)
        global a
        trace = traceback.extract_stack()[-2]
        a = trace
        print('---', name, dir(trace), trace[2])
        return object.__getattribute__(self, name)

    def __setattr__(self, name, value):
        ovalue = self.__dict__.get(name, None)
        self.__dict__[name] = value

        try:
            self.__on_func__(name, ovalue, value)
        except Exception as ex:
            Log.error(ex)

    def __on_func__(self, name, ovalue, value):
        name = 'on_' + name
        #调用on_函数
        if name not in self.__dict__:
            return None

        on_func = self.__dict__[name]
        on_func(ovalue, value)

        #调用事件


if __name__ == '__main__':
    class TestProperty(Property):
        def on_test(self, old, new):
            print(old, new)

    p = TestProperty()
    p.test = 1

    print(p.test)

    class T(object):
        def __init__(self, p):
            self.p = p

        @property
        def testT(self):
            return self.p.test
        
        def testP(self):
            return self.p.test

    t = T(p)
    print(t.testT)
    print(t.testP())
