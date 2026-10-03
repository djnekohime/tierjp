#!/usr/bin/env python3
"""
ペット×季節の更新カレンダー（data/backlog_pet_season.yaml）を見て、今月作るものを表示する。

    python scripts/season.py        今月
    python scripts/season.py 4      4月
    python scripts/season.py next   来月（先取り用）
    python scripts/season.py all    全月の進み具合

content/tiers/<slug>.yaml があれば「済」、無ければ「未」。
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CAL = yaml.safe_load((ROOT / "data" / "backlog_pet_season.yaml").read_text(encoding="utf-8"))["months"]
TIERS = ROOT / "content" / "tiers"


def show(m: int) -> None:
    e = CAL[m]
    print(f"■ {m}月：{e['theme']}")
    for i in e["ideas"]:
        done = (TIERS / f"{i['slug']}.yaml").exists()
        print(f"  {'済' if done else '未'}  {i['slug']:<26} {i['title']}")


def main() -> None:
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    today = date.today().month
    if arg == "all":
        for m in range(1, 13):
            show(m)
        return
    if arg == "next":
        m = today % 12 + 1
    elif arg.isdigit() and 1 <= int(arg) <= 12:
        m = int(arg)
    else:
        m = today
    show(m)
    print("\n作ったら: python scripts/make_images.py → python build.py → site.yaml の featured を旬に → 投票用Workerを再デプロイ → push")


if __name__ == "__main__":
    main()
