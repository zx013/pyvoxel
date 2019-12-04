# -*- coding: utf-8 -*-
from pyvoxel.manager import Manager
from pyvoxel.node import Node
from pyvoxel.log import Log
from ast import literal_eval
import re


class ConfigNode(object):
    def __init__(self):
        self._trigger = {}
        self._reflex = {}
        self.parent = None
        self.children = []

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

    #使用缩写语法，p代表parent，c1代表children[1]，缩写语法默认添加self
    #使用bind绑定时，所有的变量必须可访问
    def bind(self, name, expr, local={}):
        if '__import__' in expr: #literal_eval不能设置locals，因此需要对expr进行判断
            return False, 'Expr can not use __import__.'

        local['self'] = self

        #表达式中的字符串不参与匹配，解析表达式中的字符串
        cursor = None #字符串起始标识
        sinfo = [] #字符串起始位置
        backslash = False #反斜杠
        size = len(expr) #字符串长度
        n = 0
        while n < size:
            if cursor is None:
                if expr[n: n + 3] in ("'''", '"""'):
                    cursor = expr[n: n + 3]
                    begin = n
                    n += 3
                    continue
                if expr[n] in ("'", '"'): #进入字符串
                    cursor = expr[n]
                    begin = n
            elif backslash: #转义字符
                backslash = False
            elif expr[n] == '\\': #反斜杠
                backslash = True
            elif cursor in ("'''", '"""') and expr[n: n + 3] == cursor:
                cursor = None
                n += 3
                sinfo.append((begin, n))
                continue
            elif cursor in ("'", '"') and expr[n] == cursor:
                cursor = None
                n += 1
                sinfo.append((begin, n))
                continue
            n += 1

        #替换字符串
        smap = {}
        offset = 0
        for i, (begin, end) in enumerate(sinfo):
            sname = '_s{i}'.format(i=i)
            sval = expr[begin + offset:end + offset]
            expr = expr.replace(sval, sname, 1)
            smap[sname] = sval
            offset -= len(sval) - len(sname)

        #self可省略
        ptn = '(?:^|[^a-z0-9_.])(?=(?!({}))[a-z_]+[a-z0-9_]*)'.format('|'.join(local.keys() | smap.keys()))
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
        pset = []
        #查找所有变量
        offset = 0
        for i, p in enumerate(re.finditer(ptn, expr, flags=re.I)):
            iname = '_x{i}'.format(i=i)
            pname = p.group()
            if pname in pset: #防止重复定义
                continue

            plist = pname.split('.')
            try: #定位变量所在的类
                rname = '' #逆向索引字符串
                base_cls = local[plist[0]]
                for node in plist[1:-1]:
                    if node.startswith('parent'):
                        for n, c in enumerate(base_cls.parent.children):
                            if c == base_cls:
                                break
                        rname = '.children[{}]'.format(n) + rname
                        base_cls = base_cls.parent
                    elif node.startswith('children'):
                        rname = '.parent' + rname
                        base_cls = base_cls.children[int(node.split('[')[1].split(']')[0])]
                rname = 'self' + rname
            except Exception:
                return False, 'Analyse attr error'
            base_name = plist[-1]

            pset.append(pname)
            base_key = (base_cls, base_name)
            if base_key in pattern: #相同的变量使用相同的名称
                iname, _, _ = pattern[base_key]
            else:
                pn = '.'.join(plist[:-1]).replace('self.', '').replace('self', '').replace('parent', 'p').replace('children', 'c').replace('[', '').replace(']', '')
                rn = rname.replace('self.', '').replace('self', '').replace('parent', 'p').replace('children', 'c').replace('[', '').replace(']', '')
                pattern[base_key] = iname, pn, rn

            #不能直接用replace，会有名称部分包含的情况
            sindex = p.span()[0] + offset
            eindex = p.span()[1] + offset
            expr = expr[:sindex] + iname + expr[eindex:]
            offset -= len(pname) - len(iname)

        #将标识替换回字符串
        for sname, sval in smap.items(): #似乎可以不用按照从小到大的顺序，更大的索引不会匹配到更小的索引
            expr = expr.replace(sname, sval, 1)

        try:
            local = {} #使语句中的self生效
            for key, val in pattern.items():
                base_cls, base_name = key
                iname, pname, rname = val
                local[iname] = getattr(base_cls, base_name)
            value = eval(expr, None, local)
            setattr(self, name, value)
        except Exception as ex:
            print(expr, ex)
            return False, 'Run expr error'

        #能够正常获取参数值时，写入配置变量
        reflex = {}
        for key, val in pattern.items():
            base_cls, base_name = key
            iname, pname, rname = val
            base_cls._trigger.setdefault(base_name, set())
            base_cls._trigger[base_name].add('{}.{}'.format(rname, name) if rname else name)
            reflex['{}.{}'.format(pname, base_name) if pname else base_name] = iname
        self._reflex[name] = (expr, reflex, local)
        return True, 'Success'


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
        self.plugins = Manager._instance #已有的插件类
        self.newclass = {} #配置文件中新建的类

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
        cls = None
        if name in self.newclass:
            return self.newclass[name]
        if name in self.plugins:
            cls = self.plugins[name]
        if name in globals():
            cls = globals()[name]
        if cls: #新建类不直接使用外部类
            attr = {}
            for k, v in cls.__dict__.items():
                if k.startswith('_'):
                    continue
                attr[k] = v
            cls = type(name, (ConfigNode,), attr)
            self.newclass[name] = cls
        return cls

    def _load(self, lines):
        root = ConfigNode() #根节点

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
            line_real = line.strip('\r').strip('\n') #原始行，用于出错时的返回
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
                return False, line_number, line_real, 'Invalid indentation, must be a multiple of 4 spaces'

            space = int(space / 4)

            if space - last_space >= 2: #缩进跳跃太多，防止一次多2个缩进
                return False, line_number, line_real, 'Unindent does not match any outer indentation level'
            last_space = space


            split_line = self._strip_split(line, ':', 1)
            if len(split_line) == 1: #其他的语法
                return False, line_number, line_real, 'Other'

            key, val = split_line
            if not key: #键值为空
                return False, line_number, line_real, 'Key is empty'

            if val: #定义属性
                if space != attr_space: #属性值必须跟在类定义后面
                    return False, line_number, line_real, 'Attribute must follow class'

                if not self._legal_var(key):
                    return False, line_number, line_real, 'Var is illegal'

                #值是否是python中的常量
                try:
                    val = literal_eval(val)
                    is_expr = False
                except Exception:
                    is_expr = True

                #统计类的属性，按行号索引
                cite_cursor.setdefault(cursor_line, {})
                cite_cursor[cursor_line][key] = (line_number, line_real, is_expr, val)
                #属性分为动态属性和静态属性，动态属性在该属性在引用的其他属性变化时动态变化
                #operate_type = 'attr'
                #process_data[line_number] = (operate_type, line_number, line_real, space, key, (is_expr, val))
            else: #类
                if space == 0:
                    if key[0] != '<' or key[-1] != '>': #键值格式不对
                        return False, line_number, line_real, 'Key is not right'

                    #类的声明
                    key = key[1:-1].strip()
                    if not key: #键值为空
                        return False, line_number, line_real, 'Class is empty'

                split_line = self._strip_split(key, '->', 1) #解析别名
                if len(split_line) == 1:
                    class_info, = split_line
                    class_alias = self.BASE_ALIAS #没有别名
                else:
                    class_info, class_alias = split_line
                    if not self._legal_alias(class_alias): #别名不合法
                        return False, line_number, line_real, 'Alias is illegal'

                #<T(s)>, T(s), <T(S)>
                result, class_split = self._split_alias(class_info)
                if not result:
                    return False, line_number, line_real, class_split

                class_name, alias_name = class_split
                class_key = class_name, class_alias

                #新建类，<T>, <T -> t>, <T(S) -> t>, <T(S(s), t1) -> t2>
                if space == 0:
                    nest_key = class_key

                    if class_key in nest_class: #类重复定义
                        return False, line_number, line_real, 'Class can not redefine'

                    #类定义需要在继承类之前（或者为外部类）
                    for inherit_set in nest_inherit.values():
                        if class_key in inherit_set:
                            return False, line_number, line_real, 'Class must define before inherit'

                    #类定义需要在使用类之前
                    for nest_set in nest_class.values():
                        if class_key in nest_set:
                            return False, line_number, line_real, 'Class must define before use'

                    if alias_name == self.BASE_ALIAS: #没有继承
                        if class_alias == self.BASE_ALIAS: #<T>, 类没有定义
                            if self._get_class(class_name) is None:
                                return False, line_number, line_real, 'Class not exist'
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
                                    return False, line_number, line_real, cls_split
                            cls_name, cls_alias_name = cls_split
                            if cls_alias_name != self.BASE_ALIAS:
                                if cls_split not in nest_class: #未定义的类不能使用别名引用
                                    return False, line_number, line_real, 'Alias must exist'

                            cls_list.append(cls_split)

                        #新建的类有继承关系
                        nest_inherit[class_key] = set(cls_list) #先放进去可以判断继承自身
                        if not self._is_inherit(nest_inherit, class_key, set(cls_list)):
                            return False, line_number, line_real, 'Class inherit is nested'

                        #使用cls_list创建名称为class_name的新类
                        operate_type = 'newclass'
                        data = cls_list

                    #类尚未新建，没有子节点的类也需要统计，不能用setdefault
                    if class_key not in nest_class:
                        nest_class[class_key] = set()
                else: #别名查找类，T(t1) -> t2
                    #T(t1) -> t2，class_split相当于(T, t1)，class_key相当于(T, t2)
                    if class_split == nest_key: #类内部不能使用自身
                        return False, line_number, line_real, 'Class can not use when define'

                    nest_class[nest_key].add(class_split)
                    if class_alias != self.BASE_ALIAS: #统计子节点的别名
                        cite_class.setdefault(nest_key, {})
                        cite_class[nest_key][class_alias] = line_number #class_split

                    if not self._legal_alias(alias_name): #别名索引不合法
                        return False, line_number, line_real, 'Alias is illegal'
                    if alias_name != self.BASE_ALIAS:
                        if class_split not in nest_class: #未定义的类不能使用别名引用
                            return False, line_number, line_real, 'Alias must exist'

                    #查找class_name类中别名为alias_name的子类
                    operate_type = 'findclass'
                    data = alias_name

                process_data.append((operate_type, line_number, line_real, space, nest_key, class_name, class_alias, data))
                cursor_line = line_number
                attr_space = space + 1

        nest_line = {} #根节点和行数的对应关系
        cursor_node = root #当前节点
        cursor_space = -1
        for line in process_data:
            operate_type, line_number, line_real, space, nest_key, class_name, class_alias, data = line
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
                return False, line_number, line_real, 'Operate type error'

            for b in base:
                if b is None: #父类不存在
                    return False, line_number, line_real, 'Base class not exist'

            def check_parent_class(base, deep=0):
                if deep > 32: #类层级太多或者循环继承
                    return False
                if isinstance(base, tuple) or isinstance(base, list):
                    for b in base:
                        if check_parent_class(b, deep + 1):
                            return True
                else:
                    if base == ConfigNode:
                        return True
                    if base == object:
                        return False
                    for b in base.__bases__:
                        if check_parent_class(b, deep + 1):
                            return True
                return False

            try: #创建节点
                if not check_parent_class(base): #所有的父类中不存在Node节点
                    base.append(ConfigNode)

                #类中可以使用的索引序列，先用行号索引，再替换成对应节点，用字典保证相同nest_key对应的节点为同一个
                total_attr = cite_cursor.get(line_number, {}) #类中的属性，静态类型可继承
                static_attr = {} #静态属性，为python常量
                dynamic_expr = {} #类中动态属性，继承会导致关系混乱，因此不继承
                for k, v in total_attr.items():
                    linen, liner, is_expr, val = v
                    if is_expr:
                        dynamic_expr[k] = (linen, liner, val) #出错提示
                    else:
                        static_attr[k] = val

                static_attr['_ids'] = cite_class.get(nest_key, {})
                node_type = type(class_real_name, tuple(base), static_attr) #只继承静态属性

                if operate_type in ('baseclass', 'aliasclass', 'newclass'): #需要新建的类（根类）
                    print(class_real_name, class_real_name in self.newclass)
                    self.newclass[class_real_name] = node_type
                node = node_type()
                node._dynamic_expr = dynamic_expr #尽量不要重复，暂存动态属性
            except:
                return False, line_number, line_real, 'Create class failed'

            try: #查找父节点
                parent = cursor_node
                if space != cursor_space + 1:
                    parent = cursor_node
                    for i in range(cursor_space - space + 1):
                        parent = parent.parent

                parent.add_node(node)
            except:
                return False, line_number, line_real, 'Add class failed'

            try: #查找根节点
                rootnode = node
                while rootnode.parent.parent:
                    rootnode = rootnode.parent
                node._ids['root'] = rootnode
            except:
                return False, line_number, line_real, 'Get root class failed'

            nest_line[line_number] = node
            cursor_node = node
            cursor_space = space

        #将索引从行号替换成对应节点
        for node, deep in root.walk(isroot=False):
            for key, ids_line in node._ids.items():
                if not isinstance(ids_line, int): #节点已经替换
                    continue
                node = nest_line[ids_line]
                node._ids[key] = node

        #通过索引序列解析属性
        for node, deep in root.walk(isroot=False):
            local = dict(node._ids)
            for key, val in node._dynamic_expr.items():
                line_number, line_real, expr = val

                result, message = node.bind(key, expr, local)
                if not result:
                    return False, line_number, line_real, message
            delattr(node, '_dynamic_expr')

        for node, deep in root.walk(isroot=False):
            print(node._trigger, node._reflex)

        return True, 0, '', root

    def load(self, data):
        try:
            if '\n' not in data or '\r' not in data: #字符串
                with open(data, 'r') as fp:
                    data = fp.read()
            data = data.replace('\r', '\n').replace('\n\n', '\n')
            lines = data.split('\n')
            result, line_number, line_real, message = self._load(lines)
            if not result:
                Log.error('{} {} {}'.format(line_number, line_real, message))
                return None
        except Exception as ex:
            Log.error(ex)
            return None
        return message


if __name__ == '__main__':
    class TestWidget(object):
        pass
    class TestWidget05(object):
        def testwidget05(self):
            pass
    Manager.auto_load()
    config = Config()
    tree = config.load('config/testconfig.vx')
    #root.show()
    print(tree.children[1].name)
    tree.children[1].children[0].name = 'xc'
    #root.show()
    print(tree.children[1].name)
    
    tw = TestWidget05()
