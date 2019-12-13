# -*- coding: utf-8 -*-
"""解析配置文件."""
from pyvoxel.manager import Manager
# from pyvoxel.node import Node
from pyvoxel.log import Log
from ast import literal_eval
import re


class ConfigMethod:
    """解析配置中使用的静态方法."""

    LEGAL_CLASS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    LEGAL_ALIAS = 'abcdefghijklmnopqrstuvwxyz0123456789_'
    LEGAL_VAR = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_'

    # 属性注解
    NOTE_INFO = {
        'safe': ('safe', 'unsafe'),  # 安全/不安全，属性是否需要安全检查，不设置的使用全局安全设置
        'state': ('static', 'dynamic'),  # 静态/动态，属性是否是静态属性（不使用外部变量进行动态计算）
        # 动态属性索引和子节点访问优先使用的方式，自身的类(selfindex)，来源的基类(baseindex，默认)
        'index': ('selfindex', 'baseindex'),
        # 子节点访问顺序，先访问自身子节点(selfchild)，先访问基类子节点(basechild，默认)
        # index设置为selfindex时生效，若index为baseindex，会将self解析到基类中
        'child': ('selfchild', 'basechild'),
        # python内建的数据类型
        # 'dict', 'complex', 'property', 'enumerate', 'bytes', 'filter', 'reversed', 'super', 'range'
        # 'object', 'frozenset', 'map', 'set', 'zip', 'type', 'str', 'memoryview', 'staticmethod',
        # 'float', 'bool', 'classmethod', 'int', 'tuple', 'list', 'bytearray', 'slice'
        'type': {k for k, v in globals()['__builtins__'].items() if k[0].islower() and isinstance(v, type)}
    }

    BASE_ALIAS = '__ALIAS__'  # 默认别名，使用大写保证和其他别名不相同
    CLASS_SPLIT = '-'  # 类和别名之间的分割符必须是非法的别名字符

    @staticmethod
    def strip_split(info, sep, maxsplit=-1):
        """分割后去空格."""
        return [s.strip() for s in info.split(sep, maxsplit)]

    @classmethod
    def legal_class(self, class_name):
        """类名称是否合法."""
        if not class_name:  # 名称为空
            return False
        if class_name[0] not in self.LEGAL_CLASS:  # 首字母不是大写
            return False
        for s in class_name:
            if s not in self.LEGAL_VAR:
                return False
        return True

    @classmethod
    def is_alias(self, name):
        """判断是否是别名."""
        if not name:
            return False
        if name == self.BASE_ALIAS:
            return True
        if name[0] not in self.LEGAL_ALIAS:
            return False
        return True

    @classmethod
    def legal_alias(self, alias_name):
        """判断别名是否合法."""
        if not alias_name:
            return False
        if alias_name == self.BASE_ALIAS:  # 默认别名
            return True
        for s in alias_name:  # 别名不能有大写字母
            if s not in self.LEGAL_ALIAS:
                return False
        return True

    @classmethod
    def legal_var(self, var_name):
        """判断变量是否合法."""
        if not var_name:  # 名称为空
            return False
        for s in var_name:
            if s not in self.LEGAL_VAR:
                return ''
        return True

    @classmethod
    def split_note(self, name):
        """解析属性中的注解."""
        if name.endswith(')'):
            name = name[:-1]

            split_line = self.strip_split(name, '(', 1)
            if len(split_line) == 1:
                return False, 'No ( find in attr note'

            var_name, note_name = split_line
            if not self.legal_var(var_name):  # 类命不合法
                return False, 'Attr note is illegal'

            if not note_name:  # 括号里为空
                return False, 'Attr note is empty'

            note_info = {}
            for nname in self.strip_split(note_name, '|'):
                for key in self.NOTE_INFO.keys():
                    if nname not in self.NOTE_INFO[key]:
                        continue
                    if key in note_info:
                        return False, 'Attr note {} redefine'.format(key)
                    note_info[key] = nname
                    break
                else:  # 都不属于其它的类型，other为自定义的type类型
                    if 'other' in note_info or 'type' in note_info:
                        return False, 'Attr note type redefine'
                    if not self.legal_class(nname):  # 检查注解名称的合法性，注解中不能使用别名等索引
                        return False, 'Attr note class is illegal'
                    note_info['other'] = nname

            return True, (var_name, note_info)

        if not self.legal_var(name):  # 类命不合法
            return False, 'Attr note is illegal'
        return True, (name, {})

    @classmethod
    def split_alias(self, name):
        """分割形如T(t)的别名."""
        if name.endswith(')'):
            name = name[:-1]

            split_line = self.strip_split(name, '(', 1)
            if len(split_line) == 1:
                return False, 'No ( find'

            class_name, alias_name = split_line
            if not self.legal_class(class_name):  # 类命不合法
                return False, 'Class is illegal'

            if not alias_name:  # 括号里为空
                return False, 'Alias is empty'

            return True, (class_name, alias_name)

        if not self.legal_class(name):  # 类命不合法
            return False, 'Class is illegal ' + str(name)
        return True, (name, self.BASE_ALIAS)

    @staticmethod
    def is_inherit(nest_inherit, class_key, cls_set):
        """检查继承是否包含循环结构."""
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
        """获取类的真实名称（合并类和别名）."""
        if class_alias == self.BASE_ALIAS:
            return class_name
        return '{}{}{}'.format(class_name, self.CLASS_SPLIT, class_alias)

    @classmethod
    def class_type(self, name, sconfig, config):
        """从配置中获取类的来源类型."""
        if name in config['node']:  # 先查找新建的类
            return 'node'
        if name in sconfig['plugins']:
            return 'plugins'
        if name in sconfig['globals']:
            return 'globals'
        return ''

    @classmethod
    def get_class(self, name, config):
        """获取类的定义."""
        if name in config['node']:  # 先查找新建的类
            return config['node'][name]
        return None

    @staticmethod
    def analyse(expr, localkeys=()):
        """解析expr表达式，localkeys为引用的别名列表."""
        try:
            literal_eval(expr)
            return expr, {}, {}
        except Exception:
            pass

        #  表达式中的字符串不参与匹配，解析表达式中的字符串
        cursor = None  # 字符串起始标识
        sinfo = []  # 字符串起始位置
        backslash = False  # 反斜杠
        size = len(expr)  # 字符串长度
        n = 0
        while n < size:
            if cursor is None:
                if expr[n: n + 3] in ("'''", '"""'):
                    cursor = expr[n: n + 3]
                    begin = n
                    n += 3
                    continue
                if expr[n] in ("'", '"'):  # 进入字符串
                    cursor = expr[n]
                    begin = n
            elif backslash:  # 转义字符
                backslash = False
            elif expr[n] == '\\':  # 反斜杠
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

        #  替换字符串
        smap = {}
        offset = 0
        for i, (begin, end) in enumerate(sinfo):
            sname = '__s{i}'.format(i=i)
            sval = expr[begin + offset:end + offset]
            expr = expr.replace(sval, sname, 1)
            try:
                smap[sname] = literal_eval(sval)  # 获取真实的字符串，这里出错说明前面的解析有问题
            except Exception:
                Log.error('Analyse string error : ' + str(sval))
            offset -= len(sval) - len(sname)

        #  默认都有self, root两个变量
        localkeys = tuple(set(localkeys) | set(('self', 'root')))

        #  self可省略，匹配selfa, selfb, a.self
        ptn = '(?:^|[^a-z0-9_.])(?=(?!((?:{localkeys})\\b))[a-z_]+[a-z0-9_]*)'.format(localkeys='|'.join(localkeys | smap.keys()))
        bypass = 'self.'
        offset = 0
        for i, p in enumerate(re.finditer(ptn, expr, flags=re.I)):
            index = p.span()[1] + offset
            expr = expr[:index] + bypass + expr[index:]
            offset += len(bypass)

        #  parent缩写为p，children[x]缩写为cx
        while True:
            size = len(expr)
            expr = re.sub('[.]parent[.]', '.p.', expr, flags=re.I)
            expr = re.sub('[.]children\\[([0-9]+)\\][.]', lambda m: '.c{}.'.format(m.group(1)), expr, flags=re.I)
            if len(expr) == size:
                break

        #  cx.p.可以省略，p.cx.不可省略
        expr = re.sub('[.]c[0-9]+[.]p[.]', '.', expr, flags=re.I)

        # 匹配self.p.c0.name, self, 不匹配a.self, selfa
        ptn = '(?:{localkeys}).((?:p|c[0-9]+).)*[a-z_]+[a-z0-9_]*|(?:^|(?<=[^.]))\\b(?:{localkeys})\\b'.format(localkeys='|'.join(localkeys))
        pattern = {}

        #  查找所有变量
        offset = 0
        for i, p in enumerate(re.finditer(ptn, expr, flags=re.I)):
            iname = '__x{i}'.format(i=i)
            pname = p.group()

            if pname in pattern:  # 相同的变量使用相同的名称
                iname = pattern[pname]
            else:
                pattern[pname] = iname

            #  不能直接用replace，会有名称部分包含的情况
            sindex = p.span()[0] + offset
            eindex = p.span()[1] + offset
            expr = expr[:sindex] + iname + expr[eindex:]
            offset -= len(pname) - len(iname)

        xmap = {v: k for k, v in pattern.items()}
        return expr, xmap, smap


