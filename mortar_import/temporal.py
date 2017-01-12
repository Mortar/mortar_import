from __future__ import absolute_import
# import orm here so that event registration work
import sqlalchemy.orm

from abc import abstractmethod
from mortar_import.sqlalchemy import SQLAlchemyDiff
from sqlalchemy import inspect


class TemporalDiff(SQLAlchemyDiff):

    # is it okay to replace whole rows because the update
    # has the same time period as the existing value?
    replace = False
    key_fields = None

    def __init__(self, session, imported, at):
        self.at = at
        if self.key_fields is None:
            self.key_fields = self.model.key_columns
        super(TemporalDiff, self).__init__(session, imported)

    def existing(self):
        return self.session.query(self.model)\
                           .filter(self.model.value_at(self.at))

    def extract_existing(self, obj):
        _, extracted = super(TemporalDiff, self).extract_existing(obj)
        del extracted['period']
        del extracted['id']
        key = tuple(getattr(obj, name) for name in self.key_fields)
        return key, extracted

    def extract_imported(self, obj):
        # this assumes obj is a dict, override this method if that's not
        # the case
        return tuple(obj[k] for k in self.key_fields), obj

    def add(self, key, imported, extracted_imported):
        obj = self.model(**extracted_imported)
        obj.value_from = self.at
        self.session.add(obj)

    def update(self,
               key,
               existing, existing_extracted,
               imported, imported_extracted):
        if existing.value_from == self.at:
            if self.replace:
                for key, value in imported_extracted.items():
                    setattr(existing, key, value)
            else:
                raise ValueError((
                    "Replacing existing value for {key!r} over {period!r} "
                    "would lose history. Existing: {existing}, "
                    "imported {imported}."
                    ).format(key=key,
                             period=existing.period,
                             existing=existing_extracted,
                             imported=imported_extracted))
        else:
            existing_value_to = existing.value_to
            existing.value_to = self.at
            obj = self.model(**imported_extracted)
            obj.value_from = self.at
            obj.value_to = existing_value_to
            self.session.add(obj)

    def delete(self, key, existing, existing_extracted):
        existing.value_to = self.at
