# Copyright (c) 2015-2017 Chris Withers
# See README.rst for license details.

import os
from setuptools import setup, find_packages

base_dir = os.path.dirname(__file__)

setup(
    name='mortar_import',
    author='Chris Withers',
    version='0.12.0',
    author_email='chris@withers.org',
    license='MIT',
    description="Tools for importing data, particularly when using mortar_mixins",
    long_description=open(os.path.join(base_dir, 'README.rst')).read(),
    url='https://github.com/Mortar/mortar_import',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=['six'],
    extras_require=dict(
        test=['nose', 'nose-cov','testfixtures', 'coveralls', 'mortar_mixins',
              'mock'],
        build=['setuptools-git', 'wheel', 'twine']
        ),
    )

