#!/usr/bin/env python3
"""
Tier表の画像を自動で作る。

    python scripts/make_images.py            # 全Tier表（画像が無いもの・YAMLが新しいものだけ）
    python scripts/make_images.py --all      # 全部作り直す
    python scripts/make_images.py neko-omocha  # 1つだけ

出力:
    og/<slug>.png            … 1200x630  サイトのシェア画像（build.py が dist/og/ にコピー）
    sns/<slug>_9x16.png      … 1080x1920 リール・TikTok・ショート用の縦長画像
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
TIERS_DIR = ROOT / "content" / "tiers"
OG_DIR = ROOT / "og"
SNS_DIR = ROOT / "sns"
SITE = yaml.safe_load((ROOT / "data" / "site.yaml").read_text(encoding="utf-8"))

RANKS = ["S", "A", "B", "C", "D"]
COLORS = {"S": "#ff6b6b", "A": "#ffa94d", "B": "#ffd43b", "C": "#8ce99a", "D": "#74c0fc"}
BG, PANEL, INK, MUTED = "#fffaf5", "#ffffff", "#2b2330", "#8a7f8f"

FONT_BOLD = "C:/Windows/Fonts/YuGothB.ttc"
FONT_REG = "C:/Windows/Fonts/YuGothM.ttc"


def font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def fit_text(draw, text, max_w, size, bold=True, min_size=18):
    """幅に収まるまで文字を小さくする"""
    while size > min_size:
        f = font(size, bold)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 2
    return font(min_size, bold)


def wrap_chips(draw, names, f, max_w, pad_x, gap):
    """項目名をチップにして、行ごとに分ける"""
    lines, cur, w = [], [], 0
    for n in names:
        cw = draw.textlength(n, font=f) + pad_x * 2
        if cur and w + cw > max_w:
            lines.append(cur)
            cur, w = [], 0
        cur.append((n, cw))
        w += cw + gap
    if cur:
        lines.append(cur)
    return lines


def draw_tier(img, box, rows, chip_size):
    """box=(x0,y0,x1,y1) にTier表を描く。文字が溢れたら小さくして描き直す"""
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(img)
    label_w = int(chip_size * 2.6)
    row_gap = int(chip_size * 0.35)
    size = chip_size
    while True:
        f = font(size)
        pad_x, gap, chip_h = int(size * .6), int(size * .35), int(size * 1.7)
        layouts = {r: wrap_chips(d, rows[r], f, x1 - x0 - label_w - 24, pad_x, gap) or [[]] for r in RANKS}
        heights = {r: max(len(layouts[r]) * (chip_h + gap) + gap, int(chip_size * 2.2)) for r in RANKS}
        total = sum(heights.values()) + row_gap * 4
        if total <= y1 - y0 or size <= 16:
            break
        size -= 2
    # 余った高さは各行に均等に配る
    extra = max(0, (y1 - y0) - total) // 5
    y = y0
    for r in RANKS:
        h = heights[r] + extra
        d.rounded_rectangle((x0, y, x0 + label_w, y + h), 16, fill=COLORS[r])
        d.rectangle((x0 + label_w - 16, y, x0 + label_w, y + h), fill=COLORS[r])
        d.rounded_rectangle((x0 + label_w, y, x1, y + h), 16, fill=PANEL, outline="#eee3ea", width=2)
        lf = font(int(chip_size * 1.5))
        d.text((x0 + label_w / 2, y + h / 2), r, font=lf, fill="#222", anchor="mm")
        cy = y + (h - len(layouts[r]) * (chip_h + gap) + gap) / 2
        for line in layouts[r]:
            cx = x0 + label_w + 14
            for n, cw in line:
                d.rounded_rectangle((cx, cy, cx + cw, cy + chip_h), 12, fill=BG, outline="#eee3ea", width=2)
                d.text((cx + cw / 2, cy + chip_h / 2), n, font=f, fill=INK, anchor="mm")
                cx += cw + gap
            cy += chip_h + gap
        y += h + row_gap


def make(slug: str, data: dict) -> None:
    rows = {r: [str(x["name"] if isinstance(x, dict) else x) for x in (data["tiers"].get(r) or [])]
            for r in RANKS}
    title = data["title"]

    # 横長 1200x630（OG）
    img = Image.new("RGB", (1200, 630), BG)
    d = ImageDraw.Draw(img)
    d.text((48, 36), title, font=fit_text(d, title, 1104, 48), fill=INK)
    draw_tier(img, (48, 112, 1152, 570), rows, 22)
    d.text((1152, 600), f"{SITE['name']}｜ランク付け：{SITE['ranker']}", font=font(20, False),
           fill=MUTED, anchor="rm")
    OG_DIR.mkdir(exist_ok=True)
    img.save(OG_DIR / f"{slug}.png", optimize=True)

    # 縦長 1080x1920（リール・TikTok・ショート）
    # 上下はアプリのUIで隠れるので、大事な情報は中央寄せ
    img = Image.new("RGB", (1080, 1920), BG)
    d = ImageDraw.Draw(img)
    d.text((540, 250), "AIが決めた", font=font(44, False), fill=MUTED, anchor="mm")
    lines = split_title(d, title.replace(" Tier表", ""), 960, 76)
    ty = 330
    for ln, f in lines:
        d.text((540, ty), ln, font=f, fill=INK, anchor="mt")
        ty += f.size + 16
    d.text((540, ty + 10), "Tier表", font=font(56), fill=COLORS["S"], anchor="mt")
    draw_tier(img, (60, ty + 110, 1020, 1620), rows, 34)
    d.text((540, 1680), "理由はサイトで → " + SITE["name"], font=font(34, False), fill=MUTED, anchor="mm")
    SNS_DIR.mkdir(exist_ok=True)
    img.save(SNS_DIR / f"{slug}_9x16.png", optimize=True)


def split_title(d, text, max_w, size):
    """長いタイトルは2行に分ける"""
    f = font(size)
    if d.textlength(text, font=f) <= max_w:
        return [(text, f)]
    # 助詞や記号の直後で、真ん中にいちばん近い位置で切る
    cands = [i + 1 for i, ch in enumerate(text[:-1]) if ch in " のもでがはをにと、・"]
    cut = min(cands, key=lambda c: abs(c - len(text) / 2)) if cands else len(text) // 2
    a, b = text[:cut].strip(), text[cut:].strip()
    f = fit_text(d, max(a, b, key=len), max_w, size)
    return [(a, f), (b, f)]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    force = "--all" in args
    only = [a for a in args if not a.startswith("--")]
    n = 0
    for p in sorted(TIERS_DIR.glob("*.yaml")):
        if p.name.startswith("_") or (only and p.stem not in only):
            continue
        out = OG_DIR / f"{p.stem}.png"
        if not force and not only and out.exists() and out.stat().st_mtime >= p.stat().st_mtime:
            continue
        make(p.stem, yaml.safe_load(p.read_text(encoding="utf-8")))
        n += 1
        print("🖼", p.stem)
    print(f"✅ 画像 {n}件 作成（og/ と sns/）")


if __name__ == "__main__":
    main()
