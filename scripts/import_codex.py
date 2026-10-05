#!/usr/bin/env python3
"""
コーディクスが作った「完成画像」（1080x1920）を、サイトに取り込む。

    python scripts/import_codex.py          # completed.json に載っている分を全部取り込む

入力: C:/Users/himic/HIMEKA避難所/ティアる/production/completed.json
      （slug と、完成画像の場所が入っている。status が complete のものだけ使う）
出力: codex/<slug>.webp      … ページに載せるまとめ画像（縦長・そのまま）
      og_codex/<slug>.jpg    … シェア用 1200x630（画像の上のタイトル部分を切り出し）
build.py が codex/ と og_codex/ を見て、あるページだけ自動で差し替える。無いページは今まで通り。
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
WORK = Path(r"C:\Users\himic\HIMEKA避難所\ティアる")
COMPLETED = WORK / "production" / "completed.json"
TIERS_DIR = ROOT / "content" / "tiers"
OUT_FULL = ROOT / "codex"
OUT_OG = ROOT / "og_codex"


def main() -> None:
    OUT_FULL.mkdir(exist_ok=True)
    OUT_OG.mkdir(exist_ok=True)
    entries = json.loads(COMPLETED.read_text(encoding="utf-8"))
    done = skipped = 0
    for e in entries:
        slug = e.get("slug", "")
        if e.get("status") != "complete" or not (TIERS_DIR / f"{slug}.yaml").exists():
            print(f"⏭ {slug}: 取り込まない（未完成 or Tier表が無い）")
            skipped += 1
            continue
        src = WORK / e["file"]
        if not src.exists():
            print(f"⚠ {slug}: 画像が見つからない {src}")
            skipped += 1
            continue
        im = Image.open(src).convert("RGB")
        if im.size != (1080, 1920):
            print(f"⚠ {slug}: サイズが違う {im.size}")
            skipped += 1
            continue
        im.save(OUT_FULL / f"{slug}.webp", quality=84, method=6)
        og = im.crop((0, 0, 1080, 567)).resize((1200, 630), Image.LANCZOS)
        og.save(OUT_OG / f"{slug}.jpg", quality=88)
        print(f"🖼 {slug}")
        done += 1
    print(f"✅ 取り込み {done} 件 / スキップ {skipped} 件")


if __name__ == "__main__":
    main()
