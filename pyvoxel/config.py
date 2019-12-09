# -*- coding: utf-8 -*-
from pyvoxel.manager import Manager
#from pyvoxel.node import Node
from pyvoxel.log import Log
from ast import literal_eval
import re


class ConfigMethod(object):
    LEGAL_CLASS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    LEGAL_ALIAS = 'abcdefghijklmnopqrstuvwxyz0123456789_'
    LEGAL_VAR = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_'

    BASE_ALIAS = '__ALIAS__' #默认别名，使用大写保证和其他别名不相同
    CLASS_SPLIT = '-' #类和别名之间的分割符必须是非法的别名字符

    #分割后去空格
    @staticmethod
    def strip_split(info, sep, maxsplit=-1):
        return [s.strip() for s in info.split(sep, maxsplit)]

    #类名称是否合法
    @classmethod
    def legal_class(self, class_name):
        if not class_name: #名称为空
            return False
        if class_name[0] not in self.LEGAL_CLASS: #首字母不是大写
            return False
        for s in class_name:
            if s not in self.LEGAL_VAR:
                return False
        return True

    #判断是否是别名
    @classmethod
    def is_alias(self, name):
        if not name:
            return False
        if name == self.BASE_ALIAS:
            return True
        if name[0] not in self.LEGAL_ALIAS:
            return False
        return True

    #判断别名是否合法
    @classmethod
    def legal_alias(self, alias_name):
        if not alias_name:
            return False
        if alias_name == self.BASE_ALIAS: #默认别名
            return True
        for s in alias_name: #别名不能有大写字母
            if s not in self.LEGAL_ALIAS:
                return False
        return True

    #判断变量是否合法
    @classmethod
    def legal_var(self, var_name):
        if not var_name: #名称为空
            return False
        for s in var_name:
            if s not in self.LEGAL_VAR:
                return ''
        return True

    @classmethod
    def split_alias(self, name):
        if name.endswith(')'):
            name = name[:-1]

            split_line = self.strip_split(name, '(', 1)
            if len(split_line) == 1:
                return False, 'No ( find'

            class_name, alias_name = split_line
            if not self.legal_class(class_name): #类命不合法
                return False, 'Class is illegal ' + str(class_name)

            if not alias_name: #括号里为空
                return False, 'Alias is empty'

            return True, (class_name, alias_name)

        if not self.legal_class(name): #类命不合法
            return False, 'Class is illegal ' + str(name)
        return True, (name, self.BASE_ALIAS)

    #检查继承
    @staticmethod
    def is_inherit(nest_inherit, class_key, cls_set):
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

    @classmethod
    def real_name(self, class_name, class_alias):
        if class_alias == self.BASE_ALIAS:
            return class_name
        else:
            return '{}{}{}'.format(class_name, self.CLASS_SPLIT, class_alias)

    @classmethod
    def class_type(self, name, sconfig, config):
        if name in config['newclass']: #先查找新建的类
            return 'newclass'
        if name in config['otherclass']:
            return 'otherclass'
        if name in sconfig['plugins']:
            return 'plugins'
        if name in sconfig['globals']:
            return 'globals'
        return ''

    #获取类，类是否是配置中新建的类，类的定义
    @classmethod
    def get_class(self, name, config):
        if name in config['newclass']: #先查找新建的类
            return config['newclass'][name]
        #if name in config['otherclass']:
        #    return config['otherclass'][name]
        return None


#类中attr属性改变时触发on_attr事件，同时同步改变关联的值
class Node(object):
    def __new__(cls): #不用在子类中调用super初始化
        cls._init(cls)
        return super().__new__(cls)

    def _init(cls):
        cls._trigger = {}
        cls._reflex = {}
        cls.parent = None
        cls.children = []
        if not hasattr(cls, '_config'):
            return

        name, root, sconfig, config = getattr(cls, '_config')
        node = config['newnode'][name]
        print(node, name, node.__class__.__name__)

        for child in node.children:
            child_name = child.__class__.__name__
            method_class = ConfigMethod.get_class(child_name, sconfig, config)
            child_name = child_name.split('-')[0]
            is_local, child_node = ConfigMethod.get_class(child_name, sconfig, {'newclass': {}, 'otherclass': {}})
            print(child_name, child_node)
            cls.children.append(child_node())


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


