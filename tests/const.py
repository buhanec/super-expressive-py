"""Some test constants."""

import unicodedata

NAMED_UNICODE = {}

for n in range(0x000000, 0x11FFFF + 1):
    try:
        NAMED_UNICODE[chr(n)] = unicodedata.name(chr(n))
    except ValueError:
        pass
