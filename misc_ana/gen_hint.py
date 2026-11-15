#!/usr/bin/env python3
"""Generator gambar hint challenge Misc (OSINT script Nod-Krai).

Cara kerja (tanpa font, tanpa server):
  1. Baca sheet Nod-Krai_Script.webp (grid 7 kolom x 4 baris, glyph hitam,
     label huruf merah di bawah tiap glyph).
  2. Potong (patch) tiap glyph dari sheet memakai mask piksel gelap.
     Label merah otomatis terbuang karena bukan piksel gelap.
  3. Perbesar glyph (upscale + blur + threshold) supaya tepinya tajam,
     lalu tempel satu per satu menjadi baris-baris teks.
  4. Tulis hint.png. Plaintext TIDAK ikut tertulis di gambar.

Sheet hanya punya 23 glyph: J, Q, X tidak ada. Plaintext yang memakai
huruf itu akan ditolak dengan pesan error.

Pakai:
    python gen_hint.py                 # hasil: hint.png + glyph_check.png
    python gen_hint.py --text-file x.txt --out lain.png
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
SHEET = HERE / "Nod-Krai_Script.webp"

# Urutan huruf di sheet: baris demi baris, 7 kolom per baris.
SHEET_ORDER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
COLS, ROWS = 7, 4
MISSING = set("JQX")  # sel kosong di sheet

# Hint default: tiga kalimat deskripsi (jawaban ada di CSV/folder author).
DEFAULT_TEXT = """\
PRIMORDIAL HUMAN BORN FROM CRYO SOVEREIGN EGG
FOUNDER OF KITEZH AND PALE STAR COURT
SVAROG THE SOULLESS HUSK OF WHITE BIRCH
"""

UPSCALE = 8          # faktor upscale internal sebelum threshold
TARGET_BAND_H = 96   # tinggi band glyph pada gambar akhir (px)
LETTER_GAP = 14      # jarak antar glyph (px)
WORD_GAP = 64        # jarak antar kata (px)
LINE_GAP = 36        # jarak antar baris dalam satu kalimat (px)
PARA_GAP = 90        # jarak antar kalimat (px)
MAX_WIDTH = 1500     # lebar maksimum area teks sebelum wrap (px)
PAD = 70             # margin gambar (px)


def dark_mask(rgb: np.ndarray) -> np.ndarray:
    """Piksel glyph = semua kanal RGB gelap. Label merah (R tinggi) tersingkir.
    Hanya dipakai untuk mencari bbox; gambar glyph memakai tinta lunak."""
    return rgb.max(axis=2) < 140


def extract_glyphs() -> dict[str, Image.Image]:
    """Potong tiap glyph dari sheet. Hasil: huruf -> gambar L (255 = tinta)."""
    sheet = Image.open(SHEET).convert("RGB")
    rgb = np.asarray(sheet)
    mask = dark_mask(rgb)
    h, w = mask.shape
    cell_w = w / COLS
    cell_h = h / ROWS
    # Tinggi band glyph di tiap sel; sisanya (bawah) adalah label huruf.
    band_h = int(cell_h * 0.68)

    # Cari bbox tiap glyph dulu supaya semua glyph memakai y-range yang sama
    # per baris (baseline terjaga), tapi lebar dipangkas rapat.
    boxes: dict[str, tuple[int, int, int, int]] = {}
    for idx, ch in enumerate(SHEET_ORDER):
        if ch in MISSING:
            continue
        r, c = divmod(idx, COLS)
        x0, x1 = int(c * cell_w), int((c + 1) * cell_w)
        y0, y1 = int(r * cell_h), int(r * cell_h) + band_h
        sub = mask[y0:y1, x0:x1]
        ys, xs = np.nonzero(sub)
        if xs.size == 0:
            raise RuntimeError(f"Glyph {ch} kosong, cek pembagian grid")
        boxes[ch] = (x0 + xs.min(), x0 + xs.max() + 1, y0, y1)

    # Global top/bottom dari semua glyph dipakai sebagai band seragam.
    tops, bots = [], []
    for idx, ch in enumerate(SHEET_ORDER):
        if ch in MISSING:
            continue
        r = idx // COLS
        x0, x1, y0, y1 = boxes[ch]
        sub = mask[y0:y1, x0:x1]
        ys = np.nonzero(sub.any(axis=1))[0]
        tops.append(ys.min() + 0 - 0)  # relatif ke y0 baris
        bots.append(ys.max() + 1)
    band_top = int(min(tops))
    band_bot = int(max(bots))

    # Tinta lunak: 255 - kanal terterang. Hitam -> 255, putih -> 0, dan label
    # merah (R=255) -> 0, jadi tetap terbuang. Anti-alias tepi terjaga sehingga
    # glyph tidak membengkak seperti kalau memakai mask biner.
    ink = 255 - rgb.max(axis=2)

    glyphs: dict[str, Image.Image] = {}
    for idx, ch in enumerate(SHEET_ORDER):
        if ch in MISSING:
            continue
        x0, x1, y0, _ = boxes[ch]
        crop = ink[y0 + band_top : y0 + band_bot, x0:x1]
        glyphs[ch] = Image.fromarray(crop.astype(np.uint8), "L")
    return glyphs


def sharpen(img: Image.Image, scale: float) -> Image.Image:
    """Upscale halus lalu threshold -> tepi tajam ala vektor, lalu ke ukuran akhir."""
    big = img.resize(
        (img.width * UPSCALE, img.height * UPSCALE), Image.LANCZOS
    ).filter(ImageFilter.GaussianBlur(UPSCALE * 0.30))
    arr = np.asarray(big)
    big = Image.fromarray(((arr > 128) * 255).astype(np.uint8), "L")
    out_w = max(1, round(img.width * scale))
    out_h = max(1, round(img.height * scale))
    return big.resize((out_w, out_h), Image.LANCZOS)


def build_glyph_set() -> dict[str, Image.Image]:
    glyphs = extract_glyphs()
    any_h = next(iter(glyphs.values())).height
    scale = TARGET_BAND_H / any_h
    return {ch: sharpen(g, scale) for ch, g in glyphs.items()}


def layout_word(word: str, glyphs: dict[str, Image.Image]) -> Image.Image:
    width = sum(glyphs[c].width for c in word) + LETTER_GAP * (len(word) - 1)
    canvas = Image.new("L", (width, TARGET_BAND_H), 0)
    x = 0
    for c in word:
        canvas.paste(glyphs[c], (x, 0))
        x += glyphs[c].width + LETTER_GAP
    return canvas


def wrap_words(words: list[Image.Image]) -> list[list[Image.Image]]:
    lines, cur, cur_w = [], [], 0
    for w in words:
        add = w.width + (WORD_GAP if cur else 0)
        if cur and cur_w + add > MAX_WIDTH:
            lines.append(cur)
            cur, cur_w = [w], w.width
        else:
            cur.append(w)
            cur_w += add
    if cur:
        lines.append(cur)
    return lines


def render(text: str, glyphs: dict[str, Image.Image]) -> Image.Image:
    paragraphs = [p.strip().upper() for p in text.splitlines() if p.strip()]
    bad = sorted({c for p in paragraphs for c in p if c != " " and c not in glyphs})
    if bad:
        sys.exit(
            "Karakter tidak ada di sheet: " + " ".join(bad)
            + "  (hanya A-Z kecuali J, Q, X)"
        )

    blocks: list[list[list[Image.Image]]] = []
    for p in paragraphs:
        words = [layout_word(w, glyphs) for w in p.split()]
        blocks.append(wrap_words(words))

    total_h = 2 * PAD
    max_w = 0
    for bi, lines in enumerate(blocks):
        total_h += len(lines) * TARGET_BAND_H + (len(lines) - 1) * LINE_GAP
        if bi:
            total_h += PARA_GAP
        for ln in lines:
            lw = sum(w.width for w in ln) + WORD_GAP * (len(ln) - 1)
            max_w = max(max_w, lw)

    page = Image.new("L", (max_w + 2 * PAD, total_h), 255)
    y = PAD
    for bi, lines in enumerate(blocks):
        if bi:
            y += PARA_GAP
        for li, ln in enumerate(lines):
            if li:
                y += LINE_GAP
            x = PAD
            for w in ln:
                # w = mask tinta (255 = tinta): tempel sebagai hitam di atas putih
                page.paste(0, (x, y), w)
                x += w.width + WORD_GAP
            y += TARGET_BAND_H
    return page


def contact_sheet(glyphs: dict[str, Image.Image]) -> Image.Image:
    """Lembar cek untuk author: tiap glyph + hurufnya, buat verifikasi segmentasi."""
    from PIL import ImageDraw

    cell_w, cell_h = 150, TARGET_BAND_H + 50
    cols = 6
    rows = (len(glyphs) + cols - 1) // cols
    img = Image.new("RGB", (cols * cell_w, rows * cell_h), "white")
    d = ImageDraw.Draw(img)
    for i, (ch, g) in enumerate(sorted(glyphs.items())):
        cx, cy = (i % cols) * cell_w, (i // cols) * cell_h
        img.paste((0, 0, 0), (cx + (cell_w - g.width) // 2, cy + 10), g)
        d.text((cx + cell_w // 2 - 4, cy + TARGET_BAND_H + 20), ch, fill=(220, 0, 0))
    return img


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--text-file", type=Path, help="plaintext (satu kalimat per baris)")
    ap.add_argument("--out", type=Path, default=HERE / "hint.png")
    ap.add_argument("--check", type=Path, default=HERE / "glyph_check.png",
                    help="lembar cek segmentasi glyph (author only)")
    args = ap.parse_args()

    text = args.text_file.read_text(encoding="utf-8") if args.text_file else DEFAULT_TEXT
    glyphs = build_glyph_set()
    contact_sheet(glyphs).save(args.check)
    page = render(text, glyphs)
    page.save(args.out, optimize=True)
    print(f"OK  {args.out.name}  {page.width}x{page.height}  glyph={len(glyphs)}")


if __name__ == "__main__":
    main()
