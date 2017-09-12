# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

from googleads_requests import __version__


setup(
    name='googleads-requests',
    version=__version__,
    packages=find_packages(),
    # suds_requests cannot be added here, as it refers to suds, conflicting with suds-jurko
    install_requires=['requests', 'googleads>=7.0.0'],
    url='https://github.com/Precis/googleads-requests',
    license='MIT',
    author='Matthias Erll',
    author_email='matthias@precisdigital.com',
    description='Python Requests for Google AdWords API client and utilities.'
)
