#!/usr/bin/env python3
"""news-image-20261123: sum up Monday 23 November 2026's world news in one image.

Draws a newspaper front page (1024x1024 PNG) with the day's real news,
researched from reporting published on 23 November 2026:

  * COP31 collapses in Antalya: no climate pact, fossil-fuel deadlock,
    the longest UN climate summit on record (ended Sunday 22 Nov).
  * Tankers hit in the Strait of Hormuz amid the US-Iran conflict.
  * Russian drone strike on a building in the Kyiv region, 14 missing,
    as Trump says the US is working on a larger Ukraine-Russia ceasefire.
  * Factory fire in Banten, Indonesia: 24 dead, about 30 unaccounted for.
  * Plus the day in brief: EU Big Tech tax, South Korea minister quits
    over AI exam cheating, Bangladesh arson, Lisbon cost-of-living march,
    Mexico captures cartel boss 'El Chapo Isidro', Pant's Test record.

Stdlib only. No network, no fonts, no images: every pixel is drawn by
this code, including a hand-built 5x7 bitmap font. Deterministic:
running twice produces byte-identical output.
"""

import os
import struct
import zlib

W, H = 1024, 1024
OUT = os.environ.get("MAKEFUN_OUTPUT", "/output/entry.png")

# ---------------------------------------------------------------- palette
PAPER = (246, 241, 231)
INK = (20, 33, 61)          # deep navy ink
INK_SOFT = (58, 68, 92)
RED = (178, 35, 27)
TEAL = (15, 118, 110)
OCHRE = (201, 138, 27)
GREY = (120, 116, 108)
LIGHT = (232, 226, 213)
SKY = (176, 205, 222)
SEA = (38, 84, 120)
SEA_DARK = (24, 58, 88)
SAND = (214, 178, 120)
EARTH = (146, 96, 58)
EARTH_DARK = (104, 64, 36)
SMOKE = (96, 96, 96)
FLAME = (232, 110, 24)
FLAME_Y = (245, 196, 66)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (46, 125, 50)

# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(bg) * (w * h)

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(c)

    def rect(self, x, y, w, h, c):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            self.px[base:base + (x1 - x0) * 3] = bytes(c) * (x1 - x0)

    def hline(self, x, y, w, c, t=1):
        for k in range(t):
            self.rect(x, y + k, w, 1, c)

    def vline(self, x, y, h, c, t=1):
        for k in range(t):
            self.rect(x + k, y, 1, h, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            for a in range(t):
                for b in range(t):
                    self.set(x0 + a, y0 + b, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, c):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                    self.set(xx, yy, c)

    def ring(self, cx, cy, r, c, t=2):
        for yy in range(cy - r - t, cy + r + t + 1):
            for xx in range(cx - r - t, cx + r + t + 1):
                d = ((xx - cx) ** 2 + (yy - cy) ** 2) ** 0.5
                if r - t / 2 <= d <= r + t / 2:
                    self.set(xx, yy, c)

    def poly(self, pts, c):
        """Scanline fill of a simple polygon."""
        ys = [p[1] for p in pts]
        for y in range(max(0, min(ys)), min(self.h, max(ys) + 1)):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                for x in range(int(xs[k]), int(xs[k + 1]) + 1):
                    self.set(x, y, c)

    def frame(self, x, y, w, h, c, t=2):
        self.hline(x, y, w, c, t)
        self.hline(x, y + h - t, w, c, t)
        self.vline(x, y, h, c, t)
        self.vline(x + w - t, y, h, c, t)


# ---------------------------------------------------------------- 5x7 font
# Each glyph: 7 rows of 5 bits, '#' = on.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10111", "10001", "10001", "01110"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "00100", "00100", "00100"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "01100", "01000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00010", "00100", "00000", "00100"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "&": ("01100", "10010", "10010", "01000", "10101", "10010", "01101"),
    "%": ("10001", "10010", "00010", "00100", "01000", "10010", "10001"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "01100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "$": ("00100", "01111", "10101", "01100", "11101", "10001", "01110"),
    "*": ("00000", "10101", "01110", "11111", "01110", "10101", "00000"),
}

UPPER = {chr(c): chr(c) for c in range(97, 123)}
for _k, _v in list(UPPER.items()):
    pass


def text_width(s, scale):
    return len(s) * 6 * scale - scale


def draw_text(cv, x, y, s, scale, color, align="left"):
    """Draw uppercase text (lowercase is uppercased). Returns width used."""
    s = s.upper()
    w = text_width(s, scale)
    if align == "center":
        x -= w // 2
    elif align == "right":
        x -= w
    cx = x
    for ch in s:
        g = FONT.get(ch, FONT[" "])
        for r in range(7):
            row = g[r]
            for c in range(5):
                if row[c] == "1":
                    cv.rect(cx + c * scale, y + r * scale, scale, scale, color)
        cx += 6 * scale
    return w


def wrap_text(s, scale, max_w):
    """Greedy word wrap; returns list of lines."""
    words = s.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if text_width(trial, scale) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_para(cv, x, y, s, scale, color, max_w, leading=None):
    lh = leading if leading is not None else 10 * scale
    for i, line in enumerate(wrap_text(s, scale, max_w)):
        draw_text(cv, x, y + i * lh, line, scale, color)
    return y + len(wrap_text(s, scale, max_w)) * lh


# ---------------------------------------------------------------- PNG encode
def png_bytes(cv):
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)  # filter: None
        raw += cv.px[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(typ, data):
        c = struct.pack(">I", len(data)) + typ + data
        return c + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", comp) + chunk(b"IEND", b""))


# ---------------------------------------------------------------- scenes
def scene_cop31(cv, x, y, w, h):
    """Antalya: empty summit hall under a harsh sun, cracked earth."""
    cv.rect(x, y, w, h, SKY)
    # sun
    cv.circle(x + w - 78, y + 62, 44, OCHRE)
    cv.ring(x + w - 78, y + 62, 52, OCHRE, 3)
    # distant sea band
    cv.rect(x, y + h - 150, w, 26, SEA)
    # cracked earth
    cv.poly([(x, y + h - 124), (x + w, y + h - 124), (x + w, y + h), (x, y + h)],
            EARTH)
    cv.line(x + 40, y + h - 124, x + 90, y + h - 60, EARTH_DARK, 4)
    cv.line(x + 90, y + h - 60, x + 70, y + h - 10, EARTH_DARK, 3)
    cv.line(x + 90, y + h - 60, x + 170, y + h - 30, EARTH_DARK, 3)
    cv.line(x + w - 120, y + h - 124, x + w - 170, y + h - 55, EARTH_DARK, 4)
    cv.line(x + w - 170, y + h - 55, x + w - 240, y + h - 20, EARTH_DARK, 3)
    cv.line(x + w - 170, y + h - 55, x + w - 150, y + h - 8, EARTH_DARK, 3)
    cv.line(x + w // 2, y + h - 124, x + w // 2 + 30, y + h - 40, EARTH_DARK, 3)
    # empty chairs row (delegates gone)
    for i in range(5):
        cx0 = x + 30 + i * 62
        cy0 = y + h - 178
        cv.rect(cx0, cy0, 44, 8, INK)
        cv.rect(cx0, cy0 + 8, 6, 34, INK)
        cv.rect(cx0 + 38, cy0 + 8, 6, 34, INK)
    # fallen gavel
    cv.line(x + w // 2 - 30, y + h - 95, x + w // 2 + 46, y + h - 78, INK, 5)
    cv.rect(x + w // 2 + 40, y + h - 92, 26, 18, INK)
    # red NO DEAL stamp
    cv.frame(x + 22, y + 18, 150, 52, RED, 4)
    draw_text(cv, x + 97, y + 32, "NO DEAL", 2, RED, align="center")


def scene_hormuz(cv, x, y, w, h):
    """Burning tanker in the Strait of Hormuz. Fits a short strip (h~118)."""
    cv.rect(x, y, w, h, (224, 196, 150))  # hazy sky
    cv.circle(x + w - 52, y + 26, 18, (240, 220, 170))
    # sea
    cv.rect(x, y + h - 44, w, 44, SEA)
    cv.rect(x, y + h - 44, w, 4, SEA_DARK)
    # tanker hull
    cv.poly([(x + 24, y + h - 58), (x + w - 24, y + h - 58),
             (x + w - 42, y + h - 34), (x + 42, y + h - 34)], (52, 52, 56))
    cv.rect(x + 52, y + h - 78, 52, 20, (52, 52, 56))
    cv.rect(x + 112, y + h - 72, 22, 14, (52, 52, 56))
    # fire + smoke (kept inside the strip)
    cv.poly([(x + 140, y + h - 58), (x + 158, y + h - 100), (x + 176, y + h - 58)],
            FLAME)
    cv.poly([(x + 168, y + h - 58), (x + 182, y + h - 88), (x + 198, y + h - 58)],
            FLAME_Y)
    cv.circle(x + 158, y + h - 108, 13, SMOKE)
    cv.circle(x + 178, y + h - 118, 11, SMOKE)
    # mine in the water
    cv.circle(x + w - 56, y + h - 22, 9, INK)
    for dx, dy in ((-11, 0), (11, 0), (0, -11), (0, 11), (-8, -8), (8, -8)):
        cv.line(x + w - 56, y + h - 22, x + w - 56 + dx, y + h - 22 + dy, INK, 2)
    # waves
    for i in range(4):
        wx = x + 16 + i * 84
        cv.line(wx, y + h - 14, wx + 34, y + h - 14, WHITE, 2)


def scene_kyiv(cv, x, y, w, h):
    """Kyiv skyline at dusk, drone dots, one damaged tower. Fits h~118."""
    cv.rect(x, y, w, h, (46, 52, 84))  # dusk sky
    cv.circle(x + w - 52, y + 26, 15, (232, 226, 213))
    # skyline (base at bottom of strip)
    heights = [34, 52, 42, 62, 46, 56, 38, 48]
    bx = x + 10
    bw = (w - 20) // len(heights)
    for i, hh in enumerate(heights):
        cv.rect(bx, y + h - 12 - hh, bw - 5, hh + 12, (24, 28, 48))
        for wy in range(y + h - 12 - hh + 8, y + h - 16, 16):
            for wx in range(bx + 5, bx + bw - 9, 12):
                if (wx * 7 + wy * 13) % 5 == 0:
                    cv.rect(wx, wy, 4, 5, FLAME_Y)
        bx += bw
    # damaged tower: jagged top + smoke + flame
    dx0 = x + w // 2 - 26
    cv.poly([(dx0, y + h - 12 - 62), (dx0 + 14, y + h - 12 - 74),
             (dx0 + 24, y + h - 12 - 60), (dx0 + 36, y + h - 12 - 70),
             (dx0 + 48, y + h - 12 - 56), (dx0 + 48, y + h),
             (dx0, y + h)], (24, 28, 48))
    cv.circle(dx0 + 22, y + h - 88, 12, SMOKE)
    cv.circle(dx0 + 36, y + h - 102, 10, SMOKE)
    cv.poly([(dx0 + 16, y + h - 12 - 62), (dx0 + 28, y + h - 12 - 92),
             (dx0 + 40, y + h - 12 - 62)], FLAME)
    # drone dots
    for dx, dy in ((48, 34), (92, 52), (w - 96, 58), (w - 56, 84)):
        cv.circle(x + dx, y + dy, 3, RED)
        cv.circle(x + dx, y + dy, 7, RED)


def scene_fire(cv, x, y, w, h):
    """Banten factory fire: flames over a low industrial block. Fits h~110."""
    cv.rect(x, y, w, h, (30, 30, 34))
    # factory block
    cv.rect(x + 24, y + h - 40, w - 48, 40, (74, 70, 66))
    cv.rect(x + 24, y + h - 56, 72, 16, (74, 70, 66))
    for i in range(5):
        cv.rect(x + 36 + i * 62, y + h - 32, 34, 18, (30, 30, 34))
    # chimney
    cv.rect(x + w - 58, y + h - 84, 22, 44, (74, 70, 66))
    cv.circle(x + w - 47, y + h - 96, 12, SMOKE)
    cv.circle(x + w - 34, y + h - 108, 10, SMOKE)
    # flames (kept inside the strip: base y+h-40, apex no higher than y+4)
    for fx, fh, fc in ((52, 62, FLAME), (96, 84, FLAME_Y), (140, 56, FLAME),
                       (184, 74, FLAME), (228, 50, FLAME_Y), (272, 66, FLAME)):
        cv.poly([(x + fx, y + h - 40), (x + fx + 15, y + h - 40 - fh),
                 (x + fx + 30, y + h - 40)], fc)
    # embers
    for ex, ey in ((70, 18), (130, 10), (200, 16), (260, 8), (310, 20)):
        cv.circle(x + ex, y + ey, 3, FLAME_Y)


# ---------------------------------------------------------------- page
def build():
    cv = Canvas(W, H, PAPER)
    M = 28  # margin

    # ---- masthead
    draw_text(cv, W // 2, 30, "THE WORLD", 9, INK, align="center")
    draw_text(cv, W // 2, 108, "MONDAY 23 NOVEMBER 2026", 2, INK_SOFT,
              align="center")
    draw_text(cv, M, 108, "ONE DAY", 2, RED)
    draw_text(cv, W - M, 108, "ONE IMAGE", 2, RED, align="right")
    cv.hline(M, 132, W - 2 * M, INK, 4)
    cv.hline(M, 140, W - 2 * M, INK, 2)

    # ---- lead story: COP31
    lx, ly, lw, lh = M, 152, W - 2 * M, 316
    cv.frame(lx, ly, lw, lh, INK, 2)
    scene_cop31(cv, lx + 2, ly + 2, 470, lh - 4)
    tx = lx + 500
    draw_text(cv, tx, ly + 22, "CLIMATE", 2, RED)
    draw_text(cv, tx, ly + 52, "COP31", 7, INK)
    draw_text(cv, tx, ly + 112, "COLLAPSES", 7, INK)
    draw_para(cv, tx, ly + 190,
              "Antalya talks end with no climate pact as "
              "fossil-fuel deadlock defeats 196 nations.", 2, INK_SOFT,
              lw - 500 - 24, 22)
    draw_text(cv, tx, ly + 266, "ANTALYA, TURKIYE", 2, GREY)

    # ---- row 2: Hormuz + Kyiv
    ry, rh = 484, 236
    pw = (W - 2 * M - 16) // 2
    # Hormuz
    hx = M
    cv.frame(hx, ry, pw, rh, INK, 2)
    scene_hormuz(cv, hx + 2, ry + 2, pw - 4, 118)
    draw_text(cv, hx + 14, ry + 132, "TANKERS HIT", 3, INK)
    draw_text(cv, hx + 14, ry + 162, "IN HORMUZ", 3, INK)
    draw_para(cv, hx + 14, ry + 196,
              "Two tankers struck in the Strait as the US-Iran "
              "standoff at sea deepens.", 2, INK_SOFT, pw - 28, 20)
    # Kyiv
    kx = M + pw + 16
    cv.frame(kx, ry, pw, rh, INK, 2)
    scene_kyiv(cv, kx + 2, ry + 2, pw - 4, 118)
    draw_text(cv, kx + 14, ry + 132, "KYIV STRUCK AS", 3, INK)
    draw_text(cv, kx + 14, ry + 162, "TRUCE TALK LOOMS", 3, INK)
    draw_para(cv, kx + 14, ry + 196,
              "Drone hits a building near Kyiv, 14 missing, as "
              "Trump pushes a truce.", 2, INK_SOFT, pw - 28, 20)

    # ---- row 3: Indonesia fire + day in brief
    by, bh = 736, 224
    fx = M
    fw = 380
    cv.frame(fx, by, fw, bh, INK, 2)
    scene_fire(cv, fx + 2, by + 2, fw - 4, 110)
    draw_text(cv, fx + 14, by + 120, "FACTORY FIRE:", 3, INK)
    draw_text(cv, fx + 14, by + 148, "24 DEAD, 30", 3, RED)
    draw_text(cv, fx + 14, by + 176, "MISSING", 3, RED)
    draw_text(cv, fx + 14, by + 206, "BANTEN, INDONESIA", 2, GREY)

    bx = M + fw + 16
    bw = W - 2 * M - fw - 16
    cv.frame(bx, by, bw, bh, INK, 2)
    draw_text(cv, bx + 16, by + 14, "THE DAY IN BRIEF", 3, INK)
    cv.hline(bx + 16, by + 48, bw - 32, INK, 2)
    briefs = [
        ("EU", "Big Tech tax in new budget draft."),
        ("SEOUL", "minister quits in AI exam scandal."),
        ("BANGLADESH", "30 houses ablaze in Narail."),
        ("LISBON", "thousands march over living costs."),
        ("MEXICO", "'El Chapo Isidro' captured; 11 dead."),
        ("CRICKET", "Pant's Test record 128 vs NZ."),
    ]
    yy = by + 58
    for tag, text in briefs:
        draw_text(cv, bx + 16, yy, tag, 2, RED)
        tx0 = bx + 16 + text_width(tag + "  ", 2)
        lines = wrap_text(text, 2, bw - 32 - text_width(tag + "  ", 2))
        for i, line in enumerate(lines):
            draw_text(cv, tx0, yy + i * 20, line, 2, INK_SOFT)
        yy += max(1, len(lines)) * 20 + 6

    # ---- footer
    cv.hline(M, 978, W - 2 * M, INK, 2)
    draw_text(cv, W // 2, 990, "DRAWN FROM THE DAY'S REPORTING  -  23 NOVEMBER 2026",
              2, GREY, align="center")

    return cv


def main():
    cv = build()
    data = png_bytes(cv)
    out = OUT
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "wb") as f:
        f.write(data)
    os.chmod(out, 0o644)
    print(f"wrote {out}: {len(data)} bytes, {W}x{H}")


if __name__ == "__main__":
    main()
