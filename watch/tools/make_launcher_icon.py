#!/usr/bin/env python3
"""Generate the Connect IQ launcher icon.

The Connect IQ SDK wants a PNG for the launcher icon and the repository does
not want to carry binary blobs that nobody can review, so the icon is drawn
from scratch with the standard library only.

Usage::

    python3 watch/tools/make_launcher_icon.py [output.png]

The default output is ``watch/resources/drawables/LauncherIcon.png``.

The Connect IQ resource compiler turns ``LauncherIcon.png`` into the
resource ``@Drawables.LauncherIcon`` that the manifest refers to.
"""

from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path

SIZE = 40

# Palette (RGBA).
BACKGROUND = (16, 24, 40, 255)
HOUSE = (240, 244, 248, 255)
ACCENT = (58, 190, 120, 255)
TRANSPARENT = (0, 0, 0, 0)


def _blank() -> list[list[tuple[int, int, int, int]]]:
    return [[TRANSPARENT for _ in range(SIZE)] for _ in range(SIZE)]


def _fill_rect(px, x0: int, y0: int, x1: int, y1: int, colour) -> None:
    for y in range(max(0, y0), min(SIZE, y1)):
        for x in range(max(0, x0), min(SIZE, x1)):
            px[y][x] = colour


def _draw_house(px) -> None:
    """Draw a simple house with a roof and a lit window."""
    # Roof: a triangle spanning the top half of the icon.
    apex = 6
    base = 18
    for y in range(apex, base):
        half = int((y - apex) * 0.9)
        _fill_rect(px, 20 - half, y, 20 + half, y + 1, HOUSE)
    # Body.
    _fill_rect(px, 9, base, 31, 33, HOUSE)
    # Door punched out in the background colour.
    _fill_rect(px, 16, 24, 24, 33, BACKGROUND)
    # Window.
    _fill_rect(px, 11, 21, 15, 25, ACCENT)


def _draw_watch_band(px) -> None:
    """Draw two small bands above and below the house."""
    _fill_rect(px, 14, 0, 26, 5, ACCENT)
    _fill_rect(px, 14, 35, 26, 40, ACCENT)


def _png_bytes(px) -> bytes:
    raw = bytearray()
    for row in px:
        raw.append(0)  # filter type "none"
        for r, g, b, a in row:
            raw += bytes((r, g, b, a))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


def build() -> bytes:
    px = _blank()
    _fill_rect(px, 2, 2, SIZE - 2, SIZE - 2, BACKGROUND)
    _draw_watch_band(px)
    _draw_house(px)
    return _png_bytes(px)


def main(argv: list[str]) -> int:
    default = (
        Path(__file__).resolve().parents[1] / "resources" / "drawables" / "LauncherIcon.png"
    )
    target = Path(argv[1]) if len(argv) > 1 else default
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(build())
    print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
