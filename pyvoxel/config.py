# -*- coding: utf-8 -*-
try:
    from xml.etree import cElementTree as ElementTree
except:
    from xml.etree import ElementTree

class Config(object):
    def __init__(self):
        #tree = ElementTree.parse('config/testconfig.xml')
        #root = tree.getroot()
        with open('config/testconfig.xml', 'r') as fp:
            lines = fp.readlines()
            for line in lines:
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
                    break
                
                space = int(space / 4)
                
                print(space, line)


if __name__ == '__main__':
    Config()
