#!/usr/bin/env python3
"""
コーディクスの毎日の完成画像 → SNS用「投稿パック」（キャプション・ハッシュタグ・使う曲）を作る。

    python scripts/make_post_pack.py 2026-10-06      # その日の output/<日付>/完成画像/ を読む
    python scripts/make_post_pack.py                 # 今日の日付

出力: C:/Users/himic/HIMEKA避難所/ティアる/投稿パック/<日付>.md
さくらがやること＝アプリで「曲（サウンド）を選ぶ」→ 画像を選ぶ → キャプションを貼る → 投稿。
曲はアプリのライブラリから選ぶ（使用回数と収益に数えられるため）。曲の選び方は SOUND_RULES。
キャプションは事実だけ（ページの題名と、Sランクの項目名）。効能や誇張は書かない。
"""

from __future__ import annotations

import difflib
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TIERS = ROOT / "content" / "tiers"
WORK = Path(r"C:\Users\himic\HIMEKA避難所\ティアる")

# 曲の選び方（TikTokサウンド収益の実績：1本あたり視聴＝素敵な一日2,587／English Fun Song 2,018／君のことが好きすぎる1,343／let's go 1,114）
DEFAULT_SOUND = "素敵な一日"
SOUND_RULES = [
    (("eigo", "英語", "英検"), "English Fun Song"),
    (("kanryu", "kandrama", "韓国", "BTS", "bts", "ラブコメ", "恋"), "君のことが好きすぎる"),
    (("music", "音楽", "作業用", "BGM"), "let's go"),
]
BASE_TAGS = ["#ティアる", "#Tier表", "#ランキング"]


def load_tiers() -> list[dict]:
    out = []
    for f in TIERS.glob("*.yaml"):
        d = yaml.safe_load(f.read_text(encoding="utf-8"))
        d["slug"] = f.stem
        out.append(d)
    return out


def norm(s: str) -> str:
    return s.replace(" レトロTier表", "").replace(" Tier表", "").replace("Tier表", "").replace(" ", "").replace("　", "")


def find_tier(name: str, tiers: list[dict]) -> dict | None:
    key = norm(Path(name).stem)
    best, score = None, 0.0
    for t in tiers:
        r = difflib.SequenceMatcher(None, key, norm(t["title"])).ratio()
        if r > score:
            best, score = t, r
    return best if score >= 0.6 else None


def pick_sound(t: dict) -> str:
    hay = " ".join([t["slug"], t["title"], t.get("category", ""), " ".join(t.get("tags", []))])
    for keys, sound in SOUND_RULES:
        if any(k in hay for k in keys):
            return sound
    return DEFAULT_SOUND


def s_items(t: dict, n: int = 3) -> list[str]:
    items = (t.get("tiers", {}) or {}).get("S", []) or []
    return [i.get("short") or i["name"] for i in items[:n]]


def main() -> None:
    day = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    src = WORK / "output" / day / "完成画像"
    if not src.exists() or not list(src.glob("*.png")):
        print(f"まだ画像がありません（{src}）。コーディクスの完成後にもう一度。")
        return
    tiers = load_tiers()
    imgs = sorted(src.glob("*.png"))
    lines = [f"# 投稿パック {day}（{len(imgs)}枚）", "",
             "やること：①アプリで曲を選ぶ（下の「曲」）②画像を選ぶ ③キャプションを貼る ④投稿。リンクは**プロフィールのリンク**（tierjp.com）。",
             "TikTok＝画像（写真モード）に曲、Instagram＝リールまたは画像に曲。投稿文には楽天のリンクは貼らない（押せない・PR表記が必要なため）。", ""]
    for p in imgs:
        t = find_tier(p.name, tiers)
        if not t:
            lines += [f"## {p.stem}", f"- 画像：`{p}`", "- ⚠ 対応するTier表ページが見つかりません（公開前？）", ""]
            continue
        sound = pick_sound(t)
        title = t["title"].replace(" Tier表", "")
        top = "・".join(f"「{x}」" for x in s_items(t))
        tags = BASE_TAGS + [f"#{x}" for x in t.get("tags", [])[:3]]
        cap = (f"【{title}】Tier表\nAIが決めたSランクは、{top}。\nあなたのSランクは？ コメントで教えてね👇\n"
               f"全部のランクと理由は、プロフのリンクから（tierjp.com）\n" + " ".join(tags))
        lines += [f"## {title}", f"- 画像：`{p}`", f"- ページ：https://tierjp.com/tier/{t['slug']}/",
                  f"- 曲：**{sound}**（アプリのライブラリから選ぶ）", "", "```", cap, "```", ""]
    out = WORK / "投稿パック"
    out.mkdir(exist_ok=True)
    f = out / f"{day}.md"
    f.write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ {f}（{len(imgs)}枚）")
    # iPhone（OneDriveアプリ）から使えるように、画像とパックを OneDrive にもコピー
    import shutil
    od = Path(r"C:\Users\himic\OneDrive\ティアる投稿") / day
    od.mkdir(parents=True, exist_ok=True)
    for img in imgs:
        shutil.copy2(img, od / img.name)
    shutil.copy2(f, od / "00_投稿パック.md")
    print(f"✅ OneDriveへコピー → {od}")


if __name__ == "__main__":
    main()
