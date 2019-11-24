# -*- coding: utf-8 -*-
import os
import shutil
from setuptools import setup, find_packages, Command

class Clean(Command):
    user_options = []
    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def remove(self, remove_list):
        for name in remove_list:
            if not os.path.exists(name):
                continue
            shutil.rmtree(name)

    def run(self):
        self.remove(['build', 'dist', 'pyvoxel.egg-info'])

setup(
    name = 'pyvoxel',
    version = '0.1',
    description = '',
    author = 'zx013',
    url = 'https://github.com/zx013/pyvoxel',
    license = 'MIT',
    keywords = ['voxel'],
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3'
    ],
    packages = find_packages(),
    python_requires = '>=3.5',
    setup_requires = [
        'panda3d'
    ],
    install_requires = [
        #'panda3d>=1.10.4.1'
    ],
    cmdclass = {
        'clean': Clean,
    },
    zip_safe = False
)