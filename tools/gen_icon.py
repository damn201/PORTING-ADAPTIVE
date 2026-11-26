"""Generate assets/icon.png dan assets/icon.ico (murni stdlib, tanpa PIL).

Ikon: huruf "U" emas di latar gelap, dikelilingi cincin kompas dengan
4 penanda arah. Desain orisinal — tidak memakai art resmi Sony/Naughty Dog.
ICO berisi PNG yang sama (format ICO modern membolehkan gambar PNG).
"""

import math
import struct
import zlib
from pathlib import Path

SIZE = 256


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    chunk = struct.pack(">I", len(data)) + chunk_type + data
    chunk += struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    return chunk


def _set(buf, x, y, color):
    if 0 <= x < SIZE and 0 <= y < SIZE:
        i = (y * SIZE + x) * 4
        buf[i:i + 4] = bytes(color)


def _rounded_rect(buf, x0, y0, x1, y1, radius, color):
    """Isi rounded-rect ke buffer RGBA (bytearray)."""
    for y in range(max(0, y0), min(SIZE, y1)):
        for x in range(max(0, x0), min(SIZE, x1)):
            cx = min(max(x, x0 + radius), x1 - radius)
            cy = min(max(y, y0 + radius), y1 - radius)
            if (x - cx) ** 2 + (y - cy) ** 2 <= radius * radius:
                _set(buf, x, y, color)


def _disc(buf, cx, cy, radius, color):
    for y in range(max(0, cy - radius), min(SIZE, cy + radius)):
        for x in range(max(0, cx - radius), min(SIZE, cx + radius)):
            if (x - cx) ** 2 + (y - cy) ** 2 <= radius * radius:
                _set(buf, x, y, color)


def _ring(buf, cx, cy, radius, thickness, color):
    """Cincin (lingkaran berongga)."""
    for y in range(max(0, cy - radius - 1), min(SIZE, cy + radius + 1)):
        for x in range(max(0, cx - radius - 1), min(SIZE, cx + radius + 1)):
            d = math.hypot(x - cx, y - cy)
            if radius - thickness <= d <= radius:
                _set(buf, x, y, color)


def _arc_lower(buf, cx, cy, radius, thickness, color):
    """Setengah cincin bawah saja (busur bawah huruf U)."""
    for y in range(max(0, cy), min(SIZE, cy + radius + 1)):
        for x in range(max(0, cx - radius - 1), min(SIZE, cx + radius + 1)):
            d = math.hypot(x - cx, y - cy)
            if radius - thickness <= d <= radius:
                _set(buf, x, y, color)


def make_icon_png() -> bytes:
    buf = bytearray(SIZE * SIZE * 4)
    # latar: gradien vertikal gelap (biru arang ke hitam)
    for y in range(SIZE):
        t = y / SIZE
        r = int(16 + (8 - 16) * t)
        g = int(22 + (12 - 22) * t)
        b = int(34 + (18 - 34) * t)
        for x in range(SIZE):
            i = (y * SIZE + x) * 4
            buf[i:i + 4] = bytes((r, g, b, 255))

    gold = (212, 175, 55, 255)      # emas
    gold_dark = (160, 128, 32, 255)

    # cincin kompas
    _ring(buf, 128, 128, 108, 5, gold_dark)
    # 4 penanda arah (N/E/S/W) — segitiga kecil di tepi cincin
    for angle_deg in (0, 90, 180, 270):
        a = math.radians(angle_deg)
        cx = int(128 + 92 * math.cos(a))
        cy = int(128 + 92 * math.sin(a))
        _disc(buf, cx, cy, 6, gold)

    # huruf "U" emas: dua batang vertikal + busur bawah
    _rounded_rect(buf, 82, 66, 110, 168, 8, gold)
    _rounded_rect(buf, 146, 66, 174, 168, 8, gold)
    # busur bawah (setengah cincin) + isi tengah agar menyatu dengan batang
    _arc_lower(buf, 128, 168, 46, 28, gold)
    _disc(buf, 128, 168, 18, gold)

    raw = b""
    for y in range(SIZE):
        raw += b"\x00" + bytes(buf[y * SIZE * 4:(y + 1) * SIZE * 4])
    ihdr = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", zlib.compress(raw, 9))
        + _png_chunk(b"IEND", b"")
    )
    return png


def make_icon_ico(png: bytes) -> bytes:
    header = struct.pack("<HHH", 0, 1, 1)
    entry = struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(png), 6 + 16)
    return header + entry + png


def main():
    assets = Path(__file__).resolve().parents[1] / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    png = make_icon_png()
    ico = make_icon_ico(png)
    (assets / "icon.png").write_bytes(png)
    (assets / "icon.ico").write_bytes(ico)
    print(f"icon.png: {len(png)} byte")
    print(f"icon.ico: {len(ico)} byte")


if __name__ == "__main__":
    main()
