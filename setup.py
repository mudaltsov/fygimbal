#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name="FY-Gimbal",
    version="0.1",
    packages=find_packages(),
    scripts=['fypoke.py'],

    author="Micah Scott",
    author_email="micah@misc.name",
    description="Talking to the Feiyu Tech gimbals over serial",
    license="MIT",
)
