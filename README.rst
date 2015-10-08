|Travis|_ |Coveralls|_

.. |Travis| image:: https://api.travis-ci.org/Mortar/mortar_import.png?branch=master
.. _Travis: https://travis-ci.org/Mortar/mortar_import

.. |Coveralls| image:: https://coveralls.io/repos/Mortar/mortar_import/badge.png?branch=master
.. _Coveralls: https://coveralls.io/r/Mortar/mortar_import?branch=master

mortar_import
=============

Tools for importing data, particularly when using mortar_mixins.

Install from PyPI with pip.

Development
-----------

Get a clone of the git repo and then do the following::

  virtualenv .
  bin/pip install -e .[build,test]
  
  sudo -u postgres psql -d postgres -c "create user testuser with password 'testpassword';"
  sudo -u postgres createdb -O testuser testdb
  sudo -u postgres psql -d testdb -c "CREATE EXTENSION btree_gist;"

  export DB_URL=postgres://testuser:testpassword@localhost:5432/testdb
  bin/nosetests --with-cov --cov=mortar_import

Releasing
---------

To make a release, just update the version in ``setup.py``, tag it
and push to https://github.com/Mortar/mortar_import
and Travis CI should take care of the rest.


