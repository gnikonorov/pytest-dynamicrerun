#!/usr/bin/env python
import codecs
import os

from setuptools import setup


def read(fname):
    file_path = os.path.join(os.path.dirname(__file__), fname)
    return codecs.open(file_path, encoding="utf-8").read()


setup(
    name="pytest-dynamicrerun",
    version="1.0.6",
    author="Gleb Nikonorov",
    author_email="gleb.i.nikonorov@gmail.com",
    maintainer="Gleb Nikonorov",
    maintainer_email="gleb.i.nikonorov@gmail.com",
    license="MIT",
    url="https://github.com/gnikonorov/pytest-dynamicrerun",
    description="A pytest plugin to rerun tests dynamically based off of test outcome and output.",
    long_description=read("README.rst"),
    py_modules=["pytest_dynamicrerun"],
    python_requires=">=3.5",
    install_requires=["pytest>=5.4.0", "croniter==0.3.34"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: Pytest",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
    ],
    entry_points={"pytest11": ["dynamicrerun = pytest_dynamicrerun"]},
)