# 类中attr属性改变时触发on_attr事件，同时同步改变关联的值
class Node:
    """节点类."""

    def __new__(cls):  # 不用在子类中调用super初始化
        """初始化触发器等数据."""
        cls._init()
        return super().__new__(cls)

    @classmethod
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
            pass
            #  child_name = child.__class__.__name__
            #  method_class = ConfigMethod.get_class(child_name, sconfig, config)
            #  child_name = child_name.split('-')[0]
            #  is_local, child_node = ConfigMethod.get_class(child_name, sconfig, {'newclass': {}, 'otherclass': {}})
            #  print(child_name, child_node)
            #  cls.children.append(child_node())

    def __setattr__(self, name, value):
        """改变变量时触发数据同步."""
        ovalue = self.__dict__.get(name, None)
        self.__dict__[name] = value

        try:
            self._on_func(name, ovalue, value)
        except Exception as ex:
            Log.error(ex)

    #  调用on_函数
    def _on_func(self, name, ovalue, value):
        on_name = 'on_' + name
        if on_name in self.__dict__:
            on_func = self.__dict__[on_name]
            on_func(ovalue, value)

        if name in self._trigger:
            for node, nname in self._trigger[name]:
                node._update_value(nname, (self, name), value)

    #  更新关联类的值
    def _update_value(self, name, base, basev):
        try:
            expr, pattern, local = self._reflex[name]
            local[pattern[base]] = basev

            value = eval(expr, None, local)
            setattr(self, name, value)
        except Exception as ex:
            Log.error(ex)

    def add_node(self, node):
        """添加节点."""
        self.children.append(node)
        if node.parent:
            Log.warning('{node} already has parent'.format(node=node))
        node.parent = self


