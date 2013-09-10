#!/usr/bin/env python

import os

from setuptools import setup


def readreq(filename):
    result = []
    with open(filename) as f:
        for req in f:
            req = req.partition('#')[0].strip()
            if not req:
                continue
            result.append(req)
    return result


def readfile(filename):
    with open(filename) as f:
        return f.read()


setup(
    name='cli_tools',
    version='0.2.2',
    author='Kevin L. Mitchell',
    author_email='klmitch@mit.edu',
    description="Command Line Interface Tools",
    py_modules=['cli_tools'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 or '
        'later (GPLv3+)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: User Interfaces',
    ],
    url='https://github.com/klmitch/cli_utils',
    long_description=readfile('README.rst'),
    install_requires=readreq('.requires'),
    tests_require=readreq('.test-requires'),
)
