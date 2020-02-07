#!/usr/bin/env python
  
from setuptools import setup

setup(
    name='yoshiki',
    version='0.0.1',
    packages=['yoshiki'],
    entry_points={
        'console_scripts': [
            'yoshiki=yoshiki.main:main',
        ]
    }
)

