"""Read hard numbers (date, funds, population) from a native .SC2 save.

Layout per https://github.com/OpenCity2k/SC2k-docs: an IFF ``FORM``/``SCDH``
container whose ``MISC`` segment is RLE-compressed big-endian int32s.
The game calendar has 12 months of 25 days (300 days per year).
"""

from __future__ import annotations

import struct
from pathlib import Path

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
MISC_YEAR_FOUNDED, MISC_DAYS, MISC_FUNDS, MISC_POPULATION = 3, 4, 5, 12


def segments(data: bytes) -> dict[str, bytes]:
    if data[:4] != b"FORM" or data[8:12] != b"SCDH":
        raise ValueError("not a SimCity 2000 city file")
    out, i = {}, 12
    while i + 8 <= len(data):
        n = struct.unpack(">I", data[i + 4:i + 8])[0]
        out[data[i:i + 4].decode("latin-1")] = data[i + 8:i + 8 + n]
        i += 8 + n
    return out


def unrle(b: bytes) -> bytes:
    out, i = bytearray(), 0
    while i < len(b):
        c = b[i]
        i += 1
        if c < 128:
            out += b[i:i + c]
            i += c
        else:
            out += bytes([b[i]]) * (c - 127)
            i += 1
    return bytes(out)


def read_stats(path: Path) -> dict[str, int | str]:
    misc = unrle(segments(path.read_bytes())["MISC"])
    v = struct.unpack(f">{len(misc) // 4}i", misc[:len(misc) // 4 * 4])
    days = v[MISC_DAYS]
    year = v[MISC_YEAR_FOUNDED] + days // 300
    return {
        "date": f"{MONTHS[(days % 300) // 25]} {year}",
        "year": year,
        "funds": v[MISC_FUNDS],
        "population": v[MISC_POPULATION],
    }
