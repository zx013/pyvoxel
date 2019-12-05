# -*- coding: utf-8 -*-
from pyvoxel.log import Log


#类中attr属性改变时触发on_attr事件，同时同步改变关联的值
class Node(object):
    def __new__(cls): #不用在子类中调用super初始化
        cls._trigger = {}
        cls._reflex = {}
        cls.parent = None
        cls.children = []
        print('node new')
        return super().__new__(cls)

    def __setattr__(self, name, value):
        ovalue = self.__dict__.get(name, None)
        self.__dict__[name] = value

        try:
            self._on_func(name, ovalue, value)
        except Exception as ex:
            Log.error(ex)

    #调用on_函数
    def _on_func(self, name, ovalue, value):
        on_name = 'on_' + name
        if on_name in self.__dict__:
            on_func = self.__dict__[on_name]
            on_func(ovalue, value)

        if name in self._trigger:
            for node, nname in self._trigger[name]:
                node._update_value(nname, (self, name), value)

    #更新关联类的值
    def _update_value(self, name, base, basev):
        try:
            expr, pattern, local = self._reflex[name]
            local[pattern[base]] = basev

            value = eval(expr, None, local)
            setattr(self, name, value)
        except Exception as ex:
            Log.error(ex)

    def add_node(self, node):
        self.children.append(node)
        if node.parent:
            Log.warning('{node} already has parent'.format(node=node))
        node.parent = self


if __name__ == '__main__':
    t1 = Node()
    t2 = Node()
    t3 = Node()
    t4 = Node()

    t1.add_node(t2)
    t2.add_node(t3)
    t3.add_node(t4)

    t1.testa = 1
    t1.testb = 2
    t3.testc = 3
    t4.test = 10

    t2.bind('testd', 'p.testa + p.testb * p.testb - c0.testc')
    t4.bind('teste', 'p.p.testd + p.p.p.testa + self.test')
    print(t2.testd, t4.teste)

    t1.testa = 4
    print(t2.testd, t4.teste)

    t1.testb = 5
    print(t2.testd, t4.teste)

    t3.testc = 6
    print(t2.testd, t4.teste)