# 使用配置树的模式可以检查配置的有效性，不生成类结构会导致只能在运行时检查配置的有效性
# 运行前检测配置可能降低一些灵活性，但代码安全性会有很大的提高
class ConfigNode:
    """从配置中解析出的配置节点."""

    def __init__(self, name, ids):
        """初始化."""
        self.name = name  # 类的名称
        self._ids = ids  # 类的索引
        # 存放属性的名称
        # {'name1': ("'testname1'", {}, {}), 'name2': ('__x0 + __s0', {'__x0': 'self.name1'}, {'__s0': 'testname2'})}
        self.class_attr = {}
        # 标记属性的状态，静态变量(static)，动态变量(dynamic)，未检查变量(uncheck)
        # {'name1': 'static', 'name2': 'dynamic', 'name3': 'uncheck'}
        self.check_attr = {}
        self.class_base = []  # 继承的父类对应的节点

        self.trigger = {}
        self.reflex = {}
        self._parent = None
        self._children = []

    @property
    def ids(self):
        """索引映射."""
        # 基类的引用的覆盖现有的引用，确保基类的引用有效
        ids = dict(self._ids)
        for base in self.class_base:
            ids.update(base.ids)
        return ids

    def get_note(self, name, ntype, nbase):
        """获取索引注解."""
        if name not in self.class_attr:
            return nbase
        line, note, check, attr = self.class_attr[name]
        return note.get(ntype, nbase)

    def get_ids(self, name):
        """根据注解获取索引映射."""
        if self.get_note(name, 'index', 'baseindex') == 'baseindex':
            ids = dict(self._ids)
            for base in self.class_base:
                ids.update(base.get_ids(name))
        else:
            ids = {}
            for base in self.class_base:
                ids.update(base.get_ids(name))
            ids = dict(self._ids)
        return ids

    @property
    def parent(self):
        """父节点."""
        return self._parent

    @property
    def children(self):
        """子节点."""
        children = []
        for base in self.class_base:
            children += base.children
        children += self._children
        return children  # self._children

    def get_children(self, name):
        """根据注解获取子节点."""
        if self.get_note(name, 'child', 'basechild') == 'basechild':
            children = []
            for base in self.class_base:
                children += base.children
            children += self._children
        else:
            children = list(self._children)
            for base in self.class_base:
                children += base.children
        return children

    def _walk(self, deep, isroot=True):
        if isroot:
            yield self, deep
        for child in self._children:
            for node, node_deep in child._walk(deep + 1):
                yield node, node_deep

    def walk(self, isroot=True):
        """遍历节点."""
        for node, deep in self._walk(0, isroot):
            yield node, deep

    def show(self):
        """展示节点结构."""
        for node, deep in self.walk(isroot=False):
            spacesep = '    ' * (deep - 1)
            print(spacesep + '<' + node.name + '>:')
            spacesep += '    '
            for key, val in node.class_attr.items():
                if node.check_attr[key] == 'dynamic':
                    val = val[0]
                print(spacesep + key + ': ' + str(val))

    def add_node(self, node):
        """添加节点."""
        self._children.append(node)
        if node._parent:
            Log.warning('{node} already has parent'.format(node=node))
        node._parent = self

    #  使用缩写语法，p代表parent，c1代表children[1]，缩写语法默认添加self
    #  使用bind绑定时，所有的变量必须可访问
    def _execute(self, name):
        if name not in self.class_attr:
            ids = self.get_ids(name)
            if name in ids:
                return ids[name]
            if name == 'root':
                return
            if name[0] == 'p':
                return self.parent
            if name[0] == 'c':
                index = name[1:]
                children = self.get_children(name)
                if index.isdigit():
                    return children[int(index)]
                return children
            raise Exception

        # 行号，来源节点，注解，校验标志，属性
        line, note, check, attr = self.class_attr[name]

        if check in ('static', 'dynamic'):
            return attr[0]
        expr, xmap, smap = attr

        if '__import__' in expr:  # literal_eval不能设置locals，因此需要对expr进行判断
            raise Exception

        local_info = dict(smap)
        check = 'static' if xmap == {} else 'dynamic'
        for iname, pname in xmap.items():
            # 定位变量所在的类
            rname = ''  # 逆向索引字符串
            plist = pname.split('.')
            base_cls = self.get_ids(name)[plist[0]]

            for pn in plist[1:-1]:
                if pn.startswith('p'):
                    for n, c in enumerate(base_cls.parent.get_children(name)):
                        if c == base_cls:
                            break
                    rname = '.c{}{}'.format(n, rname)
                    base_cls = base_cls.parent
                elif pn.startswith('c'):
                    rname = '.p{}'.format(rname)

                    base_cls = base_cls.get_children(name)[int(pn[1:])]
            rname = 'self' + rname

            base_name = plist[-1]
            local_info[iname] = base_cls._execute(base_name)

        value = eval(expr, None, local_info)
        self.class_attr[name] = line, note, check, (value, (expr, xmap, smap))
        return value

    def execute(self, name):
        """将变量绑定到相关的值."""
        try:
            self._execute(name)
            return True
        except Exception:
            return False

    def add_trigger(self, attr, note):
        """添加触发器."""
        pass
        '''
        # 能够正常获取参数值时，写入配置变量
        reflex = {}
        for key, val in pattern.items():
            base_cls, base_name = key
            iname, pname, rname = val
            base_cls._trigger.setdefault(base_name, set())
            base_cls._trigger[base_name].add('{}.{}'.format(rname, name) if rname else name)
            reflex['{}.{}'.format(pname, base_name) if pname else base_name] = iname
        self._reflex[name] = (expr, reflex, local)
        '''


