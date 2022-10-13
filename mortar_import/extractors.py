from typing import Tuple, Callable, NamedTuple, Dict, Any

from .typing import Key


class SingleKeyDictExtractor:
    def __init__(self, key: str):
        self.key = key

    def __call__(self, obj: dict) -> Tuple[Key, dict]:
        return obj[self.key], obj


class MultiKeyDictExtractor:
    def __init__(self, *keys: str):
        self.keys = keys

    def __call__(self, obj: dict) -> Tuple[Key, dict]:
        return tuple(obj[key] for key in self.keys), obj


def DictExtractor(*keys: str) -> Callable[[dict], Tuple[Key, dict]]:
    if len(keys) == 1:
        return SingleKeyDictExtractor(keys[0])
    else:
        return MultiKeyDictExtractor(*keys)


class NamedTupleExtractor:
    def __init__(self, *keys: str):
        self.keys = keys

    def __call__(self, raw: NamedTuple) -> Tuple[Key, Dict[str, Any]]:
        key = tuple(getattr(raw, name) for name in self.keys)
        obj = dict(zip(raw._fields, raw))
        return key, obj
