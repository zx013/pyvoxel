# -*- coding: utf-8 -*-
from manager import Manager
from log import Log


class Node(object):
    def __init__(self, name, space):
        self.name = name
        self.space = space
        self.attr = []

        self.parent = None
        self.children = []

    def show(self):
        if self.name != 'root':
            space = '    ' * self.space
            print(space + '<' + self.name + '>:')
            space += '    '
            for key, val in self.attr:
                print(space + key + ': ' + val)
        for child in self.children:
            child.show()

    def add(self, attr):
        self.attr.append(attr)

    def add_node(self, node):
        self.children.append(node)

        if node.parent:
            Log.warning('{node} already has parent'.format(node=node))
        node.parent = self

    #前面num级节点
    def prev(self, num):
        node = self
        for i in range(num):
            node = node.parent
            if node is None:
                return None
        return node

    #根节点
    @property
    def root(self):
        node = self
        while node.parent:
            node = node.parent
        return node


class Config(object):
    LEGAL_CLASS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    LEGAL_VAR = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_'

    def __init__(self):
        #tree = ElementTree.parse('config/testconfig.xml')
        #root = tree.getroot()
        self.root = Node('root', -1)
        self.plugins = Manager.get_plugins() #已有的插件类
        self.load('config/testconfig.vx')

    def load(self, name):
        with open(name, 'r') as fp:
            lines = fp.readlines()

        process_data = []
        plugins = set()
        base_class = '' #当前行所在最顶层的类
        attr_space = -1 #属性对应的缩进
        last_space = -1
        for line_number, line in enumerate(lines):
            line_number += 1 #行号

            #计算开头空格数
            space = 0
            for s in line:
                if s == ' ':
                    space += 1
                elif s == '\t':
                    space += 4
                else:
                    break

            line = line.strip()
            if not line: #空行
                continue
            if line[0] == '#': #注释
                continue

            if space % 4 != 0: #缩进不是4的倍数
                print('Invalid indentation, must be a multiple of 4 spaces')
                return False

            space = int(space / 4)

            if space - last_space >= 2: #缩进跳跃太多，防止一次多2个缩进
                print('Unindent does not match any outer indentation level')
                return False

            split_line = self._strip_split(line, ':', 1)
            if len(split_line) == 1: #其他的语法
                print('Other')
                return False

            key, val = split_line
            if not key: #键值为空
                print('Key is empty')
                return False
            if key[0] == '<' or key[-1] == '>':
                if key[0] != '<' or key[-1] != '>': #键值格式不对
                    print('Key is not right')
                    return False
                #类声明
                key = key[1:-1].strip()
                if not key: #键值为空
                    print('Key is empty')
                    return False

                split_key = self._strip_split(key, '@')
                if len(split_key) > 2: #@表示继承关系
                    print('Too many @')
                    return False

                class_name = split_key[0]
                if not self._legal_class(class_name): #类命不合法
                    print('Class is illegal', class_name)
                    return False

                if len(split_key) == 2: #新建类并设定格式
                    if space != 0: #新建类不能在其他类中定义
                        print('New class can not be define in other class')
                        return False
                    base_class = class_name

                    base_list = self._strip_split(split_key[1], '+')
                    for base in base_list:
                        if not self._legal_class(base):
                            print('Class is illegal', base)
                            return False
                        if base not in self.plugins and base not in plugins:
                            print('Class not exist', base)
                            return False
                    plugins.add(class_name)

                    process_data.append(('nclass', line_number, space, class_name, base_list))
                else: #设定已有类格式
                    if space == 0:
                        base_class = ''
                    if class_name not in self.plugins and class_name not in plugins:
                        print('Class not exist', class_name)
                        return False
                    if class_name == base_class: #新建类不能作为该类的子节点
                        print('New class can not be subclass')
                        return False
                    process_data.append(('class', line_number, space, class_name))
                attr_space = space + 1
            else:
                if space != attr_space: #属性值必须跟在类定义后面
                    print('Attribute must follow class')
                    return False
                if not self._legal_var(key):
                    print('Var is illegal')
                    return False

                process_data.append(('data', line_number, space, key, val))

            last_space = space

        cursor_node = self.root #当前节点
        last_space = 0 #上一行的缩进
        for line in process_data:
            line_type, line_number, space = line[:3]
            line = line[3:]
            if line_type == 'data':
                key, val = line[:2]
                cursor_node.add((key, val))
            else:
                class_name = line[0]
                if line_type == 'nclass':
                    base_list = line[1]

                node = Node(class_name, space)
                if space == cursor_node.space + 1:
                    cursor_node.add_node(node)
                else:
                    parent = cursor_node.prev(space - cursor_node.space)
                    parent.add_node(node)

                cursor_node = node
        self.root.show()

    #分割后去空格
    def _strip_split(self, info, sep, maxsplit=-1):
        return [s.strip() for s in info.split(sep, maxsplit)]

    #类名称是否合法
    def _legal_class(self, class_name):
        if not class_name: #名称为空
            return False
        if class_name[0] not in self.LEGAL_CLASS: #首字母不是大写
            return False
        for s in class_name:
            if s not in self.LEGAL_VAR:
                return ''
        return True

    #判断变量是否合法
    def _legal_var(self, var_name):
        if not var_name: #名称为空
            return False
        for s in var_name:
            if s not in self.LEGAL_VAR:
                return ''
        return True


if __name__ == '__main__':
    Manager.auto_load()
    Config()
