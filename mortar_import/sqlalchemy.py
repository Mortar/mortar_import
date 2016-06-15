from __future__ import absolute_import
# import orm here so that event registration work
import sqlalchemy.orm

from abc import abstractmethod, abstractproperty
from mortar_import.diff import Diff
from sqlalchemy import inspect

class SQLAlchemyDiff(Diff):

    flush_per_type = True
    ignore_fields = set()

    def __init__(self, session, imported):
        self.session = session
        super(SQLAlchemyDiff, self).__init__(self.existing(), imported)

    @abstractproperty
    def model(self):
        """
        The model that will be used to source existing objects.
        """

    def existing(self):
        return self.session.query(self.model)

    def extract_existing(self, obj):
        state = inspect(obj)
        relationships = state.mapper.relationships
        key = state.identity
        extracted = {name: attr.value for (name, attr) in state.attrs.items()
                     if not (name in self.ignore_fields or
                             name in relationships)}
        return key, extracted

    @abstractmethod
    def extract_imported(self, obj):
        """
        Must return ``key, dict_`` where ``key`` is the key of the imported
        object and ``dict_`` is a mapping of all keys to values for the
        imported object.
        """

    def add(self, key, imported, extracted_imported):
        self.session.add(self.model(**extracted_imported))

    def update(self,
               key,
               existing, existing_extracted,
               imported, imported_extracted):
        for key, value in imported_extracted.items():
            setattr(existing, key, value)

    def delete(self, key, existing, existing_extracted):
        self.session.delete(existing)

    def per_type_flush(self):
        if self.flush_per_type:
            self.session.flush()

    post_add = post_update = post_delete = per_type_flush
