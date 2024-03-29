# Copyright (c) 2015 onwards Chris Withers
# See README.rst for license details.

import os
from setuptools import setup, find_packages

base_dir = os.path.dirname(__file__)

setup(
    name='mortar_import',
    author='Chris Withers',
    version='0.12.1',
    author_email='chris@withers.org',
    license='MIT',
    description="Tools for importing data, particularly when using mortar_mixins",
    long_description=open(os.path.join(base_dir, 'README.rst')).read(),
    url='https://github.com/Mortar/mortar_import',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    python_requires=">=3.7",
    extras_require=dict(
        test=[
            'pytest',
            'pytest-cov',
            'testfixtures',
            'SQLAlchemy<2',
            'mortar_mixins>=3',
            'mock',
        ],
        build=['setuptools-git', 'wheel', 'twine'],
    ),
)
