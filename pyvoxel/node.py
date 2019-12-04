# -*- coding: utf-8 -*-
import re
from pyvoxel.log import Log


#类中attr属性改变时触发on_attr事件，同时同步改变关联的值
class Node(object):
    def __init__(self):
        self._trigger = {}
        self._reflex = {}
        self.parent = None
        self.children = []

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

    def _walk(self, deep, isroot=True):
        if isroot:
            yield self, deep
        for child in self.children:
            for node, node_deep in child._walk(deep + 1):
                yield node, node_deep
    
    def walk(self, isroot=True):
        for node, deep in self._walk(0, isroot):
            yield node, deep

    def show(self):
        for node, deep in self.walk(isroot=False):
            spacesep = '    ' * (deep - 1)
            print(spacesep + '<' + node.__class__.__name__ + '>:')
            spacesep += '    '
            for key in dir(node):
                if key.startswith('_'):
                    continue
                if hasattr(getattr(node, key), '__call__'):
                    continue
                if key in ('parent', 'children', 'show', 'add_node', 'bind'):
                    continue
                print(spacesep + key + ': ' + str(getattr(node, key)))

    def add_node(self, node):
        self.children.append(node)
        if node.parent:
            Log.warning('{node} already has parent'.format(node=node))
        node.parent = self

    #新建类中name变量，并将name变量和expr表达式中其他类变量绑定，当其他类变量变化时，同步修改该变量
    #使用缩写语法，p代表parent，c1代表children[1]，缩写语法默认添加self
    #使用bind绑定时，所有的变量必须可访问
    def bind(self, name, expr, local={}):
        if '__import__' in expr: #literal_eval不能设置locals，因此需要对expr进行判断
            return False, 'Expr can not use __import__.'
        
        local['self'] = self
        
        #self可省略
        ptn = '(?:^|[^a-z0-9_.])(?=(?!({}))[a-z_]+[a-z0-9_]*)'.format('|'.join(local.keys()))
        bypass = 'self.'
        offset = 0
        for i, p in enumerate(re.finditer(ptn, expr, flags=re.I)):
            index = p.span()[1] + offset
            expr = expr[:index] + bypass + expr[index:]
            offset += len(bypass)

        #parent缩写为p，children[x]缩写为cx
        while True:
            size = len(expr)
            expr = re.sub('[.]p[.]', '.parent.', expr, flags=re.I)
            expr = re.sub('[.]c([0-9]+)[.]', lambda m: '.children[{}].'.format(m.group(1)), expr, flags=re.I)
            if len(expr) == size:
                break

        ptn = '(?:{}).((?:parent|children\[[0-9]+\]).)*[a-z_]+[a-z0-9_]*'.format('|'.join(local.keys()))
        pattern = {}
        pset = set()
        #查找所有变量
        for i, p in enumerate(re.finditer(ptn, expr, flags=re.I)):
            iname = '_x{i}'.format(i=i)
            pname = p.group()
            if pname in pset: #防止重复定义
                continue

            plist = pname.split('.')
            try: #定位变量所在的类
                base_cls = local[plist[0]]
                for node in plist[1:-1]:
                    if node.startswith('parent'):
                        base_cls = base_cls.parent
                    elif node.startswith('children'):
                        base_cls = base_cls.children[int(node.split('[')[1].split(']')[0])]
            except Exception:
                return False, 'Analyse attr error'
            base_name = plist[-1]

            pset.add(pname)
            if (base_cls, base_name) in pattern: #相同的变量使用相同的名称
                expr = expr.replace(pname, pattern[(base_cls, base_name)])
            else:
                pattern[(base_cls, base_name)] = iname
                expr = expr.replace(pname, iname)

        try:
            local = {} #使语句中的self生效
            for base, key in pattern.items():
                base_cls, base_name = base
                local[key] = getattr(base_cls, base_name)
            value = eval(expr, None, local)
            setattr(self, name, value)
        except Exception:
            return False, 'Run expr error'

        #能够正常获取参数值时，写入配置变量
        for base_cls, base_name in pattern.keys():
            base_cls._trigger.setdefault(base_name, set())
            base_cls._trigger[base_name].add((self, name))
        self._reflex[name] = (expr, pattern, local)
        return True, 'Success'


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
