# -*- coding: utf-8 -*-
from pyvoxel.manager import Manager
from pyvoxel.log import Log


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
    '''
    <>: 表示根类，用来定义或声明一个类
    ->: 在根类中表示以别名新建已有的类，可以用别名搜索
        在非根类中表示类的索引，该索引在当前根类中生效
    (): 在根类中表示类的继承
        在非根类中通过不同的别名使用根类
    root: 根类中所有元素使用root访问该类
    self: 当前类
    '''
    LEGAL_CLASS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    LEGAL_ALIAS = 'abcdefghijklmnopqrstuvwxyz0123456789_'
    LEGAL_VAR = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_'

    BASE_ALIAS = '__ALIAS__' #默认别名，使用大写保证和其他别名不相同

    def __init__(self):
        #tree = ElementTree.parse('config/testconfig.xml')
        #root = tree.getroot()
        self.root = Node('root', -1)
        self.plugins = Manager.get_plugins() #已有的插件类
        self.load('config/testconfig.vx')

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
                return False
        return True

    #判断是否是别名
    def _is_alias(self, name):
        if not name:
            return False
        if name == self.BASE_ALIAS:
            return True
        if name[0] not in self.LEGAL_ALIAS:
            return False
        return True

    #判断别名是否合法
    def _legal_alias(self, alias_name):
        if not alias_name:
            return False
        if alias_name == self.BASE_ALIAS: #默认别名
            return True
        for s in alias_name: #别名不能有大写字母
            if s not in self.LEGAL_ALIAS:
                return False
        return True

    def _check_class(self, class_name, plugins):
        #类名称不合法
        if not self._legal_class(class_name):
            return False

        #类不存在
        if class_name not in self.plugins and class_name not in plugins:
            return False
        return True

    #判断变量是否合法
    def _legal_var(self, var_name):
        if not var_name: #名称为空
            return False
        for s in var_name:
            if s not in self.LEGAL_VAR:
                return ''
        return True

    def _split_alias(self, name):
        if name.endswith(')'):
            name = name[:-1]

            split_line = self._strip_split(name, '(', 1)
            if len(split_line) == 1:
                return False, 'No ( find'

            class_name, alias_name = split_line
            if not self._legal_class(class_name): #类命不合法
                return False, 'Class is illegal ' + str(class_name)

            if not alias_name: #括号里为空
                return False, 'Alias is empty'

            return True, (class_name, alias_name)

        if not self._legal_class(name): #类命不合法
            return False, 'Class is illegal ' + str(name)
        return True, (name, self.BASE_ALIAS)

    #检查继承
    def is_nest_inherit(self, nest_inherit, class_key, cls_set):
        while True:
            class_next = set()
            for cls_key in cls_set:
                if cls_key not in nest_inherit:
                    continue
                class_next |= nest_inherit[cls_key]

            if class_key in class_next:
                return False

            if not class_next:
                break

            cls_set = class_next
        return True

    def is_nest(self, nest_class, nest_inherit, nest_key, class_key):
        nest_set = set()
        nest_set.add(nest_key)
        if nest_key in nest_inherit:
            nest_set |= nest_inherit[nest_key]
        if class_key in nest_set:
            print('err')
        for base_class, base_set in nest_class.items():
            if not base_set:
                continue
        print(nest_set, class_key)
        #print(base_class, base_set, class_key)

    def analyse(self, expr):
        '''
        解析表达式
        '''
        #root，根节点
        #self，自身节点
        pass

    def load(self, name):
        with open(name, 'r') as fp:
            lines = fp.readlines()

        process_data = []
        nest_class = {} #类中包含所有的其他类
        nest_key = () #当前的根类
        nest_inherit = {} #类的继承关系

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
            last_space = space


            split_line = self._strip_split(line, ':', 1)
            if len(split_line) == 1: #其他的语法
                print('Other')
                return False

            key, val = split_line
            if not key: #键值为空
                print('Key is empty')
                return False

            if val: #定义属性
                if space != attr_space: #属性值必须跟在类定义后面
                    print('Attribute must follow class')
                    return False

                if not self._legal_var(key):
                    print('Var is illegal')
                    return False

                operate_type = 'attr'
                process_data.append((operate_type, line_number, space, key, val))
            else: #类
                if space == 0:
                    if key[0] != '<' or key[-1] != '>': #键值格式不对
                        print('Key is not right')
                        return False

                    #类的声明
                    key = key[1:-1].strip()
                    if not key: #键值为空
                        print('Class is empty')
                        return False

                split_line = self._strip_split(key, '->', 1) #解析别名
                if len(split_line) == 1:
                    class_info, = split_line
                    class_alias = self.BASE_ALIAS #没有别名
                else:
                    class_info, class_alias = split_line
                    if not self._legal_alias(class_alias): #别名不合法
                        print('Alias is illegal')
                        return False

                #<T(s)>, T(s), <T(S)>
                result, class_split = self._split_alias(class_info)
                if not result:
                    print(class_split)
                    return False

                class_name, alias_name = class_split
                class_key = class_name, class_alias

                #新建类，<T>, <T -> t>, <T(S) -> t>, <T(S(s), t1) -> t2>
                if space == 0:
                    nest_key = class_key

                    if class_key in nest_class: #类重复定义
                        print('Class can not redefine', class_key)
                        return False

                    if alias_name == self.BASE_ALIAS: #没有继承
                        operate_type = 'aliasclass'
                        data = class_alias
                    else: #使用继承关系生成类
                        cls_list = []
                        for cls_name in self._strip_split(alias_name, ','):
                            if self._is_alias(cls_name): #引用自身的别名，<T(t)> => <T(T(t))>
                                cls_split = (class_name, cls_name)
                            else:
                                result, cls_split = self._split_alias(cls_name)
                                if not result:
                                    print(cls_split)
                                    return False
                            cls_name, cls_alias_name = cls_split
                            if cls_alias_name != self.BASE_ALIAS:
                                if cls_split not in nest_class: #未定义的类不能使用别名引用
                                    print('Alias must exist')
                                    return False

                            cls_list.append(cls_split)

                        #新建的类有继承关系
                        nest_inherit[class_key] = set(cls_list) #先放进去可以判断继承自身
                        if not self.is_nest_inherit(nest_inherit, class_key, set(cls_list)):
                            print('Class inherit is nested')
                            return False

                        #使用cls_list创建名称为class_name的新类
                        operate_type = 'newclass'
                        data = cls_list

                    if class_key not in nest_class: #类尚未新建
                        nest_class[class_key] = set()

                else: #别名查找类，T(t)
                    nest_class[nest_key].add(class_key)

                    if not self._legal_alias(alias_name): #别名索引不合法
                        print('Alias is illegal')
                        return False
                    if alias_name != self.BASE_ALIAS:
                        if class_split not in nest_class: #未定义的类不能使用别名引用
                            print('Alias must exist')
                            return False

                    #判断类使用是否循环，如果一个类有继承，则这个类包括它的所有继承
                    self.is_nest(nest_class, nest_inherit, nest_key, class_key)

                    #查找class_name类中别名为alias_name的子类
                    operate_type = 'findclass'
                    data = alias_name

                '''
                if space == 0:
                    #防止类的嵌套定义，但无法处理循环嵌套
                    if class_alias == self.BASE_ALIAS:
                        base_class = ''
                        base_alias = []
                    else:
                        base_class = class_name
                        if operate_type == 'newclass':
                            base_alias = [self.BASE_ALIAS, class_alias]
                        else:
                            base_alias = [class_alias]
                else:
                    if class_name == base_class: #新建类不能作为该类的子节点
                        if operate_type != 'aliasclass':
                            alias_name = self.BASE_ALIAS
                        for alias in base_alias:
                            if alias_name == alias:
                                print('New class or Alias class can not be subclass')
                                return False
                '''

                process_data.append((operate_type, line_number, space, class_name, class_alias, data))
                attr_space = space + 1

        cursor_node = self.root #当前节点
        for line in process_data:
            operate_type, line_number, space = line[:3]
            line = line[3:]
            if operate_type == 'attr':
                key, val = line[:2]
                self.analyse(val)
                cursor_node.add((key, val))
            else:
                class_name, class_alias = line[:2]
                if operate_type == 'newclass':
                    cls_list = line[1]

                node = Node(class_name, space)
                if space == cursor_node.space + 1:
                    cursor_node.add_node(node)
                else:
                    parent = cursor_node.prev(space - cursor_node.space)
                    parent.add_node(node)

                cursor_node = node
        #self.root.show()
        #print(node_dict)


if __name__ == '__main__':
    Manager.auto_load()
    Config()
