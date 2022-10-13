from abc import abstractmethod
from datetime import datetime
from typing import Sequence, cast, Tuple, Dict, Any, Union

from mortar_mixins import Temporal
from sqlalchemy.orm import Session

from .sqlalchemy import SQLAlchemyDiff, Model, ModelAttributes
from .typing import Imported, Key


# Once we only support Python 3.8+, this can become a protocol:
TemporalModel = Union[Temporal, Model]


class TemporalDiff(SQLAlchemyDiff):

    # is it okay to replace whole rows because the update
    # has the same time period as the existing value?
    replace = False
    key_fields: Sequence[str] = None

    def __init__(self, session: Session, imported: Sequence[Imported], at: datetime):
        self.at: datetime = at
        if self.key_fields is None:
            self.key_fields = self.model.key_columns
        super(TemporalDiff, self).__init__(session, imported)

    @property
    @abstractmethod
    def model(self) -> TemporalModel:
        """
        The model that will be used to source existing objects.
        """

    def existing(self) -> Sequence[TemporalModel]:
        return cast(Sequence[Temporal],
                    self.session.query(self.model).filter(self.model.value_at(self.at)))

    def extract_existing(self, obj: TemporalModel) -> Tuple[Key, ModelAttributes]:
        _, extracted = super(TemporalDiff, self).extract_existing(obj)
        del extracted['period']
        del extracted['id']
        key = tuple(getattr(obj, name) for name in self.key_fields)
        return key, extracted

    def extract_imported(self, obj: Dict[str, Any]) -> Tuple[Key, ModelAttributes]:
        # this assumes obj is a dict, override this method if that's not
        # the case
        return tuple(obj[k] for k in self.key_fields), obj

    def add(
            self,
            key: Key,
            imported: Imported,
            extracted_imported: ModelAttributes
    ):
        obj = self.model(**extracted_imported)
        obj.value_from = self.at
        self.session.add(obj)

    def update(
            self,
            key: Key,
            existing: TemporalModel,
            existing_extracted: ModelAttributes,
            imported: Imported,
            imported_extracted: ModelAttributes
    ):
        if existing.value_from == self.at:
            if self.replace:
                for key, value in imported_extracted.items():
                    setattr(existing, key, value)
            else:
                raise ValueError(
                    (
                        "Replacing existing value for {key!r} over {period!r} "
                        "would lose history. Existing: {existing}, "
                        "imported {imported}."
                    ).format(
                        key=key,
                        period=existing.period,
                        existing=existing_extracted,
                        imported=imported_extracted,
                    )
                )
        else:
            existing_value_to = existing.value_to
            existing.value_to = self.at
            obj = self.model(**imported_extracted)
            obj.value_from = self.at
            obj.value_to = existing_value_to
            self.session.add(obj)

    def delete(
            self,
            key: Key,
            existing: TemporalModel,
            existing_extracted: ModelAttributes
    ):
        existing.value_to = self.at
