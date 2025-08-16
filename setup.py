#!/usr/bin/env python
try:
    import os
    import platform
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup

# 根據操作系統設置依賴
install_requires = []

if platform.system() == 'Windows':
    install_requires.append('comtypes')
elif platform.system() == 'Darwin':  # macOS
    install_requires.extend(['pyobjc-core', 'pyobjc-framework-CoreWLAN'])

setup(
    name='pywifi',
    version='1.1.9',
    author='Jiang Sheng-Jhih',
    author_email='shengjhih@gmail.com',
    description="A cross-platform module for manipulating WiFi devices.",
    packages=find_packages(),
    install_requires=install_requires,
    url='https://github.com/awkman/pywifi', 
    license='MIT',
    download_url='https://github.com/awkman/pywifi/archive/master.zip', 
    classifiers=[
        'Intended Audience :: Developers',
        'Topic :: Utilities',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 2.7',
    ],
    keywords=['wifi', 'wireless', 'Linux', 'Windows', 'macOS'], 
)
