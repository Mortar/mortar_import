from mock import Mock, call
from unittest import TestCase
from testfixtures import compare, ShouldRaise
from mortar_import.diff import Diff


class TestPlain(TestCase):

    def make_differ(self):
        mock = Mock()

        class DiffTuple(Diff):
            def extract_existing(self, obj):
                return obj[0], (obj[0], obj[-1])

            extract_imported = extract_existing

            add = mock.add
            update = mock.update
            delete = mock.delete

        return DiffTuple, mock

    def test_tuple(self):

        DiffTuple, mock = self.make_differ()

        diff = DiffTuple(
            [('a', 1, 2), ('b', 3, 4), ('c', 5, 6)],
            [('b', 3, 4), ('c', 5, 7), ('d', 7, 8)]
        )

        compare([], mock.mock_calls)

        diff.apply()

        compare([
            call.add('d', ('d', 7, 8), ('d', 8)),
            call.update('c', ('c', 5, 6), ('c', 6), ('c', 5, 7), ('c', 7)),
            call.delete('a', ('a', 1, 2), ('a', 2)),
        ], mock.mock_calls)

    def test_duplicate_existing_key(self):

        DiffTuple, mock = self.make_differ()

        diff = DiffTuple([('a', 1, 2), ('a', 3, 4)], [])

        with ShouldRaise(
                KeyError("'a' occurs more than once in existing, "
                         "first was ('a', 2) from ('a', 1, 2), "
                         "next was ('a', 4) from ('a', 3, 4)")):
            diff.apply()

    def test_duplicate_imported_key(self):

        DiffTuple, mock = self.make_differ()

        diff = DiffTuple([], [('a', 1, 2), ('a', 3, 4)])

        with ShouldRaise(
                KeyError("'a' occurs more than once in imported, "
                         "first was ('a', 2) from ('a', 1, 2), "
                         "next was ('a', 4) from ('a', 3, 4)")):
            diff.apply()
