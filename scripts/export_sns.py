#!/usr/bin/env python3
"""
SNS用の素材（動画・縦画像・横画像）を、避難所の「ティアる/SNS素材」へ、分かる名前で整理して出す。

    python scripts/export_sns.py --series pet     # シリーズ全部
    python scripts/export_sns.py inu-kiken pet-fuyu-kiken
    python scripts/export_sns.py --all

出力：C:/Users/himic/HIMEKA避難所/ティアる/SNS素材/<グループ名>/<題名>.mp4 ／ <題名>_縦.png ／ <題名>_横.png
      と、一覧 SNS素材/README_一覧.md（題名・ページURL・ファイル名）

前提：動画は make_videos.py（sns/video/ に作る＝作業用の置き場）、画像は make_images.py（sns/・og/）で先に作っておく。
※ tier-site/sns/ は作業用（gitに入れない）。さくらが見る場所は、避難所のこのフォルダ。
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEST = Path(r"C:/Users/himic/HIMEKA避難所/ティアる/SNS素材")
TIERS = ROOT / "content" / "tiers"
BASE = "https://tierjp.com"


def safe(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "・", name).strip()


def load_series():
    return yaml.safe_load((ROOT / "data" / "series.yaml").read_text(encoding="utf-8"))["series"]


def load_cats():
    return {c["slug"]: c["name"] for c in yaml.safe_load((ROOT / "data" / "categories.yaml").read_text(encoding="utf-8"))["categories"]}


def folder_of(slug: str, category: str, series, cats, prefer: str | None) -> str:
    order = sorted(series, key=lambda s: (s["slug"] != prefer,))  # 指定シリーズを優先
    for s in order:
        for g in s["groups"]:
            if slug in g["tiers"]:
                return safe(g["name"])
    return safe(cats.get(category, category))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    series = load_series()
    cats = load_cats()
    slugs, prefer = [], None
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--series":
            prefer = args[i + 1]
            s = next(x for x in series if x["slug"] == prefer)
            for g in s["groups"]:
                slugs += [t for t in g["tiers"] if t not in slugs]
            i += 1
        elif a == "--all":
            slugs += [p.stem for p in sorted(TIERS.glob("*.yaml")) if not p.name.startswith("_")]
        elif not a.startswith("--"):
            slugs.append(a)
        i += 1
    if not slugs:
        raise SystemExit(__doc__)

    DEST.mkdir(parents=True, exist_ok=True)
    rows: dict[str, list[tuple[str, str, str, str]]] = {}
    n_v = n_i = 0
    for slug in dict.fromkeys(slugs):
        src = TIERS / f"{slug}.yaml"
        if not src.exists():
            print("  ✗ なし", slug); continue
        d = yaml.safe_load(src.read_text(encoding="utf-8"))
        title = safe(d["title"].replace(" Tier表", "").replace("Tier表", "").strip())
        folder = folder_of(slug, d.get("category", ""), series, cats, prefer)
        out = DEST / folder
        out.mkdir(parents=True, exist_ok=True)
        got = []
        for srcp, dst in (
            (ROOT / "sns" / "video" / f"{slug}.mp4", out / f"{title}.mp4"),
            (ROOT / "sns" / f"{slug}_9x16.png", out / f"{title}_縦.png"),
            (ROOT / "og" / f"{slug}.png", out / f"{title}_横.png"),
        ):
            if srcp.exists():
                if not dst.exists() or dst.stat().st_mtime < srcp.stat().st_mtime:
                    shutil.copy2(srcp, dst)
                got.append(dst.suffix == ".mp4" and "動画" or ("縦" if "縦" in dst.name else "横"))
                n_v += dst.suffix == ".mp4"
                n_i += dst.suffix == ".png"
        rows.setdefault(folder, []).append((title, f"{BASE}/tier/{slug}/", "・".join(got) or "（まだ無い）", slug))

    # 一覧
    lines = ["# SNS素材 一覧", "",
             "ティアる。（tierjp.com）の、SNS投稿用の動画・画像です。**フォルダ＝グループ名、ファイル名＝Tier表の題名**。",
             "- `○○.mp4` … 発表アニメの縦動画（約9秒・1080×1920・無音）。**音はアプリで流行りの曲を付ける**",
             "- `○○_縦.png` … 縦長画像（リール・TikTok・ストーリーズ用）",
             "- `○○_横.png` … 横長画像（X・ブログ用）",
             "- 投稿文（キャプション）の案は `ティアる/ペットシリーズSNS告知_2週間分.md`",
             "- 足りない素材が欲しいときは、Claudeに「○○の動画（画像）作って」と言えばOK", ""]
    existing = {}
    for folder in sorted(p.name for p in DEST.iterdir() if p.is_dir()):
        n = len(list((DEST / folder).glob("*.mp4")))
        lines.append(f"## {folder}（動画{n}本）")
        lines.append("")
        lines.append("| 題名 | ページ |")
        lines.append("|---|---|")
        for mp in sorted((DEST / folder).glob("*.mp4")):
            t = mp.stem
            slug = next((s for (tt, u, g, s) in rows.get(folder, []) if tt == t), None)
            url = f"{BASE}/tier/{slug}/" if slug else ""
            lines.append(f"| {t} | {url} |")
        lines.append("")
    (DEST / "README_一覧.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ 動画 {n_v} 本・画像 {n_i} 枚 → {DEST}")


if __name__ == "__main__":
    main()
