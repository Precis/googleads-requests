# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

from googleads_requests import __version__


setup(
    name='googleads-requests',
    version=__version__,
    packages=find_packages(),
    install_requires=['requests', 'googleads'],
    dependency_links=['git+https://github.com/Precis/googleads-python-lib.git@precis#egg=googleads'],
    url='https://github.com/Precis/googleads-requests',
    license='MIT',
    author='Matthias Erll',
    author_email='matthias@precisdigital.com',
    description='Requests implementations of Google AdWords client utilities.'
)
