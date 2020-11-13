from setuptools import setup, find_packages, Extension
import os

cutil = Extension('cutil', sources=['cutil/cutilmodule.c'])

cwd = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(cwd, 'README.md')) as df:
    DESC = df.read()

with open(os.path.join(cwd, 'requirements.txt')) as rf:
    install_requires = rf.read()

setup(
    name='statsimi',
    author='Patrick Brosi',
    author_email='brosi@cs.uni-freiburg.de',
    url="https://github.com/ad-freiburg/statsimi",
    long_description=DESC,
    long_description_content_type='text/markdown',
    version='0.0.1',
    packages=find_packages(),
    license='GPLv3',
    test_suite="statsimi.test_doctests",
    ext_modules=[cutil],
    setup_requires=['wheel'],
    install_requires=install_requires,
    include_package_data = True,
    entry_points={
        'console_scripts': [
            'statsimi = statsimi:main',
        ]
    }
)
