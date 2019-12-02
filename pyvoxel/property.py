# -*- coding: utf-8 -*-
from pyvoxel.log import Log
import traceback


class Node(object):
    def __init__(self):
        self.__obj = {}
        self.__trans = None
        self.parent = None
        self.children = []

    '''
    def __getattribute__(self, name):
        attr = object.__getattribute__(self, name)
        if name not in ('parent', 'children'):
            if name.startswith('__'): #内部调用，__dict__/__class__等
                return attr
            if name.startswith('_Node'): #python3中自定义__开头的数据
                return attr
            if not self.__trans: #正常的变量访问，只有建立关联时设置__trans
                return attr

            if not isinstance(self.__trans.__trans, str):
                if name not in self.__obj:
                    self.__obj[name] = {}
                self.__obj[name][self.__trans] = []
                self.__trans = 'test'
            else:
                self.__trans.__obj[self.__trans.__trans][self].append(name)
                self.__trans.__trans = None
                self.__trans = None
            return attr
        if traceback.extract_stack()[-2][2] == 'add_node': #内部调用parent/children的接口
            return attr

        #建立类之间的关联，通过parent/children的调用逐步获取
        if self.__trans is None:
            self.__trans = attr
            attr.__trans = self
        else:
            self.__trans.__trans = attr
            attr.__trans = self.__trans
            self.__trans = None
        return attr
    '''

    def add_node(self, node):
        self.children.append(node)
        if node.parent:
            Log.warning('{node} already has parent'.format(node=node))
        node.parent = self


#类中attr属性改变时触发on_attr事件
class Property(Node):
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


def analyse(cls, base):
    base_cls = cls
    node_list = base.split('.')
    for node in node_list[:-1]:
        if len(node) == 0:
            return False
        if node[0] == 'p':
            base_cls = base_cls.parent
        elif node[0] == 'c':
            pass
        else:
            return False
    base_name = node_list[-1]
    if not hasattr(base_cls, base_name):
        return False
    return base_cls, base_name 

#将cls类中的name变量绑定到base
#base_cls中的base_name字段改变时，同步修改cls的name字段
def bind(cls, name, base_dict, expr):
    for key, base in base_dict.items():
        result = analyse(cls, base)
        if not result:
            print('Class has no attr', base)
            return False
        base_cls, base_name = result
        base_dict[key] = result

    local = {}
    for key, base in base_dict.items():
        base_cls, base_name = base
        local[key] = getattr(base_cls, base_name)

    value = eval(expr, None, local)
    
    print(value)


if __name__ == '__main__':
    t1 = Node()
    t2 = Node()
    t3 = Node()
    
    t1.add_node(t2)
    t2.add_node(t3)
    
    t1.testa = 1
    t2.testb = 2
    
    bind(t3, 'testS', {'a': 'p.p.testa', 'b': 'p.testb'}, 'a + b')
