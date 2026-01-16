from typing import TypeVar, Hashable

#: The hashable key extracted from existing and imported objects
#: to decide if they represent the same object.
Key = TypeVar('Key', bound=Hashable)

#: An existing object.
Existing = TypeVar('Existing')
#: An imported object.
Imported = TypeVar('Imported')

#: An extracted existing object.
ExtractedExisting = TypeVar('ExtractedExisting')
#: An extracted imported object.
ExtractedImported = TypeVar('ExtractedImported')
