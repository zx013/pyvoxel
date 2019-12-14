# -*- coding: utf-8 -*-
"""单例模式."""


class Singleton(object):
    """单例模式."""

    def __new__(cls, *args, **kwargs):
        """已创建则使用原先的创建的类."""
        if not hasattr(cls, '_singleton_instance'):
            cls._singleton_instance = object.__new__(cls)
        return cls._singleton_instance


if __name__ == '__main__':
    class SingletonTest1(Singleton):
        """SingletonTest1."""

        pass

    class SingletonTest2(Singleton):
        """SingletonTest2."""

        pass

    class SingletonTest(SingletonTest1, SingletonTest2, Singleton):
        """SingletonTest."""

        pass

    singletontest1 = SingletonTest()
    singletontest2 = SingletonTest()
    assert(id(singletontest1) == id(singletontest2))
