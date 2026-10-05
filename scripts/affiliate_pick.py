#!/usr/bin/env python3
"""
楽天市場の商品検索API → data/affiliate_picks.json（ページごとの「おすすめ商品」候補）。

    python scripts/affiliate_pick.py --dry-run     # 何を検索するかだけ表示（鍵なしOK）
    python scripts/affiliate_pick.py               # 実行（鍵が必要）
    python scripts/affiliate_pick.py --only bousai-bichiku

鍵（リポジトリの外に置く）: 環境変数 RAKUTEN_APP_ID / RAKUTEN_ACCESS_KEY / RAKUTEN_AFFILIATE_ID
  または C:/Users/himic/.rakuten_keys に「名前=値」を1行ずつ。
選び方は機械的で事実ベース：レビュー平均・件数が基準以上、NG語なし、店の重複なし。
価格は載せない。効能は書かない。ルールは data/affiliate.yaml。
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONF = ROOT / "data" / "affiliate.yaml"
OUT = ROOT / "data" / "affiliate_picks.json"
KEYFILE = Path(r"C:\Users\himic\.rakuten_keys")
ENDPOINT = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"


def load_keys() -> dict:
    keys = {k: os.environ.get(k, "") for k in ("RAKUTEN_APP_ID", "RAKUTEN_ACCESS_KEY", "RAKUTEN_AFFILIATE_ID")}
    if KEYFILE.exists():
        for line in KEYFILE.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                keys.setdefault(k.strip(), "")
                if not keys.get(k.strip()):
                    keys[k.strip()] = v.strip()
    return keys


def search(keys: dict, keyword: str) -> list[dict]:
    q = urllib.parse.urlencode({
        "applicationId": keys["RAKUTEN_APP_ID"], "accessKey": keys["RAKUTEN_ACCESS_KEY"],
        "affiliateId": keys["RAKUTEN_AFFILIATE_ID"], "keyword": keyword,
        "hits": 30, "imageFlag": 1, "availability": 1, "format": "json",
    })
    req = urllib.request.Request(f"{ENDPOINT}?{q}", headers={"User-Agent": "tierjp-affiliate/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))
    out = []
    for it in data.get("Items", []):
        it = it.get("Item", it)
        out.append(it)
    return out


def first_image(it: dict) -> str:
    imgs = it.get("mediumImageUrls") or []
    if imgs:
        x = imgs[0]
        return x.get("imageUrl", "") if isinstance(x, dict) else str(x)
    return ""


def pick_for(keys: dict, slug: str, tgt: dict, conf: dict) -> list[dict]:
    picks, shops = [], set()
    for kw in tgt["queries"]:
        if len(picks) >= conf["max_per_page"]:
            break
        try:
            items = search(keys, kw)
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠ {slug} / {kw}: {e}")
            continue
        time.sleep(1.2)  # APIにやさしく
        good = []
        for it in items:
            name = it.get("itemName", "")
            if any(w in name for w in conf["ng_words"]):
                continue
            avg, cnt = float(it.get("reviewAverage") or 0), int(it.get("reviewCount") or 0)
            if avg < conf["min_review_average"] or cnt < conf["min_review_count"]:
                continue
            if it.get("shopName") in shops or not it.get("affiliateUrl") or not first_image(it):
                continue
            good.append((cnt, avg, it))
        if not good:
            print(f"  – {slug} / {kw}: 基準を満たす商品なし")
            continue
        cnt, avg, it = max(good, key=lambda x: (x[0], x[1]))
        shops.add(it.get("shopName"))
        picks.append({
            "query": kw, "name": it["itemName"][:48], "url": it["affiliateUrl"], "image": first_image(it),
            "shop": it.get("shopName", ""), "review_average": avg, "review_count": cnt,
            "picked": date.today().isoformat(),
        })
        print(f"  ✔ {slug} / {kw}: {it['itemName'][:30]}… ★{avg}（{cnt}件）")
    return picks


def main() -> None:
    conf = yaml.safe_load(CONF.read_text(encoding="utf-8"))
    only = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--only=")), None)
    targets = {s: t for s, t in conf["targets"].items() if not only or s == only}
    if "--dry-run" in sys.argv:
        for s, t in targets.items():
            print(f"{s}: {t['heading']} ← {t['queries']}")
        print(f"（鍵なしの確認のみ。enabled={conf['enabled']}）")
        return
    keys = load_keys()
    miss = [k for k in ("RAKUTEN_APP_ID", "RAKUTEN_ACCESS_KEY", "RAKUTEN_AFFILIATE_ID") if not keys.get(k)]
    if miss:
        sys.exit(f"鍵が足りません: {miss}（{KEYFILE} か環境変数）")
    result = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    for slug, tgt in targets.items():
        print(slug)
        picks = pick_for(keys, slug, tgt, conf)
        if picks:
            result[slug] = {"heading": tgt["heading"], "picks": picks}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✅ {len(result)} ページ分 → {OUT.name}")


if __name__ == "__main__":
    main()