#使用配置树的模式可以检查配置的有效性，不生成类结构会导致只能在运行时检查配置的有效性
#运行前检测配置可能降低一些灵活性，但代码安全性会有很大的提高
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
        if hasattr(self, name): #静态变量已通过继承生成
            return True, 'Static'

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

        #查找所有变量
        offset = 0
        for i, p in enumerate(re.finditer(ptn, expr, flags=re.I)):
            iname = '_x{i}'.format(i=i)
            pname = p.group()

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

    def _load(self, lines, sconfig):
        config = {
            'newclass': {}, #配置文件中新建的类
            'otherclass': {}, #没有被新建的插件类或外部类
            'newnode': {}
        }

        root = ConfigNode() #根节点

        process_data = [] #预处理后的数据
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
                return False, (line_number, line_real, 'Invalid indentation, must be a multiple of 4 spaces')

            space = int(space / 4)

            if space - last_space >= 2: #缩进跳跃太多，防止一次多2个缩进
                return False, (line_number, line_real, 'Unindent does not match any outer indentation level')
            last_space = space


            split_line = ConfigMethod.strip_split(line, ':', 1)
            if len(split_line) == 1: #其他的语法
                return False, (line_number, line_real, 'Other')

            key, val = split_line
            if not key: #键值为空
                return False, (line_number, line_real, 'Key is empty')

            if val: #定义属性
                if space != attr_space: #属性值必须跟在类定义后面
                    return False, (line_number, line_real, 'Attribute must follow class')

                if not ConfigMethod.legal_var(key):
                    return False, (line_number, line_real, 'Var is illegal')

                #统计类的属性，按行号索引
                cite_cursor.setdefault(cursor_line, {})
                cite_cursor[cursor_line][key] = (line_number, line_real, val)
                #属性分为动态属性和静态属性，动态属性在该属性在引用的其他属性变化时动态变化
                #operate_type = 'attr'
                #process_data[line_number] = (operate_type, line_number, line_real, space, key, (is_expr, val))
            else: #类
                if space == 0:
                    if key[0] != '<' or key[-1] != '>': #键值格式不对
                        return False, (line_number, line_real, 'Key is not right')

                    #类的声明
                    key = key[1:-1].strip()
                    if not key: #键值为空
                        return False, (line_number, line_real, 'Class is empty')

                split_line = ConfigMethod.strip_split(key, '->', 1) #解析别名
                if len(split_line) == 1:
                    class_info, = split_line
                    class_alias = ConfigMethod.BASE_ALIAS #没有别名
                else:
                    class_info, class_alias = split_line
                    if not ConfigMethod.legal_alias(class_alias): #别名不合法
                        return False, (line_number, line_real, 'Alias is illegal')

                #<T(s)>, T(s), <T(S)>
                is_success, class_split = ConfigMethod.split_alias(class_info)
                if not is_success:
                    return False, (line_number, line_real, class_split)

                class_name, alias_name = class_split
                class_key = class_name, class_alias

                #新建类，<T>, <T -> t>, <T(S) -> t>, <T(S(s), t1) -> t2>
                if space == 0:
                    nest_key = class_key

                    if class_key in nest_class: #类重复定义
                        return False, (line_number, line_real, 'Class can not redefine')

                    #类定义需要在继承类之前（或者为外部类）
                    for inherit_set in nest_inherit.values():
                        if class_key in inherit_set:
                            return False, (line_number, line_real, 'Class must define before inherit')

                    #类定义需要在使用类之前
                    for nest_set in nest_class.values():
                        if class_key in nest_set:
                            return False, (line_number, line_real, 'Class must define before use')

                    if alias_name == ConfigMethod.BASE_ALIAS: #没有继承
                        if class_alias == ConfigMethod.BASE_ALIAS: #<T>, 类没有定义
                            if not ConfigMethod.class_type(class_name, sconfig, config):
                                return False, (line_number, line_real, 'Class not exist')
                            operate_type = 'baseclass'
                            data = None
                        else: #<T -> t>
                            operate_type = 'aliasclass'
                            data = class_alias
                    else: #使用继承关系生成类
                        #已有的类不能重新生成（防止一些定义冲突）
                        if ConfigMethod.class_type(class_name, sconfig, config) in ('plugins', 'globals'):
                            return False, (line_number, line_real, 'Class is redefine in plugins or globals')
                        cls_list = []
                        for cls_name in ConfigMethod.strip_split(alias_name, ','):
                            if ConfigMethod.is_alias(cls_name): #引用自身的别名，<T(t)> => <T(T(t))>
                                cls_split = (class_name, cls_name)
                            else:
                                is_success, cls_split = ConfigMethod.split_alias(cls_name)
                                if not is_success:
                                    return False, (line_number, line_real, cls_split)
                            cls_name, cls_alias_name = cls_split
                            if cls_alias_name != ConfigMethod.BASE_ALIAS:
                                if cls_split not in nest_class: #未定义的类不能使用别名引用
                                    return False, (line_number, line_real, 'Alias must exist')

                            cls_list.append(cls_split)

                        #新建的类有继承关系
                        nest_inherit[class_key] = set(cls_list) #先放进去可以判断继承自身
                        if not ConfigMethod.is_inherit(nest_inherit, class_key, set(cls_list)):
                            return False, (line_number, line_real, 'Class inherit is nested')

                        #使用cls_list创建名称为class_name的新类
                        operate_type = 'newclass'
                        data = cls_list

                    #类尚未新建，没有子节点的类也需要统计，不能用setdefault
                    if class_key not in nest_class:
                        nest_class[class_key] = set()
                else: #别名查找类，T(t1) -> t2
                    #T(t1) -> t2，class_split相当于(T, t1)，class_key相当于(T, t2)
                    if class_split == nest_key: #类内部不能使用自身
                        return False, (line_number, line_real, 'Class can not use when define')

                    nest_class[nest_key].add(class_split)
                    if class_alias != ConfigMethod.BASE_ALIAS: #统计子节点的别名
                        cite_class.setdefault(nest_key, {})
                        cite_class[nest_key][class_alias] = line_number #class_split

                    if not ConfigMethod.legal_alias(alias_name): #别名索引不合法
                        return False, (line_number, line_real, 'Alias is illegal')
                    if alias_name != ConfigMethod.BASE_ALIAS:
                        if class_split not in nest_class: #未定义的类不能使用别名引用
                            return False, (line_number, line_real, 'Alias must exist')

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
            if operate_type in ('baseclass', 'aliasclass', 'newclass'):
                class_real_name = ConfigMethod.real_name(class_name, class_alias)
            elif operate_type == 'findclass':
                class_real_name = ConfigMethod.real_name(class_name, data)

            if operate_type == 'baseclass': #<T>
                base_type = {class_real_name: ConfigMethod.class_type(class_name, sconfig, config)}
            elif operate_type == 'aliasclass': #<T -> t>
                base_type = {class_real_name: ConfigMethod.class_type(class_name, sconfig, config)}
            elif operate_type == 'newclass': #<T(S)>, <T(S) -> t>
                cls_list = [ConfigMethod.real_name(cls_name, cls_alias) for cls_name, cls_alias in data]
                base_type = {cls_name: ConfigMethod.class_type(cls_name, sconfig, config) for cls_name in cls_list}
            elif operate_type == 'findclass': #T(t) -> r
                base_type = {class_real_name: ConfigMethod.class_type(class_real_name, sconfig, config)}
            else:
                return False, (line_number, line_real, 'Operate type error')

            base = []
            for cls_name, cls_type in base_type.items():
                if not cls_type: #父类不存在
                    return False, (line_number, line_real, 'Base class not exist')

            for cls_name, cls_type in base_type.items(): #新建配置类不直接使用外部类，防止不必要的初始化，继承类中的静态变量
                cls = ConfigMethod.get_class(cls_name, config)
                if cls is None:
                    cls = type(cls_name, (ConfigNode,), {}) #cls.__name__可能会被修改
                    config['newclass'][cls_name] = cls
                base.append(cls)

            try: #创建节点
                #类中可以使用的索引序列，先用行号索引，再替换成对应节点，用字典保证相同nest_key对应的节点为同一个
                class_attr = cite_cursor.get(line_number, {}) #类中的属性，静态类型可继承

                static_attr = {} #静态属性，为python常量
                dynamic_expr = {} #类中动态属性，继承会导致关系混乱，因此不继承
                for k, v in class_attr.items():
                    linen, liner, expr = v
                    #值是否是python中的常量
                    try:
                        expr = literal_eval(expr)
                        static_attr[k] = expr
                    except:
                        dynamic_expr[k] = (linen, liner, expr) #出错提示

                static_attr['_ids'] = cite_class.get(nest_key, {})

                if operate_type in ('baseclass', 'aliasclass', 'newclass'): #需要新建的类（根类）
                    node_type = type(class_real_name, tuple(base), static_attr) #只继承静态属性
                    node = node_type()
                    config['newclass'][class_real_name] = node_type
                    config['newnode'][class_real_name] = node
                else:
                    #node_type = config['newclass'][class_real_name]
                    node_type = type(class_real_name, tuple(base), static_attr) #只继承静态属性
                    node = node_type()

                node._class_attr = class_attr #尽量不要重复，暂存动态属性
            except:
                Log.exception()
                return False, (line_number, line_real, 'Create class failed')

            try: #查找父节点
                parent = cursor_node
                if space != cursor_space + 1:
                    parent = cursor_node
                    for i in range(cursor_space - space + 1):
                        parent = parent.parent

                parent.add_node(node)
            except:
                Log.exception()
                return False, (line_number, line_real, 'Add class failed')

            try: #查找根节点
                rootnode = node
                while rootnode.parent.parent:
                    rootnode = rootnode.parent
                node._ids['root'] = rootnode
            except:
                Log.exception()
                return False, (line_number, line_real, 'Get root class failed')

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
            for key, val in node._class_attr.items():
                line_number, line_real, expr = val

                is_success, message = node.bind(key, expr, local)
                if not is_success:
                    return False, (line_number, line_real, message)
            delattr(node, '_class_attr')

        return True, (root, config)

    def create_class(self, root, sconfig, config):
        for node, deep in root.walk(isroot=False):
            print(node._trigger, node._reflex)

        def check_parent_class(base, deep=0):
            if deep > 32: #类层级太多或者循环继承
                return False
            if base == Node:
                return True
            if base == object:
                return False
            for b in base.__bases__:
                if check_parent_class(b, deep + 1):
                    return True
            return False

        #导入全局变量
        for node_name in config['newclass'].keys():
            if ConfigMethod.CLASS_SPLIT in node_name:
                continue

            #插件类或外部类，将类与节点绑定，类初始化时按照配置树的结构初始类的成员变量
            if node_name in globals():
                node_type = globals()[node_name]
            elif node_name in sconfig['plugins']:
                node_type = sconfig['plugins'][node_name]

            #根据的父类和属性重新生成类
            base_list = []
            for base in node_type.__bases__:
                if base == object:
                    continue
                base_list.append(base)
            if not check_parent_class(node_type): #父类中不存在Node节点
                base_list.append(Node)

            base_attr = dict(node_type.__dict__)
            base_attr['_config'] = node_name, root, sconfig, config
            globals()[node_name] = type(node_name, tuple(base_list), base_attr)

    def load(self, data):
        sconfig = {
            'globals': globals(),
            'plugins': Manager.plugins, #已有的插件类
        }

        try:
            if '\n' not in data or '\r' not in data: #字符串
                with open(data, 'r', encoding='utf-8') as fp:
                    data = fp.read()
            data = data.replace('\r\n', '\n').replace('\n\r', '\n').replace('\r', '\n') #分割后再替换
            lines = data.split('\n')
            is_success, info  = self._load(lines, sconfig)
            if not is_success:
                line_number, line_real, message = info
                Log.error('{} {} {}'.format(line_number, line_real, message))
                return None
            root, config = info
        except Exception:
            Log.exception()
            return None

        #self.create_class(root, sconfig, config)
        return root


if __name__ == '__main__':
    class TestWidget(object):
        pass

    class TestWidget05(object):
        def __init__(self):
            print('init')

        def testwidget05(self):
            pass
    TestWidget05.__name__ = 'abc'

    Manager.auto_load()
    config = Config()
    tree = config.load('config/testconfig.vx')
    #root.show()
    #print(tree.children[2].name)
    #tree.children[1].children[0].name = 'xc'
    #root.show()
    #print(tree.children[2].name)

    tw1 = TestWidget05()
