"""食べ物ロードマップ（data/backlog_food.yaml）の進み具合と重複チェック。

  python scripts/backlog.py          # 集計＋似たタイトルの警告
  python scripts/backlog.py next 10  # 次に作る10本（step順・ジャンルが偏らないように1つずつ）
"""
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TIERS = ROOT / "content" / "tiers"


def norm(s: str) -> str:
    for w in ("Tier表", "の種類", "の具", " ", "　"):
        s = s.replace(w, "")
    return s


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    bl = yaml.safe_load((ROOT / "data" / "backlog_food.yaml").read_text(encoding="utf-8"))["genres"]
    existing = {}
    for f in TIERS.glob("*.yaml"):
        if f.stem.startswith("_"):
            continue
        d = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        existing[f.stem] = str(d.get("title", ""))

    rows = [(g, x) for g, xs in bl.items() for x in xs]
    done = [x for _, x in rows if x["slug"] in existing]
    todo = [(g, x) for g, x in rows if x["slug"] not in existing]

    if len(sys.argv) > 1 and sys.argv[1] == "next":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        picked, used = [], set()
        for step in sorted({x["step"] for _, x in todo}):
            while len(picked) < n:
                cand = [(g, x) for g, x in todo if x["step"] == step and (g, x["slug"]) not in {(p[0], p[1]["slug"]) for p in picked}]
                if not cand:
                    break
                fresh = [c for c in cand if c[0] not in used] or cand
                if not [c for c in cand if c[0] not in used]:
                    used.clear()
                g, x = fresh[0]
                used.add(g)
                picked.append((g, x))
        for g, x in picked:
            print(f"{x['slug']}\t{g}\t{x['title']}\t{x['kind']}")
        return

    food_now = sum(1 for s in existing if s.startswith(("food-", "shop-", "chain-")))
    print(f"ロードマップ {len(rows)}本（済 {len(done)}）＋ 既存の食べ物 {food_now}本 → 完成時 約{food_now + len(todo)}本")
    for k, v in sorted(Counter((x['step'], x['kind']) for _, x in todo).items()):
        print(f"  残り step{k[0]} {k[1]}: {v}本")

    # 似たタイトルの警告（既存と被ってないか）
    warn = 0
    for g, x in todo:
        a = norm(x["title"])
        for slug, t in existing.items():
            b = norm(t)
            if a and b and SequenceMatcher(None, a, b).ratio() >= 0.85 and not ("【" in a and "【" in b and a != b):
                print(f"  ⚠ 似てる？ {x['slug']}「{x['title']}」 ⇔ {slug}「{t}」")
                warn += 1
    slugs = Counter(x["slug"] for _, x in rows)
    for s, c in slugs.items():
        if c > 1:
            print(f"  ⚠ slug重複: {s}")
    if not warn:
        print("  重複の疑いなし")


main()
