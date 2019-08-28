#!/usr/bin/env python

from setuptools import setup, find_packages

__author__ = "Jordan Ovrè <ghecko78@gmail.com>"

description = 'Hydrabus Framework baudrate detection module'
name = 'hbfmodules.uart.baudrates'
setup(
    name=name,
    version='0.0.1',
    packages=find_packages(),
    license='GPLv3',
    description=description,
    author=__author__,
    url='https://github.com/hydrabus-framework/' + name,
    install_requires=[
        'tabulate'
    ],
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3',
        'Development Status :: 3 - Alpha'
    ],
    keywords=['hydrabus', 'framework', 'hardware', 'security', 'baudrates', 'uart']
)
