from setuptools import find_packages, setup

setup(
    name='EVM',
    packages=find_packages(include=['EVM']),
    version='1.0.0',
    description='EVM is a python package for Ethereum Virtual Machine',
    author='Krittipat Krittakom',
    install_requires=['web3',
                      'pandas',
                      'python-dotenv'],
)