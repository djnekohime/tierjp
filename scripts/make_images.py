#!/usr/bin/env python3
"""
Tier表の画像を自動で作る（夜空×ピンクのネオン）。

    python scripts/make_images.py              # 画像が無いもの・YAMLが新しいものだけ
    python scripts/make_images.py --all        # 全部作り直す
    python scripts/make_images.py neko-omocha  # 1つだけ

出力:
    og/<slug>.png            … 1200x630  サイトのシェア画像（build.py が dist/og/ にコピー）
    sns/<slug>_9x16.png      … 1080x1920 リール・TikTok・ショート用の縦長画像
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
TIERS_DIR = ROOT / "content" / "tiers"
OG_DIR = ROOT / "og"
SNS_DIR = ROOT / "sns"
SITE = yaml.safe_load((ROOT / "data" / "site.yaml").read_text(encoding="utf-8"))
URL = "tierjp.com"

RANKS = ["S", "A", "B", "C", "D"]
GRAD = {"S": ("#ff4f8b", "#ff9a5a"), "A": ("#ff9f43", "#ffd166"), "B": ("#ffe45c", "#fff3a8"),
        "C": ("#5ef0b0", "#b4ffd9"), "D": ("#62b8ff", "#b8e0ff")}
NIGHT, NIGHT2, PANEL, PINK, PINK2, INK, MUTED = "#0d0b1f", "#241447", "#2a1f52", "#ff5fb8", "#ff9ad5", "#ffffff", "#b9acd9"

FONT_BOLD = "C:/Windows/Fonts/YuGothB.ttc"
FONT_REG = "C:/Windows/Fonts/YuGothM.ttc"
FONT_EMOJI = "C:/Windows/Fonts/seguiemj.ttf"


def font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def hex2rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def gradient(w, h, c1, c2, vertical=False):
    a, b = hex2rgb(c1), hex2rgb(c2)
    g = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(g)
    n = h if vertical else w
    for i in range(n):
        t = i / max(1, n - 1)
        col = tuple(int(a[k] + (b[k] - a[k]) * t) for k in range(3))
        d.line([(0, i), (w, i)] if vertical else [(i, 0), (i, h)], fill=col)
    return g


def night_bg(w, h, seed):
    """夜空：紺のグラデーション＋ピンクと紫のぼんやりした光＋星"""
    base = gradient(w, h, NIGHT, NIGHT2, vertical=True)
    glow = Image.new("RGB", (w, h), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((w * .55, -h * .25, w * 1.35, h * .45), fill=(110, 25, 80))
    gd.ellipse((-w * .4, h * .35, w * .45, h * 1.1), fill=(50, 30, 120))
    glow = glow.filter(ImageFilter.GaussianBlur(min(w, h) // 5))
    base = ImageChops.screen(base, glow)
    d = ImageDraw.Draw(base)
    rnd = random.Random(seed)
    for _ in range(w * h // 9000):
        x, y, r = rnd.randrange(w), rnd.randrange(h), rnd.choice([1, 1, 1, 2])
        d.ellipse((x - r, y - r, x + r, y + r), fill=rnd.choice(["#ffffff", "#ffd6f0", "#c9f4ff"]))
    return base


def rounded_mask(w, h, r):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
    return m


def emoji_text(e: str) -> str:
    """Pillowは合成絵文字（🐈‍⬛など）をつなげられないので、先頭の1文字にする"""
    return e.split("\u200d")[0] if e else ""


def fit_text(draw, text, max_w, size, bold=True, min_size=14):
    while size > min_size:
        f = font(size, bold)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 1
    return font(min_size, bold)


def wrap2(draw, text, max_w, size):
    """タイル用：2行までに収める（入らなければ文字を小さくする）"""
    for s in range(size, int(size * .72) - 1, -1):   # まず少し小さくして1行に入るか試す
        f = font(s)
        if draw.textlength(text, font=f) <= max_w:
            return [text], f
    for s in range(size, 11, -1):
        f = font(s)
        lines, cur = [], ""
        for ch in text:
            if draw.textlength(cur + ch, font=f) > max_w:
                lines.append(cur)
                cur = ch
            else:
                cur += ch
        lines.append(cur)
        if len(lines) <= 2:
            return lines, f
    return [text[:8] + "…"], font(12)


def draw_board(img, box, rows, tile):
    """box内にTier表を描く。tile=タイルの基準サイズ（溢れたら自動で小さくする）"""
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(img)
    while True:
        gap = max(6, tile // 12)
        label_w = int(tile * 0.95)
        per_row = max(1, (x1 - x0 - label_w - gap * 2) // (tile + gap))
        heights = {r: max(1, -(-len(rows[r]) // per_row)) * (tile + gap) + gap for r in RANKS}
        total = sum(heights.values()) + gap * 4
        if total <= y1 - y0 or tile <= 60:
            break
        tile -= 4
    extra = max(0, (y1 - y0) - total) // 5
    y = y0
    for r in RANKS:
        h = heights[r] + extra
        img.paste(Image.new("RGB", (x1 - x0, h), PANEL), (x0, y), rounded_mask(x1 - x0, h, 18))
        if r == "S":
            d.rounded_rectangle((x0, y, x1, y + h), 18, outline=GRAD["S"][0], width=3)
        lab = gradient(label_w, h, *GRAD[r])
        img.paste(lab, (x0, y), rounded_mask(label_w + 18, h, 18).crop((0, 0, label_w, h)))
        d.text((x0 + label_w / 2, y + h / 2), r, font=font(int(tile * .55)), fill="#1a1030", anchor="mm")
        items = rows[r]
        n_lines = -(-len(items) // per_row)
        cy = y + (h - n_lines * (tile + gap) + gap) / 2
        for idx, (name, emo) in enumerate(items):
            cx = x0 + label_w + gap + (idx % per_row) * (tile + gap)
            ty = cy + (idx // per_row) * (tile + gap)
            d.rounded_rectangle((cx, ty, cx + tile, ty + tile), 14, fill="#3a2d6b", outline="#5b4a94", width=2)
            e = emoji_text(emo)
            if e:
                ef = ImageFont.truetype(FONT_EMOJI, int(tile * .34))
                d.text((cx + tile / 2, ty + tile * .33), e, font=ef, anchor="mm", embedded_color=True)
            lines, f = wrap2(d, name, tile - 12, int(tile * .15))
            ly = ty + tile * (.72 if e else .5) - (len(lines) - 1) * f.size * .55
            for ln in lines:
                d.text((cx + tile / 2, ly), ln, font=f, fill=INK, anchor="mm")
                ly += f.size * 1.15
        y += h + gap


def split_title(d, text, max_w, size):
    """長いタイトルは助詞の後ろで2行に分ける"""
    f = font(size)
    if d.textlength(text, font=f) <= max_w:
        return [(text, f)]
    cands = [i + 1 for i, ch in enumerate(text[:-1]) if ch in " のもでがはをにと、・"]
    cut = min(cands, key=lambda c: abs(c - len(text) / 2)) if cands else len(text) // 2
    a, b = text[:cut].strip(), text[cut:].strip()
    f = fit_text(d, max(a, b, key=len), max_w, size)
    return [(a, f), (b, f)]


def neon_text(img, xy, text, f, anchor="mm", color=INK, glow=PINK):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).text(xy, text, font=f, fill=glow, anchor=anchor)
    layer = layer.filter(ImageFilter.GaussianBlur(10))
    img.paste(layer, (0, 0), layer)
    ImageDraw.Draw(img).text(xy, text, font=f, fill=color, anchor=anchor)


def make(slug: str, data: dict) -> None:
    rows = {r: [] for r in RANKS}
    for r in RANKS:
        for x in data["tiers"].get(r) or []:
            x = x if isinstance(x, dict) else {"name": x}
            rows[r].append((str(x["name"]), str(x.get("emoji") or "")))
    title = data["title"].replace(" Tier表", "")

    # 横長 1200x630（OG）
    img = night_bg(1200, 630, slug)
    d = ImageDraw.Draw(img)
    neon_text(img, (44, 50), title + " Tier表", fit_text(d, title + " Tier表", 1100, 44), anchor="lm")
    draw_board(img, (40, 92, 1160, 580), rows, 96)
    d.text((1160, 606), f"{SITE['name']}  {URL}", font=font(22), fill=PINK2, anchor="rm")
    d.text((40, 606), f"ランク付け：{SITE['ranker']}", font=font(18, False), fill=MUTED, anchor="lm")
    OG_DIR.mkdir(exist_ok=True)
    img.save(OG_DIR / f"{slug}.png", optimize=True)

    # 縦長 1080x1920（リール・TikTok・ショート）上下はアプリUIで隠れるので中央寄せ
    img = night_bg(1080, 1920, slug + "v")
    d = ImageDraw.Draw(img)
    d.text((540, 230), "AIが本気で決めた", font=font(42), fill=PINK2, anchor="mm")
    ty = 290
    for ln, f in split_title(d, title, 960, 80):
        neon_text(img, (540, ty + f.size / 2), ln, f)
        ty += f.size + 18
    neon_text(img, (540, ty + 34), "Tier表", font(60), color="#ffd1ea")
    draw_board(img, (50, ty + 100, 1030, 1640), rows, 150)
    neon_text(img, (540, 1700), f"{SITE['name']}  {URL}", font(40))
    d.text((540, 1756), "理由はサイトで →", font=font(30, False), fill=MUTED, anchor="mm")
    SNS_DIR.mkdir(exist_ok=True)
    img.save(SNS_DIR / f"{slug}_9x16.png", optimize=True)


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
