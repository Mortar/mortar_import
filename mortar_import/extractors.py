class SingleKeyDictExtractor(object):

    def __init__(self, key):
        self.key = key

    def __call__(self, obj):
        return obj[self.key], obj


class MultiKeyDictExtractor(object):

    def __init__(self, *keys):
        self.keys = keys

    def __call__(self, obj):
        return tuple(obj[key] for key in self.keys), obj


def DictExtractor(*keys):
    if len(keys) == 1:
        return SingleKeyDictExtractor(keys[0])
    else:
        return MultiKeyDictExtractor(*keys)


class NamedTupleExtractor(object):

    def __init__(self, *keys):
        self.keys = keys

    def __call__(self, raw):
        key = tuple(getattr(raw, name) for name in self.keys)
        obj = dict(zip(raw._fields, raw))
        return key, obj