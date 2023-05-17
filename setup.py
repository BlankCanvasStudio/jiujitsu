#!/usr/bin/env python

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="jiujitsu",
    version="0.5",
    author="Spencer Stingley",
    author_email="sstingle@usc.edu",
    description="A custom bash interpreter for malware execution",
    long_description="A custom bash interpreter for malware execution",
    long_description_content_type="text/markdown",
    url="https://github.com/BlankCanvasStudio/jiujitsu",
    packages=setuptools.find_packages(),
    entry_points={
        'console_scripts': [
            'jj = jiujitsu.jInterpreter:main',
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires = '>=3.6',
    install_requires=['bashlex', 'bashparser'],
    test_suite='nose.collector',
    tests_require=['nose'],
)
