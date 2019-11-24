# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(
    name = 'pyvoxel',
    version = '0.1',
    description = '',
    author = 'zx013',
    url = 'https://github.com/zx013/pyvoxel',
    license = 'MIT',
    packages = find_packages(),
    python_requires = '>=3.5',
    setup_requires = [
        'panda3d'
    ],
    install_requires = [
        #'panda3d>=1.10.4.1'
    ]
)