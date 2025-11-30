#!/usr/bin/env python3
"""Setup script for CRISK CLI."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="crisk",
    version="0.1.0",
    author="CodeRisk",
    author_email="hello@coderisk.dev",
    description="Change Risk Analysis CLI - Find impacted files and notify owners",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/rohankatakam/fasho.ski",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Version Control :: Git",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
    ],
    entry_points={
        "console_scripts": [
            "crisk=crisk.cli:main",
        ],
    },
)
