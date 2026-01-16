from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Tuple, List, Set, Dict, Callable, NamedTuple, Sequence

from .typing import Existing, Imported, ExtractedExisting, ExtractedImported, Key


class Addition(NamedTuple):
    key: Key
    imported: Imported
    imported_extracted: ExtractedImported


class Update(NamedTuple):
    key: Key
    existing: Existing
    existing_extracted: ExtractedExisting
    imported: Imported
    imported_extracted: ExtractedImported


class Deletion(NamedTuple):
    key: Key
    existing: Existing
    existing_extracted: ExtractedExisting


class Diff(ABC):

    # Used internally:
    existing_mapping: Dict[Key, Tuple[Existing, ExtractedExisting]]
    existing_keys: Set[Key]
    imported_mapping: Dict[Key, Tuple[Imported, ExtractedImported]]
    imported_keys: Set[Key]

    # Populated by :meth:`compute`:
    to_add: List[Addition] = None
    to_update: List[Update] = None
    to_delete: List[Deletion] = None

    def __init__(self, existing: Sequence[Existing], imported: Sequence[Existing]):
        self.existing = existing
        self.imported = imported

    @abstractmethod
    def extract_existing(self, obj: Existing) -> Tuple[Key, ExtractedExisting]:
        """
        Must return ``key, obj`` where ``key`` is the key of the existing
        object and ``obj`` is an object that can be compared with
        imported objects.
        """

    @abstractmethod
    def extract_imported(self, obj: Imported) -> Tuple[Key, ExtractedImported]:
        """
        Must return ``None`` or ``key, obj`` where ``key`` is the key of the
        imported object and ``obj`` is an object that can be compared with
        existing objects.

        If ``None``, then that object will be ignored.
        """

    @abstractmethod
    def add(
            self,
            key: Key,
            imported: Imported,
            extracted_imported: ExtractedImported
    ) -> None:
        """
        Handle the addition of an imported object.
        """

    @abstractmethod
    def update(
            self,
            key: Key,
            existing: Existing,
            existing_extracted: ExtractedExisting,
            imported: Imported,
            imported_extracted: ExtractedImported,
    ) -> None:
        """
        Handle an update of an existing object.
        """

    @abstractmethod
    def delete(
            self,
            key: Key,
            existing: Existing,
            existing_extracted: ExtractedExisting
    ) -> None:
        """
        Handle the deletion of an existing object.
        """

    post_add: Callable[[], None] = None
    post_update: Callable[[], None] = None
    post_delete: Callable[[], None] = None

    def compute(self) -> None:
        problems = defaultdict(list)
        for name in 'existing', 'imported':
            mapping = {}
            sequence = getattr(self, name)
            extract = getattr(self, 'extract_' + name)
            for raw in sequence:
                extracted = extract(raw)
                if extracted is None:
                    continue
                key, extracted = extracted
                if key in mapping:
                    problems[name, key].append((raw, extracted))
                else:
                    mapping[key] = raw, extracted
            setattr(self, name + '_mapping', mapping)
            setattr(self, name + '_keys', set(mapping))

        if problems:
            lines = []
            for name_key, dups in sorted(problems.items()):
                name, key = name_key
                mapping = getattr(self, name + '_mapping')
                keys = getattr(self, name + '_keys')
                dups.insert(0, mapping[key])

                handler = getattr(self, 'handle_' + name + '_problem', None)
                if handler:
                    result = handler(key, dups)
                    if result:
                        del mapping[key]
                        keys.remove(key)
                        for key, raw, extracted in result:
                            if key in mapping:
                                raise ValueError(
                                    (
                                        'Problem handling for {!r} '
                                        'resulted in duplicate key'
                                    ).format(key)
                                )
                            mapping[key] = raw, extracted
                            keys.add(key)
                        continue

                lines.append(
                    "{key!r} occurs {len} times in {name}: {repr}".format(
                        key=key,
                        len=len(dups),
                        name=name,
                        repr=', '.join(
                            repr(extracted) + ' from ' + repr(raw)
                            for raw, extracted in dups
                        ),
                    )
                )
            if lines:
                raise AssertionError('\n'.join(lines))

        self.to_add = []
        self.to_update = []
        self.to_delete = []

        for key in sorted(self.imported_keys - self.existing_keys):
            self.to_add.append(Addition(key, *self.imported_mapping[key]))

        for key in sorted(self.imported_keys & self.existing_keys):
            existing, existing_extracted = self.existing_mapping[key]
            imported, imported_extracted = self.imported_mapping[key]
            if existing_extracted != imported_extracted:
                self.to_update.append(
                    Update(
                        key, existing, existing_extracted, imported, imported_extracted
                    )
                )

        for key in sorted(self.existing_keys - self.imported_keys):
            self.to_delete.append(Deletion(key, *self.existing_mapping[key]))

    def apply(self) -> None:
        """
        :meth:`compute` this :class:`Diff` if it has not already been computed
        and then apply it by
        :return:
        """
        if self.to_add is None:
            self.compute()
        for op in 'delete', 'update', 'add':
            meth = getattr(self, op)
            for action in getattr(self, 'to_' + op):
                meth(*action)
            post = getattr(self, 'post_' + op)
            if post is not None:
                post()
