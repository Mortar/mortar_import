import pytest
from mortar_mixins.testing import connection_in_transaction


@pytest.fixture(scope='session')
def db():
    with connection_in_transaction() as conn:
        yield conn
