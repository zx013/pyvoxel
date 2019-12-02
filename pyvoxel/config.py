# -*- coding: utf-8 -*-
from pyvoxel.manager import Manager
from pyvoxel.node import Node
from ast import literal_eval


#别名可以转译成self.parent.children[n]的形式（可能影响效率，且结构是静态的）
class Config(object):
    '''
    <>: 表示根类，用来定义一个类
    ->: 在根类中表示以别名新建已有的类，可以用别名搜索
        在非根类中表示类的索引，该索引在当前根类中生效
    (): 在根类中表示类的继承
        在非根类中通过不同的别名使用根类
    root: 根类中所有元素使用root访问该类
    self: 当前类
    '''
    LEGAL_CLASS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    LEGAL_ALIAS = 'abcdefghijklmnopqrstuvwxyz0123456789'
    LEGAL_VAR = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_'

    BASE_ALIAS = '__ALIAS__' #默认别名，使用大写保证和其他别名不相同

    def __init__(self):
        #tree = ElementTree.parse('config/testconfig.xml')
        #root = tree.getroot()
        self.root = Node('root')
        self.plugins = Manager.get_plugins() #已有的插件类

        result, line_number, real_line, message = self.load('config/testconfig.vx')
        if not result:
            print(line_number, real_line, message)

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
            for nest in nest_inherit[nest_key]:
                if nest in nest_class:
                    print('in', nest)
            nest_set |= nest_inherit[nest_key]
        if class_key in nest_set:
            print('err', class_key)
        for base_class, base_set in nest_class.items():
            if not base_set:
                continue
        #print(nest_set, class_key)
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

        cite_class = {} #根类内部的引用
        cite_attr = {} #根类内部的属性

        attr_space = -1 #属性对应的缩进
        last_space = -1
        for line_number, line in enumerate(lines):
            real_line = line.replace('\r', '').replace('\n', '') #原始行，用于出错时的返回
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
                return False, line_number, real_line, 'Invalid indentation, must be a multiple of 4 spaces'

            space = int(space / 4)

            if space - last_space >= 2: #缩进跳跃太多，防止一次多2个缩进
                return False, line_number, real_line, 'Unindent does not match any outer indentation level'
            last_space = space


            split_line = self._strip_split(line, ':', 1)
            if len(split_line) == 1: #其他的语法
                return False, line_number, real_line, 'Other'

            key, val = split_line
            if not key: #键值为空
                return False, line_number, real_line, 'Key is empty'

            if val: #定义属性
                if space != attr_space: #属性值必须跟在类定义后面
                    return False, line_number, real_line, 'Attribute must follow class'

                if not self._legal_var(key):
                    return False, line_number, real_line, 'Var is illegal'

                #值是否是python中的常量
                try:
                    val = literal_eval(val)
                    is_expr = False
                except Exception:
                    is_expr = True

                #统计类的属性
                cite_attr.setdefault(nest_key, {})
                cite_attr[nest_key][key] = (is_expr, val)
                #属性分为动态属性和静态属性，动态属性在该属性在引用的其他属性变化时动态变化
                operate_type = 'attr'
                process_data.append((operate_type, line_number, space, key, (is_expr, val)))
            else: #类
                if space == 0:
                    if key[0] != '<' or key[-1] != '>': #键值格式不对
                        return False, line_number, real_line, 'Key is not right'

                    #类的声明
                    key = key[1:-1].strip()
                    if not key: #键值为空
                        return False, line_number, real_line, 'Class is empty'

                split_line = self._strip_split(key, '->', 1) #解析别名
                if len(split_line) == 1:
                    class_info, = split_line
                    class_alias = self.BASE_ALIAS #没有别名
                else:
                    class_info, class_alias = split_line
                    if not self._legal_alias(class_alias): #别名不合法
                        return False, line_number, real_line, 'Alias is illegal'

                #<T(s)>, T(s), <T(S)>
                result, class_split = self._split_alias(class_info)
                if not result:
                    return False, line_number, real_line, class_split

                class_name, alias_name = class_split
                class_key = class_name, class_alias

                #新建类，<T>, <T -> t>, <T(S) -> t>, <T(S(s), t1) -> t2>
                if space == 0:
                    nest_key = class_key

                    if class_key in nest_class: #类重复定义
                        return False, line_number, real_line, 'Class can not redefine'

                    #类定义需要在继承类之前（或者为外部类）
                    for inherit_set in nest_inherit.values():
                        if class_key in inherit_set:
                            return False, line_number, real_line, 'Class must define before inherit'

                    #类定义需要在使用类之前
                    for nest_set in nest_class.values():
                        if class_key in nest_set:
                            return False, line_number, real_line, 'Class must define before use'

                    if alias_name == self.BASE_ALIAS: #没有继承
                        if class_alias == self.BASE_ALIAS: #类没有定义
                            if class_name not in globals():
                                return False, line_number, real_line, 'Class not exist'
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
                                    return False, line_number, real_line, cls_split
                            cls_name, cls_alias_name = cls_split
                            if cls_alias_name != self.BASE_ALIAS:
                                if cls_split not in nest_class: #未定义的类不能使用别名引用
                                    return False, line_number, real_line, 'Alias must exist'

                            cls_list.append(cls_split)

                        #新建的类有继承关系
                        nest_inherit[class_key] = set(cls_list) #先放进去可以判断继承自身
                        if not self.is_nest_inherit(nest_inherit, class_key, set(cls_list)):
                            return False, line_number, real_line, 'Class inherit is nested'

                        #使用cls_list创建名称为class_name的新类
                        operate_type = 'newclass'
                        data = cls_list

                    #类尚未新建，没有子节点的类也需要统计，不能用setdefault
                    if class_key not in nest_class:
                        nest_class[class_key] = set()
                else: #别名查找类，T(t1) -> t2
                    #T(t1) -> t2，class_split相当于(T, t1)，class_key相当于(T, t2)
                    nest_class[nest_key].add(class_split)
                    if alias_name != self.BASE_ALIAS: #统计子节点的别名
                        cite_class.setdefault(nest_key, {})
                        cite_class[nest_key][alias_name] = class_key

                    if not self._legal_alias(alias_name): #别名索引不合法
                        return False, line_number, real_line, 'Alias is illegal'
                    if alias_name != self.BASE_ALIAS:
                        if class_split not in nest_class: #未定义的类不能使用别名引用
                            return False, line_number, real_line, 'Alias must exist'

                    #查找class_name类中别名为alias_name的子类
                    operate_type = 'findclass'
                    data = alias_name

                process_data.append((operate_type, line_number, space, class_name, class_alias, data))
                attr_space = space + 1

        cursor_node = self.root #当前节点
        cursor_space = -1
        for line in process_data:
            operate_type, line_number, space = line[:3]
            line = line[3:]
            if operate_type == 'attr':
                key, val = line[:2]
                self.analyse(val)
                cursor_node.add((key, val))
            else:
                class_name, class_alias = line[:2]
                if operate_type == 'aliasclass':
                    if class_alias == self.BASE_ALIAS: #<T>
                        node = globals()[class_name](class_name)
                        #print(class_name, class_alias)
                    else: #<T -> t>
                        pass
                if operate_type == 'newclass':
                    cls_list = [class_name if class_alias == self.BASE_ALIAS else class_name + '_' + class_alias for cls_name, cls_alias in line[2]]
                    bases = []
                    print(class_name, cls_list)

                if space == cursor_space + 1:
                    parent = cursor_node
                else:
                    parent = cursor_node.prev_node(cursor_space - space + 1)

                if class_alias == self.BASE_ALIAS:
                    node = type(class_name, (Node,), {})(class_name)
                    #node = Node(class_name)
                else:
                    node = type(class_name + '_' + class_alias, (type(parent),), {})(class_name, class_alias)
                    #node = Node(class_name, class_alias)
                parent.add_node(node)

                cursor_node = node
                cursor_space = space
        #self.root.show()
        return True, 0, '', ''


if __name__ == '__main__':
    class TestWidget03(Node):
        pass
    
    class TestWidget05(Node):
        pass
    #Manager.auto_load()
    Config()
