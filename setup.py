#!/usr/bin/env python2.7

from setuptools import setup

setup(
    name='orz',
    version='0.0',

    url='https://github.com/xiazheteng/orz',
    description='porting programming languages to CPython VM',

    classifiers = [
        "Development Status :: 1 - Planning",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.7",
        "Topic :: Software Development :: Compilers",
    ],

    install_requires = ['ply'],

    packages=['orz', 'orz.lua', 'orz.lua.runtime'],
)