class Config:
    """
    配置解析.

    <>: 表示根类，用来定义一个类
    ->: 在根类中表示以别名新建已有的类，可以用别名搜索
        在非根类中表示类的索引，该索引在当前根类中生效
    (): 在根类中表示类的继承
        在非根类中通过不同的别名使用根类
    root: 根类中所有元素使用root访问该类
    self: 当前类
    """

    def __init__(self, **kwargs):
        """
        设置初始参数.

        unsafe: 是否允许配置是不安全的（属性中引用了作用域外的变量），默认为False，开启unsafe选项同样会忽略属性中的语法错误和表达式的安全性检查
        """
        self.unsafe = kwargs.get('unsafe', False)

    def _load(self, lines, sconfig):
        config = {
            'node': {}  # 配置文件中新建的类
        }

        root = ConfigNode('root', {})  # 根节点

        line_map = {}  # 行数对应的具体内容
        process_data = []  # 预处理后的数据
        nest_class = {}  # 类中包含所有的其他类
        nest_key = ()  # 当前的根类
        nest_inherit = {}  # 类的继承关系

        cursor_line = 0  # 当前类所在的行

        cite_class = {}  # 根类内部的引用，{('T1', 't'): {'t1': 25}, ('T2', '__ALIAS__'): {'t1': 36, 't2': 37}}
        cite_cursor = {}  # 统计所有类的属性，行号索引，类名索引会重复

        attr_space = -1  # 属性对应的缩进
        last_space = -1
        for line_number, line in enumerate(lines):
            line_real = line.strip('\r').strip('\n')  # 原始行，用于出错时的返回
            line_number += 1  # 行号

            # 计算开头空格数
            space = 0
            for s in line:
                if s == ' ':
                    space += 1
                elif s == '\t':
                    space += 4
                else:
                    break

            line = line.strip()
            if not line:  # 空行
                continue
            if line[0] == '#':  # 注释
                continue

            if space % 4 != 0:  # 缩进不是4的倍数
                return False, (line_number, line_real, 'Invalid indentation, must be a multiple of 4 spaces')

            space = int(space / 4)

            if space - last_space >= 2:  # 缩进跳跃太多，防止一次多2个缩进
                return False, (line_number, line_real, 'Unindent does not match any outer indentation level')
            last_space = space

            split_line = ConfigMethod.strip_split(line, ':', 1)
            if len(split_line) == 1:  # 其他的语法
                return False, (line_number, line_real, 'Other')

            key, val = split_line
            if not key:  # 键值为空
                return False, (line_number, line_real, 'Key is empty')

            if val:  # 定义属性
                if space != attr_space:  # 属性值必须跟在类定义后面
                    return False, (line_number, line_real, 'Attribute must follow class')

                is_success, result = ConfigMethod.split_note(key)  # 解析参数注解
                if not is_success:
                    return False, (line_number, line_real, result)
                name, note = result

                # 统计类的属性，按行号索引
                cite_cursor.setdefault(cursor_line, {})
                cite_cursor[cursor_line][name] = (line_number, line_real, cursor_line, note, val)
                # 属性分为动态属性和静态属性，动态属性在该属性在引用的其他属性变化时动态变化
                # operate_type = 'attr'
                # process_data[line_number] = (operate_type, line_number, line_real, space, key, (is_expr, val))
            else:  # 类
                if space == 0:
                    if key[0] != '<' or key[-1] != '>':  # 键值格式不对
                        return False, (line_number, line_real, 'Key is not right')

                    # 类的声明
                    key = key[1:-1].strip()
                    if not key:  # 键值为空
                        return False, (line_number, line_real, 'Class is empty')

                split_line = ConfigMethod.strip_split(key, '->', 1)  # 解析别名
                if len(split_line) == 1:
                    class_info, = split_line
                    class_alias = ConfigMethod.BASE_ALIAS  # 没有别名
                else:
                    class_info, class_alias = split_line
                    if not ConfigMethod.legal_alias(class_alias):  # 别名不合法
                        return False, (line_number, line_real, 'Alias is illegal')

                # <T(s)>, T(s), <T(S)>
                is_success, class_split = ConfigMethod.split_alias(class_info)
                if not is_success:
                    return False, (line_number, line_real, class_split)

                class_name, alias_name = class_split
                class_key = class_name, class_alias

                # 新建类，<T>, <T -> t>, <T(S) -> t>, <T(S(s), t1) -> t2>
                if space == 0:
                    nest_key = class_key

                    if class_key in nest_class:  # 类重复定义
                        return False, (line_number, line_real, 'Class can not redefine')

                    # 类定义需要在继承类之前（或者为外部类）
                    for inherit_set in nest_inherit.values():
                        if class_key in inherit_set:
                            return False, (line_number, line_real, 'Class must define before inherit')

                    # 类定义需要在使用类之前
                    for nest_set in nest_class.values():
                        if class_key in nest_set:
                            return False, (line_number, line_real, 'Class must define before use')

                    if alias_name == ConfigMethod.BASE_ALIAS:  # 没有继承
                        if class_alias == ConfigMethod.BASE_ALIAS:  # <T>, 类没有定义
                            if not ConfigMethod.class_type(class_name, sconfig, config):
                                return False, (line_number, line_real, 'Class not exist')
                            operate_type = 'baseclass'
                            data = None
                        else:  # <T -> t>
                            operate_type = 'aliasclass'
                            data = class_alias
                    else:  # 使用继承关系生成类
                        # 已有的类不能重新生成（防止一些定义冲突）
                        if ConfigMethod.class_type(class_name, sconfig, config) in ('plugins', 'globals'):
                            return False, (line_number, line_real, 'Class is redefine in plugins or globals')
                        cls_list = []
                        for cls_name in ConfigMethod.strip_split(alias_name, ','):
                            if ConfigMethod.is_alias(cls_name):  # 引用自身的别名，<T(t)> => <T(T(t))>
                                cls_split = (class_name, cls_name)
                            else:
                                is_success, cls_split = ConfigMethod.split_alias(cls_name)
                                if not is_success:
                                    return False, (line_number, line_real, cls_split)
                            cls_name, cls_alias_name = cls_split
                            if cls_alias_name != ConfigMethod.BASE_ALIAS:
                                if cls_split not in nest_class:  # 未定义的类不能使用别名引用
                                    return False, (line_number, line_real, 'Alias must exist')

                            cls_list.append(cls_split)

                        # 新建的类有继承关系
                        nest_inherit[class_key] = set(cls_list)  # 先放进去可以判断继承自身
                        if not ConfigMethod.is_inherit(nest_inherit, class_key, set(cls_list)):
                            return False, (line_number, line_real, 'Class inherit is nested')

                        # 使用cls_list创建名称为class_name的新类
                        operate_type = 'newclass'
                        data = cls_list

                    # 类尚未新建，没有子节点的类也需要统计，不能用setdefault
                    if class_key not in nest_class:
                        nest_class[class_key] = set()
                else:  # 别名查找类，T(t1) -> t2
                    # T(t1) -> t2，class_split相当于(T, t1)，class_key相当于(T, t2)
                    if class_split == nest_key:  # 类内部不能使用自身
                        return False, (line_number, line_real, 'Class can not use when define')

                    nest_class[nest_key].add(class_split)
                    if class_alias != ConfigMethod.BASE_ALIAS:  # 统计子节点的别名
                        cite_class.setdefault(nest_key, {})
                        if class_alias in cite_class[nest_key]:  # 同一个根类中的别名不能重复
                            return False, (line_number, line_real, 'Alias can not same')
                        cite_class[nest_key][class_alias] = line_number  # class_split

                    if not ConfigMethod.legal_alias(alias_name):  # 别名索引不合法
                        return False, (line_number, line_real, 'Alias is illegal')
                    if alias_name != ConfigMethod.BASE_ALIAS:
                        if class_split not in nest_class:  # 未定义的类不能使用别名引用
                            return False, (line_number, line_real, 'Alias must exist')

                    # 查找class_name类中别名为alias_name的子类
                    operate_type = 'findclass'
                    data = alias_name

                process_data.append((line_number, operate_type, space, nest_key, class_name, class_alias, data))
                cursor_line = line_number
                attr_space = space + 1

            line_map[line_number] = line_real

        nest_line = {}  # 节点和行数的对应关系，{12: node1, 13: node2}
        nest_root = {}  # 根节点对应的行数，{T-t: 12, S-s: 13}
        cursor_node = root  # 当前节点
        cursor_space = -1
        for line in process_data:
            line_number, operate_type, space, nest_key, class_name, class_alias, data = line
            line_real = line_map[line_number]
            if operate_type in ('baseclass', 'aliasclass', 'newclass'):
                class_real_name = ConfigMethod.real_name(class_name, class_alias)
                nest_root[class_real_name] = line_number
            elif operate_type == 'findclass':
                class_real_name = ConfigMethod.real_name(class_name, data)

            class_attr = {}  # 需要继承的属性
            class_base = []  # 需要继承的类
            if operate_type in ('newclass', 'findclass'):
                if operate_type == 'newclass':  # <T(S)>, <T(S) -> t>
                    cls_list = [ConfigMethod.real_name(cls_name, cls_alias) for cls_name, cls_alias in data]
                    base_type = {cls_name: ConfigMethod.class_type(cls_name, sconfig, config) for cls_name in cls_list}
                elif operate_type == 'findclass':  # T(t) -> r
                    base_type = {class_real_name: ConfigMethod.class_type(class_real_name, sconfig, config)}

                for cls_name, cls_type in base_type.items():
                    if not cls_type:  # 父类不存在
                        return False, (line_number, line_real, 'Base class not exist')

                for cls_name, cls_type in base_type.items():  # 新建配置类不直接使用外部类，防止不必要的初始化
                    cls = ConfigMethod.get_class(cls_name, config)
                    if not cls:  # 不考虑插件类和外部类
                        continue
                    class_base.append(cls)
                    class_attr.update(cls.class_attr)
            elif operate_type not in ('baseclass', 'aliasclass'):  # <T>, <T -> t>
                return False, (line_number, line_real, 'Operate type error')

            try:  # 创建节点
                ids = dict(cite_class.get(nest_key, {}))
                # 类中可以使用的索引序列，先用行号索引，再替换成对应节点，用字典保证相同nest_key对应的节点为同一个
                attr = cite_cursor.get(line_number, {})  # 类中的属性
                for k, v in attr.items():
                    linen, liner, linec, note, expr = v

                    # 检查注解中的类是否存在
                    if 'other' in note and note['other'] not in set(config['node']) | sconfig['plugins']:
                        return False, (linen, liner, 'Attr note not exist')
                    # 当前行号，检查标志，表达式解析结果
                    class_attr[k] = linen, note, 'uncheck', ConfigMethod.analyse(expr, ids.keys())  # 默认添加self, root

                ids['self'] = line_number
                node = ConfigNode(class_real_name, ids)

                node.class_attr = class_attr
                node.class_base = class_base

                # class_attr中除了_ids都需要继承，类自身的变量在实例化时判断，暂不考虑
                if operate_type in ('baseclass', 'aliasclass', 'newclass'):  # 需要新建的类（根类）
                    config['node'][class_real_name] = node
                else:
                    base_ids = {}
                    for base in node.class_base:
                        base_ids.update(base.ids)
                    check_ids = set(base_ids) & set(ids) - set(('root', 'self'))
                    if check_ids:  # 别名存在于根类中
                        return False, (line_number, line_real, 'Alias already in base class')
            except Exception:
                Log.exception()
                return False, (line_number, line_real, 'Create class failed')

            try:  # 查找父节点
                parent = cursor_node
                if space != cursor_space + 1:
                    parent = cursor_node
                    for _ in range(cursor_space - space + 1):
                        parent = parent.parent

                parent.add_node(node)
            except Exception:
                Log.exception()
                return False, (line_number, line_real, 'Add class failed')

            try:  # 查找根节点
                rootnode = node
                while rootnode.parent.parent:
                    rootnode = rootnode.parent
                node._ids['root'] = nest_root[rootnode.name]
            except Exception:
                Log.exception()
                return False, (line_number, line_real, 'Get root class failed')

            nest_line[line_number] = node
            cursor_node = node
            cursor_space = space

        # 将索引从行号替换成对应节点，不遍历基类的子节点
        for node, deep in root.walk(isroot=False):
            for ids_key, ids_line in node._ids.items():
                node._ids[ids_key] = nest_line.get(ids_line)
            # for attr_key, attr_val in node.class_attr.items():
            #     line_number, attr_line, attr_note, attr_check, attr = attr_val
            #     node.class_attr[attr_key] = line_number, nest_line.get(attr_line), attr_note, attr_check, attr

        # 通过索引序列解析属性
        for node, deep in root.walk(isroot=False):
            for name in node.class_attr.keys():
                line_number, attr_note, attr_check, attr = node.class_attr[name]
                line_real = line_map[line_number]

                # 以safe注解为准，未设置则使用默认safe配置
                safe = attr_note.get('safe', 'unsafe' if self.unsafe else 'safe')
                # 继承后属性未被覆盖则使用继承前的属性进行计算
                if not node.execute(name) and safe == 'safe':
                    return False, (line_number, line_real, 'Attr is unsafe')

                line_number, attr_note, attr_check, attr = node.class_attr[name]
                if attr_check == 'uncheck':  # uncheck字段不进行检查
                    continue

                # 设置了state注解才进行检查
                if 'state' in attr_note and attr_check != attr_note['state']:
                    return False, (line_number, line_real, 'Attr state is incorrect')

                # 设置了type注解才进行检查
                if 'type' in attr_note and attr[0].__class__.__name__ != attr_note['type']:
                    return False, (line_number, line_real, 'Attr type is incorrect')

                # if 'other' in attr_note:
                #     print(attr[0].__class__.__name__)

                # 动态属性添加触发器
                if attr_check == 'dynamic':
                    node.add_trigger(attr, attr_note)

        return True, (root, config)

    def create_class(self, root, sconfig, config):
        """创建新的类."""
        for node, _ in root.walk(isroot=False):
            print(node._trigger, node._reflex)

        def check_parent_class(base, deep=0):
            if deep > 32:  # 类层级太多或者循环继承
                return False
            if base == Node:
                return True
            if base == object:
                return False
            for b in base.__bases__:
                if check_parent_class(b, deep + 1):
                    return True
            return False

        # 导入全局变量
        for node_name in config['newclass'].keys():
            if ConfigMethod.CLASS_SPLIT in node_name:
                continue

            # 插件类或外部类，将类与节点绑定，类初始化时按照配置树的结构初始类的成员变量
            if node_name in globals():
                node_type = globals()[node_name]
            elif node_name in sconfig['plugins']:
                node_type = sconfig['plugins'][node_name]

            # 根据的父类和属性重新生成类
            base_list = []
            for base in node_type.__bases__:
                if base == object:
                    continue
                base_list.append(base)
            if not check_parent_class(node_type):  # 父类中不存在Node节点
                base_list.append(Node)

            base_attr = dict(node_type.__dict__)
            base_attr['_config'] = node_name, root, sconfig, config
            globals()[node_name] = type(node_name, tuple(base_list), base_attr)

    def load(self, data):
        """从文件或字符串中加载配置."""
        sconfig = {
            'globals': globals(),
            'plugins': Manager.plugins,  # 已有的插件类
        }

        try:
            if '\n' not in data or '\r' not in data:  # 字符串
                with open(data, 'r', encoding='utf-8') as fp:
                    data = fp.read()
            data = data.replace('\r\n', '\n').replace('\n\r', '\n').replace('\r', '\n')  # 分割后再替换
            lines = data.split('\n')
            is_success, info = self._load(lines, sconfig)
            if not is_success:
                line_number, line_real, message = info
                Log.error('{} {} {}'.format(line_number, line_real, message))
                return None
            root, config = info
        except Exception:
            Log.exception()
            return None

        # self.create_class(root, sconfig, config)
        return root


if __name__ == '__main__':
    class TestWidget:
        """TestWidget."""

        pass

    class TestWidget05:
        """TestWidget05."""

        def __init__(self):
            """__init__."""
            print('init')

        def testwidget05(self):
            """testwidget05."""
            pass
    TestWidget05.__name__ = 'abc'

    Manager.auto_load()
    config = Config()
    tree = config.load('config/testconfig.pv')
    # tree.show()
    # print(tree.children[2].name)
    # tree.children[1].children[0].name = 'xc'
    # root.show()
    # print(tree.children[2].name)

    tw1 = TestWidget05()
