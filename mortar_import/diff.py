from abc import ABCMeta, abstractmethod

class Diff(object):

    __metaclass__ = ABCMeta

    def __init__(self, existing, imported):
        self.existing = existing
        self.imported = imported

    @abstractmethod
    def extract_existing(self, obj):
        """
        Must return ``key, obj`` where ``key`` is the key of the existing
        object and ``obj`` is an object that can be compared with
        imported objects.
        """

    @abstractmethod
    def extract_imported(self, obj):
        """
        Must return ``key, obj`` where ``key`` is the key of the imported
        object and ``obj`` is an object that can be compared with
        existing objects.
        """

    @abstractmethod
    def add(self, key, imported, extracted_imported):
        """
        Handle the addition of an imported object.
        """

    @abstractmethod
    def update(self,
               key,
               existing, existing_extracted,
               imported, imported_extracted):
        """
        Handle an update of an existing object.
        """

    @abstractmethod
    def delete(self, key, existing, existing_extracted):
        """
        Handle the deletion of an existing object.
        """

    def apply(self):
        for name in 'existing', 'imported':
            mapping = {}
            sequence = getattr(self, name)
            extract = getattr(self, 'extract_'+name)
            for raw in sequence:
                key, extracted = extract(raw)
                if key in mapping:
                    existing_raw, existing_extracted = mapping[key]
                    raise KeyError(
                        "{key!r} occurs more than once in {name}, "
                        "first was {existing_extracted!r} from {existing!r}, "
                        "next was {new_extracted!r} from {new!r}".format(
                            key=key, name=name,
                            existing_extracted=existing_extracted,
                            existing=existing_raw,
                            new_extracted=extracted,
                            new=raw,
                        ))
                mapping[key] = raw, extracted
            setattr(self, name+'_mapping', mapping)
            setattr(self, name+'_keys', set(mapping))

        for key in sorted(self.imported_keys - self.existing_keys):
            self.add(key, *self.imported_mapping[key])

        for key in sorted(self.imported_keys & self.existing_keys):
            existing, existing_extracted = self.existing_mapping[key]
            imported, imported_extracted = self.imported_mapping[key]
            if existing_extracted != imported_extracted:
                self.update(key,
                            existing, existing_extracted,
                            imported, imported_extracted)

        for key in sorted(self.existing_keys - self.imported_keys):
            self.delete(key, *self.existing_mapping[key])
