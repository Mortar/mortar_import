from typing import TypeVar, Hashable

Key = TypeVar('Key', bound=Hashable)

Existing = TypeVar('Existing')
Imported = TypeVar('Imported')

ExtractedExisting = TypeVar('ExtractedExisting')
ExtractedImported = TypeVar('ExtractedImported')
