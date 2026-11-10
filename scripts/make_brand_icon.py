#!/usr/bin/env python3
"""Generate the brand icon used by Home Assistant and HACS.

The repository does not want to carry binary blobs that nobody can review,
so the icon is drawn from scratch with the standard library only.

Usage::

    python3 scripts/make_brand_icon.py [output.png]

The default output is ``brand/icon.png``.
"""

from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path

SIZE = 256

# Palette (RGBA).
BACKGROUND = (16, 24, 40, 255)
HOUSE = (240, 244, 248, 255)
ACCENT = (58, 190, 120, 255)
TRANSPARENT = (0, 0, 0, 0)


def _blank() -> list[list[tuple[int, int, int, int]]]:
    return [[TRANSPARENT for _ in range(SIZE)] for _ in range(SIZE)]


def _fill_rect(
    px: list[list[tuple[int, int, int, int]]],
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    colour: tuple[int, int, int, int],
) -> None:
    """Fill a rectangle."""
    for y in range(max(0, y0), min(SIZE, y1)):
        for x in range(max(0, x0), min(SIZE, x1)):
            px[y][x] = colour


def _fill_rounded_rect(
    px: list[list[tuple[int, int, int, int]]],
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    radius: int,
    colour: tuple[int, int, int, int],
) -> None:
    """Fill a rectangle with rounded corners."""
    for y in range(max(0, y0), min(SIZE, y1)):
        for x in range(max(0, x0), min(SIZE, x1)):
            # Distance into the corner region.
            cx = 0
            cy = 0
            if x < x0 + radius:
                cx = x0 + radius - x
            elif x >= x1 - radius:
                cx = x - (x1 - radius - 1)
            if y < y0 + radius:
                cy = y0 + radius - y
            elif y >= y1 - radius:
                cy = y - (y1 - radius - 1)
            if cx and cy and cx * cx + cy * cy > radius * radius:
                continue
            px[y][x] = colour


def _draw_house(px: list[list[tuple[int, int, int, int]]]) -> None:
    """Draw a house with a roof and a lit window."""
    apex = 38
    base = 118
    for y in range(apex, base):
        half = int((y - apex) * 2.25)
        _fill_rect(px, 128 - half, y, 128 + half, y + 1, HOUSE)
    _fill_rect(px, 58, base, 198, 214, HOUSE)
    _fill_rect(px, 103, 154, 153, 214, BACKGROUND)
    _fill_rect(px, 71, 135, 97, 161, ACCENT)


def _draw_watch_band(px: list[list[tuple[int, int, int, int]]]) -> None:
    """Draw the watch band above and below the house."""
    _fill_rounded_rect(px, 90, 0, 166, 34, 16, ACCENT)
    _fill_rounded_rect(px, 90, 222, 166, 256, 16, ACCENT)


def _png_bytes(px: list[list[tuple[int, int, int, int]]]) -> bytes:
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
    """Build the square brand icon."""
    px = _blank()
    _fill_rounded_rect(px, 8, 8, SIZE - 8, SIZE - 8, 48, BACKGROUND)
    _draw_watch_band(px)
    _draw_house(px)
    return _png_bytes(px)


def build_logo() -> bytes:
    """Build the wide logo used in the Home Assistant brand list."""
    px = _blank()
    _draw_watch_band(px)
    _draw_house(px)
    return _png_bytes(px)


def main(argv: list[str]) -> int:
    """Write the brand images."""
    root = Path(__file__).resolve().parents[1]
    if len(argv) > 1:
        target = Path(argv[1])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(build())
        print(f"wrote {target}")
        return 0

    brand = root / "brand"
    brand.mkdir(parents=True, exist_ok=True)
    icon = brand / "icon.png"
    icon.write_bytes(build())
    print(f"wrote {icon}")

    logo = brand / "logo.png"
    logo.write_bytes(build_logo())
    print(f"wrote {logo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
