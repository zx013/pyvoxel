# -*- coding: utf-8 -*-

#单例模式
class Singleton(object):
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            cls._instance = object.__new__(cls)
        return cls._instance

if __name__ == '__main__':
    class SingletonTest1(Singleton):
        pass

    class SingletonTest2(Singleton):
        pass
    
    class SingletonTest(SingletonTest1, SingletonTest2, Singleton):
        pass

    singletontest1 = SingletonTest()
    singletontest2 = SingletonTest()
    assert(id(singletontest1) == id(singletontest2))
