#!/usr/bin/env python
# coding: utf-8
from setuptools import setup
setup(
    name="xml-compare",
    version='0.1',
    description='Compare two xml files for equality or compatibility',
    scripts=['xml_compare.py'],
    install_requires=[
        'lxml>=3.3.1',
    ],
    zip_safe=False,
    author='Nikita Kovalev',
    author_email='nikita@maizy.ru',
    url='https://github.com/maizy/xml-compare',
)
