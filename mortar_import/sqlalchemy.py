from __future__ import absolute_import
# import orm here so that event registration work
import sqlalchemy.orm

from abc import abstractmethod, abstractproperty
from mortar_import.diff import Diff
from sqlalchemy import inspect

# placeholder for all objects of a type

class SQLAlchemyDiff(Diff):

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
        i = inspect(obj)
        key = i.identity
        extracted = {name: getattr(obj, name) for name in i.attrs.keys()}
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
