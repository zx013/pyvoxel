# -*- coding: utf-8 -*-
from pyvoxel.manager import Manager
from pyvoxel.node import Node
from pyvoxel.log import Log
from ast import literal_eval
import re


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
    LEGAL_ALIAS = 'abcdefghijklmnopqrstuvwxyz0123456789_'
    LEGAL_VAR = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_'

    BASE_ALIAS = '__ALIAS__' #默认别名，使用大写保证和其他别名不相同

    def __init__(self):
        self.root = Node()
        self.plugins = Manager._instance #已有的插件类
        self.newclass = {} #配置文件中新建的类

        result, line_number, real_line, message = self.load('config/testconfig.vx')
        if not result:
            Log.warning('{} {} {}'.format(line_number, real_line, message))

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
    def _is_inherit(self, nest_inherit, class_key, cls_set):
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

    def _real_name(self, class_name, class_alias):
        if class_alias == self.BASE_ALIAS:
            return class_name
        else:
            return '{}-{}'.format(class_name, class_alias)

    def _get_class(self, name):
        if name in self.newclass:
            return self.newclass[name]
        if name in self.plugins:
            return self.plugins[name]
        if name in globals():
            return globals()[name]
        return None

    def load(self, name):
        with open(name, 'r') as fp:
            lines = fp.readlines()

        process_data = []
        nest_class = {} #类中包含所有的其他类
        nest_key = () #当前的根类
        nest_inherit = {} #类的继承关系

        cursor_line = 0 #当前类所在的行

        cite_class = {} #根类内部的引用
        cite_cursor = {} #统计所有类的属性，行号索引，类名索引会重复

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

                #统计类的属性，按行号索引
                cite_cursor.setdefault(cursor_line, {})
                cite_cursor[cursor_line][key] = (line_number, real_line, is_expr, val)
                #属性分为动态属性和静态属性，动态属性在该属性在引用的其他属性变化时动态变化
                #operate_type = 'attr'
                #process_data[line_number] = (operate_type, line_number, real_line, space, key, (is_expr, val))
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
                        if class_alias == self.BASE_ALIAS: #<T>, 类没有定义
                            if self._get_class(class_name) is None:
                                return False, line_number, real_line, 'Class not exist'
                            operate_type = 'baseclass'
                            data = None
                        else: #<T -> t>
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
                        if not self._is_inherit(nest_inherit, class_key, set(cls_list)):
                            return False, line_number, real_line, 'Class inherit is nested'

                        #使用cls_list创建名称为class_name的新类
                        operate_type = 'newclass'
                        data = cls_list

                    #类尚未新建，没有子节点的类也需要统计，不能用setdefault
                    if class_key not in nest_class:
                        nest_class[class_key] = set()
                else: #别名查找类，T(t1) -> t2
                    #T(t1) -> t2，class_split相当于(T, t1)，class_key相当于(T, t2)
                    if class_split == nest_key: #类内部不能使用自身
                        return False, line_number, real_line, 'Class can not use when define'

                    nest_class[nest_key].add(class_split)
                    if class_alias != self.BASE_ALIAS: #统计子节点的别名
                        cite_class.setdefault(nest_key, {})
                        cite_class[nest_key][class_alias] = line_number #class_split

                    if not self._legal_alias(alias_name): #别名索引不合法
                        return False, line_number, real_line, 'Alias is illegal'
                    if alias_name != self.BASE_ALIAS:
                        if class_split not in nest_class: #未定义的类不能使用别名引用
                            return False, line_number, real_line, 'Alias must exist'

                    #查找class_name类中别名为alias_name的子类
                    operate_type = 'findclass'
                    data = alias_name

                process_data.append((operate_type, line_number, real_line, space, nest_key, class_name, class_alias, data))
                cursor_line = line_number
                attr_space = space + 1

        nest_line = {} #根节点和行数的对应关系
        cursor_node = self.root #当前节点
        cursor_space = -1
        for line in process_data:
            operate_type, line_number, real_line, space, nest_key, class_name, class_alias, data = line
            class_real_name = self._real_name(class_name, class_alias)

            if operate_type == 'baseclass': #<T>
                base = [self._get_class(class_name)]
            elif operate_type == 'aliasclass': #<T -> t>
                base = [self._get_class(class_name)]
            elif operate_type == 'newclass': #<T(S)>, <T(S) -> t>
                cls_list = [self._real_name(cls_name, cls_alias) for cls_name, cls_alias in data]
                base = [self._get_class(cls) for cls in cls_list]
            elif operate_type == 'findclass': #T(t) -> r
                base_name = self._real_name(class_name, data)
                base = [self._get_class(base_name)]
            else:
                return False, line_number, real_line, 'Operate type error'

            for b in base:
                if b is None: #父类不存在
                    return False, line_number, real_line, 'Base class not exist'

            def check_parent_class(base, deep=0):
                if deep > 32: #类层级太多或者循环继承
                    return False
                if isinstance(base, tuple) or isinstance(base, list):
                    for b in base:
                        if check_parent_class(b, deep + 1):
                            return True
                else:
                    if base == Node:
                        return True
                    if base == object:
                        return False
                    for b in base.__bases__:
                        if check_parent_class(b, deep + 1):
                            return True
                return False

            try: #创建节点
                if not check_parent_class(base): #所有的父类中不存在Node节点
                    base.append(Node)

                #类中可以使用的索引序列，先用行号索引，再替换成对应节点，用字典保证相同nest_key对应的节点为同一个
                attr = cite_cursor.get(line_number, {}) #类中的属性，静态类型可继承
                expr = {} #类中动态属性，继承会导致关系混乱，因此不继承
                for k, v in attr.items():
                    linen, liner, is_expr, val = v
                    if is_expr:
                        expr[k] = (linen, liner, val) #出错提示
                    else:
                        attr[k] = val

                attr['_ids'] = cite_class.get(nest_key, {})
                node_type = type(class_real_name, tuple(base), attr)

                if operate_type in ('baseclass', 'aliasclass', 'newclass'): #需要新建的类（根类）
                    self.newclass[class_real_name] = node_type
                node = node_type()
                node._dynamic_expr = expr #尽量不要重复
            except:
                return False, line_number, real_line, 'Create class failed'

            try: #查找父节点
                parent = cursor_node
                if space != cursor_space + 1:
                    parent = cursor_node
                    for i in range(cursor_space - space + 1):
                        parent = parent.parent

                parent.add_node(node)
            except:
                return False, line_number, real_line, 'Add class failed'

            try: #查找根节点
                rootnode = node
                while rootnode.parent.parent:
                    rootnode = rootnode.parent
                node._ids['root'] = rootnode
            except:
                return False, line_number, real_line, 'Get root class failed'

            nest_line[line_number] = node
            cursor_node = node
            cursor_space = space

        #将索引从行号替换成对应节点
        for node, deep in self.root.walk(isroot=False):
            for key, ids_line in node._ids.items():
                if not isinstance(ids_line, int): #节点已经替换
                    continue
                node = nest_line[ids_line]
                node._ids[key] = node

        #通过索引序列解析属性
        for node, deep in self.root.walk(isroot=False):
            local = dict(node._ids)
            local['self'] = node
            for key, val in node._dynamic_expr.items():
                line_number, real_line, expr = val

                #self可省略
                pattern = '(?:^|[^a-z0-9_.])(?=(?!({}))[a-z_]+[a-z0-9_]*)'.format('|'.join(local.keys()))
                bypass = 'self.'
                offset = 0
                for i, p in enumerate(re.finditer(pattern, expr, flags=re.I)):
                    index = p.span()[1] + offset
                    expr = expr[:index] + bypass + expr[index:]
                    offset += len(bypass)

                #parent缩写为p，children[x]缩写为cx
                expr = re.sub('[.]p[.]', '.parent.', expr, flags=re.I)
                expr = re.sub('[.]c([0-9]+)[.]', lambda m: '.children[{}].'.format(m.group(1)), expr, flags=re.I)
                try:
                    val = eval(expr, None, local)
                    setattr(node, key, val)
                except:
                    return False, line_number, real_line, 'Analyse expr error'
                node._dynamic_expr[key] = expr
            #print(node._dynamic_expr)

        #self.root.show()
        return True, 0, '', ''


#(?:^|[^a-z0-9_.]))(self|([a-z_]+[a-z0-9_]*))
if __name__ == '__main__':
    class TestWidget():
        pass
    class TestWidget02():
        pass
    class TestWidget03():
        pass
    class TestWidget05():
        pass
    Manager.auto_load()
    config = Config()
