from setuptools import setup, find_packages, Extension
import os

cutil = Extension('cutil', sources=['cutil/cutilmodule.c'])

cwd = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(cwd, 'README.md')) as df:
    DESC = df.read()

with open(os.path.join(cwd, 'requirements.txt')) as rf:
    install_requires = rf.read()

print(find_packages())

setup(
    name='statsimi',
    author='Patrick Brosi',
    author_email='brosi@cs.uni-freiburg.de',
    url="https://github.com/ad-freiburg/statsimi",
    long_description=DESC,
    long_description_content_type='text/markdown',
    packages=find_packages(),
    ext_modules=[cutil],
    install_requires=install_requires,
    entry_points={
        'console_scripts': [
            'statsimi = statsimi:main',
        ]
    }
)
