from unittest import TestCase

from mortar_import.extractors import MultiKeyDictExtractor
from mortar_import.sqlalchemy import SQLAlchemyDiff
from mortar_mixins import Common
from mortar_rdb import get_session
from mortar_rdb.testing import register_session
from sqlalchemy import Column, Integer
from sqlalchemy import String
from sqlalchemy.ext.declarative import declarative_base
from testfixtures import ShouldRaise, compare

Base = declarative_base()


class Simple(Base):
    __tablename__ = 'simple'
    key = Column(String, primary_key=True)
    value = Column(Integer)


class MultiPK(Base):
    __tablename__ = 'multi_pk'
    name = Column(String, primary_key=True)
    index = Column(Integer, primary_key=True)
    value = Column(String)


class CommonMixedIn(Common, Base):
    key = Column(String, primary_key=True)
    value = Column(String)


class TestSQLAlchemy(TestCase):

    def setUp(self):
        register_session(transactional=False)
        self.session = get_session()
        self.addCleanup(self.session.rollback)
        Base.metadata.create_all(self.session.bind)

    def test_abstract(self):
        with ShouldRaise(TypeError(
                "Can't instantiate abstract class SQLAlchemyDiff with "
                "abstract methods extract_imported"
        )):
            SQLAlchemyDiff([], [])

    def test_simple(self):
        self.session.add(Simple(key='a', value=1))
        self.session.add(Simple(key='b', value=2))
        self.session.add(Simple(key='c', value=3))

        imported = [
            dict(key='b', value=2),
            dict(key='c', value=4),
            dict(key='d', value=5),
        ]

        class TestDiff(SQLAlchemyDiff):

            def __init__(self, session, imported):
                existing = session.query(Simple)
                super(TestDiff, self).__init__(
                    session, Simple, existing, imported
                )

            extract_imported = MultiKeyDictExtractor('key')

        diff = TestDiff(self.session, imported)

        diff.apply()

        expected = [
            dict(key='b', value=2),
            dict(key='c', value=4),
            dict(key='d', value=5),
        ]

        actual = [dict(key=o.key, value=o.value)
                  for o in self.session.query(Simple).order_by('key')]

        compare(expected, actual)
