from setuptools import find_packages, setup

setup(
    name='AsyncEVM',
    packages=find_packages(include=['AsyncEVM']),
    version='0.1.0',
    description='AsyncEVM is a python package for Ethereum Virtual Machine',
    author='Krittipat Krittakom',
    install_requires=['web3',
                      'pandas',
                      'python-dotenv'],
)