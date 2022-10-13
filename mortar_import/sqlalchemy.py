# import orm here so that event registration work

from abc import abstractmethod
from typing import Set, Sequence, TypeVar, Type, Tuple, Any, Dict

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from .diff import Diff
from .typing import Imported, Key

Model = TypeVar('Model')
ModelAttributes = Dict[str, Any]


class SQLAlchemyDiff(Diff):

    flush_per_type: bool = True
    ignore_fields: Set[str] = set()

    def __init__(self, session: Session, imported: Sequence[Imported]):
        self.session: Session = session
        super(SQLAlchemyDiff, self).__init__(self.existing(), imported)

    @property
    @abstractmethod
    def model(self) -> Type[Model]:
        """
        The model that will be used to source existing objects.
        """

    def existing(self) -> Sequence[Model]:
        return self.session.query(self.model)

    def extract_existing(self, obj: Model) -> Tuple[Key, ModelAttributes]:
        state = inspect(obj)
        relationships = state.mapper.relationships
        key = state.identity
        extracted = {
            name: attr.value
            for (name, attr) in state.attrs.items()
            if not (name in self.ignore_fields or name in relationships)
        }
        return key, extracted

    @abstractmethod
    def extract_imported(self, obj: Imported) -> Tuple[Key, ModelAttributes]:
        """
        Must return ``key, dict_`` where ``key`` is the key of the imported
        object and ``dict_`` is a mapping of all keys to values for the
        imported object.
        """

    def add(
            self,
            key: Key,
            imported: Imported,
            extracted_imported: ModelAttributes
    ):
        self.session.add(self.model(**extracted_imported))

    def update(
            self,
            key: Key,
            existing: Model,
            existing_extracted: ModelAttributes,
            imported: Imported,
            imported_extracted: ModelAttributes,
    ):
        for key, value in imported_extracted.items():
            setattr(existing, key, value)

    def delete(
            self,
            key: Key,
            existing: Model,
            existing_extracted: ModelAttributes
    ):
        self.session.delete(existing)

    def per_type_flush(self) -> None:
        if self.flush_per_type:
            self.session.flush()

    post_add = post_update = post_delete = per_type_flush
