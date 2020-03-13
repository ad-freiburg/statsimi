from setuptools import setup, find_packages, Extension

cutil = Extension('cutil', sources=['cutil/cutilmodule.c'])

setup(name='staty',
      packages=find_packages(),
      ext_modules=[cutil]
)
