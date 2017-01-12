from datetime import datetime as dt
from unittest import TestCase

from mortar_import.extractors import MultiKeyDictExtractor, DictExtractor
from mortar_import.temporal import TemporalDiff
from mortar_mixins import Temporal
from mortar_rdb import get_session
from mortar_rdb.testing import register_session
from psycopg2.extras import DateTimeRange as R
from sqlalchemy import Column, Integer
from sqlalchemy import String
from sqlalchemy.ext.declarative import declarative_base
from testfixtures import ShouldRaise, compare

Base = declarative_base()


class Model(Temporal, Base):
    __tablename__ = 'model'
    key_columns = ('key', 'source')
    key = Column(String)
    source = Column(String, default='')
    value = Column(Integer)


class NoKeys(Temporal, Base):
    __tablename__ = 'no_keys'
    not_key = Column(String)
    value = Column(Integer)


class TestTemporal(TestCase):

    def setUp(self):
        register_session(transactional=False)
        self.session = get_session()
        self.addCleanup(self.session.rollback)
        Base.metadata.create_all(self.session.bind)

    def test_abstract(self):
        with ShouldRaise(TypeError(
                "Can't instantiate abstract class TemporalDiff with "
                "abstract methods model"
        )):
            TemporalDiff([], [])

    def test_normal_set(self):
        active = R(dt(2000, 1, 1), None)
        ended = R(None, dt(2000, 1, 1), bounds='()')
        future = R(dt(3000, 1, 1), None, bounds='()')

        self.session.add(Model(key='a', value=1, period=active))
        self.session.add(Model(key='b', value=2, period=active))
        self.session.add(Model(key='c', value=3, period=active))
        self.session.add(Model(key='x', value=42, period=ended))
        self.session.add(Model(key='y', value=69, period=future))

        imported = [
            dict(key='b', value=2, source=''),
            dict(key='c', value=4, source=''),
            dict(key='d', value=5, source=''),
        ]

        class TestDiff(TemporalDiff):
            model = Model
            # this is here to test is can be explicitly specified ;-)
            extract_imported = MultiKeyDictExtractor('key', 'source')

        diff = TestDiff(self.session, imported, dt(2001, 1, 1))

        diff.apply()

        expected = [
            dict(key='a', value=1, period=R(dt(2000, 1, 1), dt(2001, 1, 1))),
            dict(key='b', value=2, period=active),
            dict(key='c', value=3, period=R(dt(2000, 1, 1), dt(2001, 1, 1))),
            dict(key='c', value=4, period=R(dt(2001, 1, 1), None)),
            dict(key='d', value=5, period=R(dt(2001, 1, 1), None)),
            dict(key='x', value=42, period=ended),
            dict(key='y', value=69, period=future),
        ]

        actual = [dict(key=o.key, value=o.value, period=o.period)
                  for o in self.session.query(Model).order_by('key', 'period')]

        compare(expected, actual)

    def test_partial_table(self):
        active = R(dt(2000, 1, 1), None)

        self.session.add(Model(key='a', value=1, period=active))
        self.session.add(Model(key='b', value=2, period=active))
        self.session.add(Model(key='c', value=3, period=active))
        self.session.add(Model(key='x', value=42, period=active, source='foo'))
        self.session.add(Model(key='y', value=69, period=active, source='foo'))

        imported = [
            dict(key='b', value=2, source=''),
            dict(key='c', value=4, source=''),
            dict(key='d', value=5, source=''),
        ]

        class TestDiff(TemporalDiff):
            model = Model
            def existing(self):
                return super(TestDiff, self).existing().filter_by(source='')

        diff = TestDiff(self.session, imported, dt(2001, 1, 1))

        diff.apply()

        expected = [
            dict(key='a', value=1,
                 period=R(dt(2000, 1, 1), dt(2001, 1, 1)), source=''),
            dict(key='b', value=2,
                 period=active, source=''),
            dict(key='c', value=3,
                 period=R(dt(2000, 1, 1), dt(2001, 1, 1)), source=''),
            dict(key='c', value=4,
                 period=R(dt(2001, 1, 1), None), source=''),
            dict(key='d', value=5,
                 period=R(dt(2001, 1, 1), None), source=''),
            dict(key='x', value=42,
                 period=active, source='foo'),
            dict(key='y', value=69,
                 period=active, source='foo'),
        ]

        actual = [dict(key=o.key, value=o.value,
                       period=o.period, source=o.source)
                  for o in self.session.query(Model).order_by('key', 'period')]

        compare(expected, actual)

    def test_future_rows(self):
        past = R(None, dt(2000, 1, 1), bounds='()')
        active = R(dt(2000, 1, 1), dt(3000, 1, 1))
        future = R(dt(3000, 1, 1), None, bounds='()')

        self.session.add(Model(key='a', value=1, period=past))
        self.session.add(Model(key='a', value=2, period=active))
        self.session.add(Model(key='a', value=4, period=future))

        imported = [
            dict(key='a', value=3, source=''),
        ]

        class TestDiff(TemporalDiff):
            model = Model

        diff = TestDiff(self.session, imported, dt(2500, 1, 1))

        diff.apply()

        expected = [
            dict(key='a', value=1, period=past),
            dict(key='a', value=2, period=R(dt(2000, 1, 1), dt(2500, 1, 1))),
            dict(key='a', value=3, period=R(dt(2500, 1, 1), dt(3000, 1, 1))),
            dict(key='a', value=4, period=future),
        ]

        actual = [dict(key=o.key, value=o.value, period=o.period)
                  for o in self.session.query(Model).order_by('key', 'period')]

        compare(expected, actual)

    def test_replace_exact_row(self):
        active = R(dt(2000, 1, 1), dt(2001, 1, 1))

        self.session.add(Model(key='a', value=1, period=active))

        imported = [
            dict(key='a', value=2, source=''),
        ]

        class TestDiff(TemporalDiff):
            model = Model

        diff = TestDiff(self.session, imported, dt(2000, 1, 1))

        with ShouldRaise(ValueError):
            diff.apply()

    def test_replace_exact_row_loss_allowed(self):
        active = R(dt(2000, 1, 1), dt(2001, 1, 1))

        self.session.add(Model(key='a', value=1, period=active))

        imported = [
            dict(key='a', value=2, source=''),
        ]

        class TestDiff(TemporalDiff):
            model = Model
            replace = True

        diff = TestDiff(self.session, imported, dt(2000, 1, 1))

        diff.apply()

        expected = [
            dict(key='a', value=2, period=active),
        ]

        actual = [dict(key=o.key, value=o.value, period=o.period)
                  for o in self.session.query(Model).order_by('key', 'period')]

        compare(expected, actual)

    def test_no_keys_bad(self):
        active = R(dt(2000, 1, 1), None)

        self.session.add(NoKeys(not_key='a', value=1, period=active))

        class TestDiff(TemporalDiff):
            model = NoKeys
            extract_imported = DictExtractor('not_key')

        diff = TestDiff(self.session, [], dt(2001, 1, 1))

        with ShouldRaise(TypeError):
            diff.apply()

    def test_no_keys_good(self):
        exists = R(dt(2000, 1, 1), None)
        closed = R(dt(2000, 1, 1), dt(2001, 1, 1))
        added = R(dt(2001, 1, 1), None)
        self.session.add(NoKeys(not_key='a', value=1, period=exists))
        self.session.add(NoKeys(not_key='b', value=2, period=exists))

        imported = [
            dict(not_key='a', value=3),
            dict(not_key='c', value=4),
        ]

        class TestDiff(TemporalDiff):
            model = NoKeys
            key_fields = ['not_key']

        diff = TestDiff(self.session, imported, dt(2001, 1, 1))

        diff.apply()

        expected = [
            dict(not_key='a', value=1, period=closed),
            dict(not_key='a', value=3, period=added),
            dict(not_key='b', value=2, period=closed),
            dict(not_key='c', value=4, period=added),
        ]

        actual = [dict(not_key=o.not_key, value=o.value, period=o.period)
                  for o in self.session.query(NoKeys).order_by('not_key', 'period')]

        compare(expected, actual)

