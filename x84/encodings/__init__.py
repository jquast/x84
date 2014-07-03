from __future__ import absolute_import

import codecs
import logging
import re

_cache = {}
_aliases = {}

logger = logging.getLogger(__name__)


def normalize_encoding(encoding):
    return re.sub(
        r'[^\w_-]', '', encoding.lower()
    ).replace('-', '_')


def search_function(encoding):
    try:
        return _cache[encoding]
    except KeyError:
        pass

    encoding = _aliases.get(encoding, encoding)
    mod = None
    try:
        mod = __import__('x84.encodings.' + encoding, fromlist=['*'], level=0)
    except ImportError:
        pass

    try:
        getregentry = mod.getregentry
    except AttributeError:
        mod = None

    if mod is None:
        _cache[encoding] = None
        return None

    _cache[encoding] = getregentry()

    try:
        codecaliases = mod.getaliases()
    except AttributeError:
        pass
    else:
        for alias in codecaliases:
            if alias not in _aliases:
                _aliases[alias] = _cache[encoding]

    return _cache[encoding]


codecs.register(search_function)


# Now to initialize all locally available codecs:
for encoding in ('amiga', 'atarist', 'cp437_art', 'cp437'):
    ''.decode(encoding)
