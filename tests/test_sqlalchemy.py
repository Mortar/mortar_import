from unittest import TestCase

from mortar_import.diff import Addition, Update, Deletion
from mortar_import.extractors import MultiKeyDictExtractor
from mortar_import.sqlalchemy import SQLAlchemyDiff
from mortar_rdb import get_session
from mortar_rdb.testing import register_session
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from testfixtures import ShouldRaise, compare

Base = declarative_base()


class Simple(Base):
    __tablename__ = 'simple'
    key = Column(String, primary_key=True)
    value = Column(Integer, unique=True)


class MultiPK(Base):
    __tablename__ = 'multi_pk'
    name = Column(String, primary_key=True)
    index = Column(Integer, primary_key=True)
    value = Column(Integer)


class AutoPK(Base):
    __tablename__ = 'auto_pk'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    value = Column(Integer)


class FKToSimple(Base):
    __tablename__ = 'simple_referrer'
    name = Column(String, primary_key=True)
    value = Column(String, ForeignKey('simple.key'))
    simple = relationship("Simple")


class TestSQLAlchemy(TestCase):

    def setUp(self):
        register_session(transactional=False)
        self.session = get_session()
        self.addCleanup(self.session.rollback)
        Base.metadata.create_all(self.session.bind)

    def test_abstract(self):
        with ShouldRaise(TypeError(
                "Can't instantiate abstract class SQLAlchemyDiff with "
                "abstract methods extract_imported, model"
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
            model = Simple
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

    def test_order_matters_no_type_flush(self):
        self.session.add(Simple(key='a', value=2))
        self.session.add(Simple(key='b', value=1))

        imported = [
            dict(key='b', value=2),
            dict(key='d', value=1),
        ]

        class TestDiff(SQLAlchemyDiff):
            model = Simple
            extract_imported = MultiKeyDictExtractor('key')
            flush_per_type = False

        diff = TestDiff(self.session, imported)
        diff.apply()

        with ShouldRaise(IntegrityError):
            self.session.flush()

    def test_order_matters_type_flush(self):
        self.session.add(Simple(key='a', value=2))
        self.session.add(Simple(key='b', value=1))

        imported = [
            dict(key='b', value=2),
            dict(key='d', value=1),
        ]

        class TestDiff(SQLAlchemyDiff):
            model = Simple
            extract_imported = MultiKeyDictExtractor('key')

        diff = TestDiff(self.session, imported)

        diff.apply()

        expected = [
            dict(key='b', value=2),
            dict(key='d', value=1),
        ]

        actual = [dict(key=o.key, value=o.value)
                  for o in self.session.query(Simple).order_by('key')]

        compare(expected, actual)

    def test_multi_column_primary_key(self):
        self.session.add(MultiPK(name='a', index=0, value=1))
        self.session.add(MultiPK(name='b', index=0, value=2))
        self.session.add(MultiPK(name='b', index=1, value=-2))
        self.session.add(MultiPK(name='c', index=0, value=3))

        imported = [
            dict(name='b', index=0, value=2),
            dict(name='b', index=2, value=-1),
            dict(name='c', index=0, value=4),
            dict(name='d', index=0, value=5),
        ]

        class TestDiff(SQLAlchemyDiff):
            model = MultiPK
            extract_imported = MultiKeyDictExtractor('name', 'index')

        diff = TestDiff(self.session, imported)

        diff.apply()

        expected = [
            dict(name='b', index=0, value=2),
            dict(name='b', index=2, value=-1),
            dict(name='c', index=0, value=4),
            dict(name='d', index=0, value=5),
        ]

        actual = [dict(name=o.name, index=o.index, value=o.value)
                  for o in self.session.query(MultiPK).order_by('name')]

        compare(expected, actual)

    def test_partial_table_contents(self):
        self.session.add(MultiPK(name='a', index=0, value=1))
        self.session.add(MultiPK(name='b', index=0, value=2))
        self.session.add(MultiPK(name='c', index=0, value=3))
        self.session.add(MultiPK(name='a', index=1, value=4))
        self.session.add(MultiPK(name='b', index=1, value=5))
        self.session.add(MultiPK(name='c', index=1, value=6))

        imported = [
            dict(name='b', index=0, value=2),
            dict(name='c', index=0, value=7),
            dict(name='d', index=0, value=8),
        ]

        class TestDiff(SQLAlchemyDiff):

            model = MultiPK
            extract_imported = MultiKeyDictExtractor('name')

            def existing(self):
                return self.session.query(MultiPK).filter_by(index=0)

        diff = TestDiff(self.session, imported)

        diff.apply()

        expected = [
            dict(name='b', index=0, value=2),
            dict(name='c', index=0, value=7),
            dict(name='d', index=0, value=8),
            dict(name='a', index=1, value=4),
            dict(name='b', index=1, value=5),
            dict(name='c', index=1, value=6),
        ]

        actual = [
            dict(name=o.name, index=o.index, value=o.value)
            for o in self.session.query(MultiPK).order_by('index', 'name')
        ]

        compare(expected, actual)

    def test_auto_id(self):
        deleted = AutoPK(name='a', value=1)
        self.session.add(deleted)
        self.session.add(AutoPK(name='b', value=2))
        existing = AutoPK(name='c', value=3)
        self.session.add(existing)

        imported = [
            dict(name='b', value=2),
            dict(name='c', value=4),
            dict(name='d', value=5),
        ]

        class TestDiff(SQLAlchemyDiff):

            model = AutoPK
            extract_imported = MultiKeyDictExtractor('name')
            ignore_fields = {'id'}

            def extract_existing(self, obj):
                _, extracted = super(TestDiff, self).extract_existing(obj)
                key = (extracted['name'], )
                return key, extracted

        diff = TestDiff(self.session, imported)

        diff.compute()

        compare(diff.to_add, [
            Addition(key=('d',),
                     imported={'name': 'd', 'value': 5},
                     imported_extracted={'name': 'd', 'value': 5})
        ])
        compare(diff.to_update, [
            Update(key=('c',),
                   existing=existing,
                   existing_extracted={'value': 3, 'name': 'c'},
                   imported={'value': 4, 'name': 'c'},
                   imported_extracted={'value': 4, 'name': 'c'})
        ])
        compare(diff.to_delete, [
            Deletion(key=('a',),
                     existing=deleted,
                     existing_extracted={'name': 'a', 'value': 1})
        ])

        diff.apply()

        expected = [
            dict(name='b', value=2),
            dict(name='c', value=4),
            dict(name='d', value=5),
        ]

        actual = [
            dict(name=o.name, value=o.value)
            for o in self.session.query(AutoPK).order_by('name', 'value')
        ]

        compare(expected, actual)

    def test_foreign_keys(self):
        s1 = Simple(key='s1', value=3)
        s2 = Simple(key='s2', value=4)
        self.session.add_all((s1, s2))
        deleted = FKToSimple(name='a', simple=s1)
        changed = FKToSimple(name='b', simple=s1)
        existing = FKToSimple(name='c', simple=s1)
        self.session.add_all((deleted, changed, existing))

        imported = [
            dict(name='b', value='s2'),
            dict(name='c', value='s1'),
            dict(name='d', value='s2'),
        ]

        class TestDiff(SQLAlchemyDiff):

            model = FKToSimple
            extract_imported = MultiKeyDictExtractor('name')

        diff = TestDiff(self.session, imported)

        diff.compute()

        compare(diff.to_add, [
            Addition(key=('d',),
                     imported={'name': 'd', 'value': 's2'},
                     imported_extracted={'name': 'd', 'value': 's2'})
        ])
        compare(diff.to_update, [
            Update(key=('b',),
                   existing=changed,
                   existing_extracted={'value': 's1', 'name': 'b'},
                   imported={'value': 's2', 'name': 'b'},
                   imported_extracted={'value': 's2', 'name': 'b'})
        ])
        compare(diff.to_delete, [
            Deletion(key=('a',),
                     existing=deleted,
                     existing_extracted={'name': 'a', 'value': 's1'})
        ])

        diff.apply()

        expected = [
            dict(name='b', value='s2'),
            dict(name='c', value='s1'),
            dict(name='d', value='s2'),
        ]

        actual = [
            dict(name=o.name, value=o.value)
            for o in self.session.query(FKToSimple).order_by('name', 'value')
        ]

        compare(expected, actual)
