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
    (): 在非根类中通过不同的别名使用根类
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

    #判断别名是否合法
    def _legal_alias(self, alias_name):
        if not alias_name:
            return False
        for s in alias_name:
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
        class_map = {}
        base_class = '' #当前行所在最顶层的类
        base_alias = []
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
                
                if class_info.endswith(')'):
                    class_info = class_info[:-1]

                    split_line = self._strip_split(class_info, '(', 1)
                    if len(split_line) == 1:
                        print('No ( find')
                        return False
                    
                    class_name, alias_name = split_line
                    if not self._legal_class(class_name): #类命不合法
                        print('Class is illegal', class_name)
                        return False

                    if not alias_name: #括号里为空
                        print('Alias is empty')
                        return False

                    #新建类使用了别名，默认值设为该别名
                    if space == 0: #新建类不能使用别名索引
                        cls_list = self._strip_split(alias_name, ',')
                        for cls_name in cls_list:
                            if not self._legal_class(cls_name): #类命不合法
                                print('Class is illegal', cls_name)
                                return False
                        #使用cls_list创建名称为class_name的新类
                        operate_type = 'newclass'
                        data = cls_list
                    else: #别名查找类
                        if not self._legal_alias(alias_name): #别名索引不合法
                            print('Alias is illegal')
                            return False
                        #查找class_name类中别名为alias_name的子类
                        operate_type = 'aliasclass'
                        data = alias_name
                else:
                    class_name = class_info
                    if not self._legal_class(class_name): #类命不合法
                        print('Class is illegal', class_name)
                        return False
                    #普通查找class_name类
                    operate_type = 'findclass'
                    data = None
                
                if space == 0:
                    #新建类
                    if class_name not in class_map: #类尚未新建
                        class_map[class_name] = {}
                        class_map[class_name][self.BASE_ALIAS] = None
                    elif operate_type == 'newclass': #新建类之前不能有该类的其他定义
                        print('New class must be first')
                        return False
                    elif class_alias in class_map[class_name]: #别名相同
                        print('Class can not redefine', class_name, class_alias)
                        return False
                    class_map[class_name][class_alias] = None

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
                print(class_name, class_alias)
                if operate_type == 'newclass':
                    cls_list = line[1]

                node = Node(class_name, space)
                if space == cursor_node.space + 1:
                    cursor_node.add_node(node)
                else:
                    parent = cursor_node.prev(space - cursor_node.space)
                    parent.add_node(node)

                cursor_node = node
        self.root.show()
        #print(node_dict)


if __name__ == '__main__':
    Manager.auto_load()
    Config()
