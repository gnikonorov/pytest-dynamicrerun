#!/usr/bin/env python
import codecs
import os

from setuptools import setup


def read(fname):
    file_path = os.path.join(os.path.dirname(__file__), fname)
    return codecs.open(file_path, encoding="utf-8").read()


setup(
    name="pytest-dynamicrerun",
    version="0.1.0",
    author="Gleb Nikonorov",
    author_email="gleb.i.nikonorov@gmail.com",
    maintainer="Gleb Nikonorov",
    maintainer_email="gleb.i.nikonorov@gmail.com",
    license="MIT",
    url="https://github.com/gnikonorov/pytest-dynamicrerun",
    description="A pytest plugin to pause test execution for a dynamic amount of time",
    long_description=read("README.rst"),
    py_modules=["pytest_dynamicrerun"],
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*",
    install_requires=["pytest>=3.5.0", "croniter==0.3.34"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: Pytest",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
    ],
    entry_points={"pytest11": ["dynamicrerun = pytest_dynamicrerun"]},
)
