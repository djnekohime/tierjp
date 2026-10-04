#!/usr/bin/env python3
"""
Tier表の「発表アニメ」縦動画（リール・TikTok・ショート用）を作る。

    python scripts/make_videos.py --series pet          # シリーズの全ページ
    python scripts/make_videos.py pet-fuyu-kiken inu-kiken   # slugを指定
    python scripts/make_videos.py --all                 # 全Tier表（時間がかかる）
    python scripts/make_videos.py --force ...           # 作り直す

動き：タイトルが出る → D → C → B → A → S の順に1段ずつフェードで登場（最後にSが決まる）。
約9秒・1080x1920・無音の音声トラック付き（音はアプリで流行りの曲を付ける）。
出力：sns/video/<slug>.mp4（gitに入れない）
要：ffmpeg（PATHに無ければ WinGet の場所を探す）
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import make_images as mi  # noqa: E402

OUT = ROOT / "sns" / "video"
TMP = ROOT / "sns" / "_frames"
TOTAL = 9.0
FADE = 0.28


def find_ffmpeg() -> str:
    p = shutil.which("ffmpeg")
    if p:
        return p
    base = Path.home() / "AppData/Local/Microsoft/WinGet/Packages"
    for c in base.glob("Gyan.FFmpeg*/ffmpeg-*/bin/ffmpeg.exe"):
        return str(c)
    raise SystemExit("ffmpeg が見つかりません")


def draw_board_reveal(img, box, rows, tile, show):
    """draw_board と同じ配置で、show に入っているランクの行だけ描く"""
    x0, y0, x1, y1 = box
    RANKS = mi.RANKS
    last = max((i for i, r in enumerate(RANKS) if rows[r]), default=len(RANKS) - 1)
    ranks = RANKS[:last + 1]
    d = ImageDraw.Draw(img)
    while True:
        gap = max(6, tile // 12)
        label_w = int(tile * 0.95)
        per_row = max(1, (x1 - x0 - label_w - gap * 2) // (tile + gap))
        heights = {r: max(1, -(-len(rows[r]) // per_row)) * (tile + gap) + gap for r in ranks}
        total = sum(heights.values()) + gap * (len(ranks) - 1)
        if total <= y1 - y0 or tile <= 60:
            break
        tile -= 4
    extra = min(tile, max(0, (y1 - y0) - total) // len(ranks))
    y = y0 + max(0, (y1 - y0) - total - extra * len(ranks)) // 2
    for r in ranks:
        h = heights[r] + extra
        if r in show:
            img.paste(Image.new("RGB", (x1 - x0, h), mi.PANEL), (x0, y), mi.rounded_mask(x1 - x0, h, 18))
            if r == "S":
                d.rounded_rectangle((x0, y, x1, y + h), 18, outline=mi.GRAD["S"][0], width=3)
            lab = mi.gradient(label_w, h, *mi.GRAD[r])
            img.paste(lab, (x0, y), mi.rounded_mask(label_w + 18, h, 18).crop((0, 0, label_w, h)))
            d.text((x0 + label_w / 2, y + h / 2), r, font=mi.font(int(tile * .55)), fill="#1a1030", anchor="mm")
            items = rows[r]
            n_lines = -(-len(items) // per_row)
            cy = y + (h - n_lines * (tile + gap) + gap) / 2
            for idx, (name, emo) in enumerate(items):
                cx = x0 + label_w + gap + (idx % per_row) * (tile + gap)
                ty = cy + (idx // per_row) * (tile + gap)
                d.rounded_rectangle((cx, ty, cx + tile, ty + tile), 14, fill="#3a2d6b", outline="#5b4a94", width=2)
                e = mi.emoji_text(emo)
                if e:
                    ef = ImageFont.truetype(mi.FONT_EMOJI, int(tile * .34))
                    d.text((cx + tile / 2, ty + tile * .33), e, font=ef, anchor="mm", embedded_color=True)
                lines, f = mi.wrap2(d, name, tile - 12, int(tile * .15))
                ly = ty + tile * (.72 if e else .5) - (len(lines) - 1) * f.size * .55
                for ln in lines:
                    d.text((cx + tile / 2, ly), ln, font=f, fill=mi.INK, anchor="mm")
                    ly += f.size * 1.15
        y += h + gap
    return ranks


def build_states(slug: str, data: dict):
    rows = {r: [] for r in mi.RANKS}
    for r in mi.RANKS:
        for x in data["tiers"].get(r) or []:
            x = x if isinstance(x, dict) else {"name": x}
            rows[r].append((str(x.get("short") or mi.short_name(str(x["name"]))), str(x.get("emoji") or "")))
    title = data["title"].replace(" Tier表", "").replace("Tier表", "").strip()
    last = max((i for i, r in enumerate(mi.RANKS) if rows[r]), default=len(mi.RANKS) - 1)
    ranks = mi.RANKS[:last + 1]
    order = list(reversed(ranks))               # D → ... → S
    states = []
    for k in range(len(order) + 1):             # 0 = タイトルだけ
        show = set(order[:k])
        img = mi.night_bg(1080, 1920, slug + "v")
        d = ImageDraw.Draw(img)
        d.text((540, 230), "AIが本気で決めた", font=mi.font(42), fill=mi.PINK2, anchor="mm")
        ty = 290
        for ln, f in mi.split_title(d, title, 960, 80):
            mi.neon_text(img, (540, ty + f.size / 2), ln, f)
            ty += f.size + 18
        mi.neon_text(img, (540, ty + 34), "Tier表", mi.font(60), color="#ffd1ea")
        draw_board_reveal(img, (50, ty + 100, 1030, 1640), rows, 150, show)
        mi.neon_text(img, (540, 1700), f"{mi.SITE['name']}  {mi.URL}", mi.font(40))
        d.text((540, 1756), "理由はサイトで →", font=mi.font(30, False), fill=mi.MUTED, anchor="mm")
        states.append(img)
    return states


def encode(slug: str, states, ffmpeg: str):
    TMP.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, im in enumerate(states):
        p = TMP / f"{slug}_{i}.png"
        im.save(p)
        paths.append(p)
    n = len(paths)
    # 見せる時間：タイトル1.0s → 各段0.85s → 最後（S）は残り全部
    d = [1.0] + [0.85] * (n - 2)
    # 総尺が TOTAL になるように最後を決める（フェード分の重なりを考慮）
    # 総尺 = Σd[:-1] + d_last + FADE*(n-1) のぶん。最後を逆算
    d_last = max(2.0, TOTAL - sum(d) - FADE * (n - 1) + FADE * (n - 1) * 0)  # 重なり分は offset 計算側で吸収
    d.append(d_last)
    inputs, lens = [], []
    for i, p in enumerate(paths):
        L = d[i] + (FADE if i < n - 1 else 0) + (FADE if i > 0 and i < n - 1 else 0)
        lens.append(L)
        inputs += ["-loop", "1", "-t", f"{L:.3f}", "-i", str(p)]
    # xfade チェーン
    filt, cur, label = [], lens[0], "[0:v]"
    for i in range(1, n):
        off = cur - FADE
        out = f"[v{i}]"
        filt.append(f"{label}[{i}:v]xfade=transition=fade:duration={FADE}:offset={off:.3f}{out}")
        cur = off + lens[i]
        label = out
    total = cur
    dst = OUT / f"{slug}.mp4"
    cmd = [ffmpeg, "-v", "error", "-y", *inputs, "-f", "lavfi", "-t", f"{total:.3f}", "-i", "anullsrc=r=44100:cl=stereo",
           "-filter_complex", ";".join(filt) + f";{label}format=yuv420p,fps=30[vout]",
           "-map", "[vout]", "-map", f"{n}:a", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart", "-t", f"{min(total, TOTAL + 0.5):.3f}", str(dst)]
    subprocess.run(cmd, check=True)
    for p in paths:
        p.unlink(missing_ok=True)
    return dst, total


def series_slugs(name: str) -> list[str]:
    data = yaml.safe_load((ROOT / "data" / "series.yaml").read_text(encoding="utf-8"))
    for s in data["series"]:
        if s["slug"] == name:
            out = []
            for g in s["groups"]:
                out += [t for t in g["tiers"] if t not in out]
            return out
    raise SystemExit(f"シリーズ {name} がありません")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    force = "--force" in args
    slugs: list[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--series":
            slugs += series_slugs(args[i + 1]); i += 1
        elif a == "--all":
            slugs += [p.stem for p in sorted(mi.TIERS_DIR.glob("*.yaml")) if not p.name.startswith("_")]
        elif not a.startswith("--"):
            slugs.append(a)
        i += 1
    seen, todo = set(), []
    for s in slugs:
        if s not in seen:
            seen.add(s); todo.append(s)
    if not todo:
        raise SystemExit(__doc__)
    ff = find_ffmpeg()
    done = 0
    for s in todo:
        dst = OUT / f"{s}.mp4"
        src = mi.TIERS_DIR / f"{s}.yaml"
        if not src.exists():
            print("  ✗ なし", s); continue
        if not force and dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
            continue
        data = yaml.safe_load(src.read_text(encoding="utf-8"))
        out, total = encode(s, build_states(s, data), ff)
        print(f"🎬 {s}  {total:.1f}s")
        done += 1
    shutil.rmtree(TMP, ignore_errors=True)
    print(f"✅ 動画 {done} 本 → sns/video/")


if __name__ == "__main__":
    main()
