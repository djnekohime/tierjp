#!/usr/bin/env python3
"""
既存のTier表（content/tiers/*.yaml）に項目を追記する道具。
YAMLの書式やコメントを崩さないよう、テキストとして該当ランクの末尾に差し込む。

    from add_items import add
    add("neko-omocha", [
        {"rank": "A", "name": "キャットタワー", "emoji": "🗼", "reason": "…"},
    ])
"""

from __future__ import annotations

import re
from pathlib import Path

TIERS_DIR = Path(__file__).resolve().parent.parent / "content" / "tiers"
RANKS = ["S", "A", "B", "C", "D"]


def q(s: str) -> str:
    """YAMLで安全な文字列（シングルクォートで囲む）"""
    return "'" + str(s).replace("'", "''") + "'"


def fmt(item: dict) -> list[str]:
    out = [f"    - name: {q(item['name'])}"]
    if item.get("short"):
        out.append(f"      short: {q(item['short'])}")
    out.append(f"      emoji: \"{item['emoji']}\"")
    out.append(f"      reason: {q(item['reason'])}")
    return out


def add(slug: str, items: list[dict]) -> int:
    path = TIERS_DIR / f"{slug}.yaml"
    lines = path.read_text(encoding="utf-8").split("\n")
    start = lines.index("tiers:")
    end = next(i for i in range(start + 1, len(lines)) if lines[i] and not lines[i].startswith(" "))
    existing = {l.split("name:", 1)[1].strip().strip("'\"") for l in lines[start:end] if l.strip().startswith("- name:")}
    added = 0
    for r in RANKS:
        new = [it for it in items if it["rank"] == r and it["name"] not in existing]
        if not new:
            continue
        head = next((i for i in range(start + 1, end) if re.match(rf"^  {r}:", lines[i])), None)
        body = sum((fmt(it) for it in new), [])
        if head is None:
            # ランクの見出しが無ければ、次のランクの前（無ければ末尾）に作る
            nxt = next((i for i in range(start + 1, end)
                        if re.match(r"^  ([SABCD]):", lines[i]) and RANKS.index(lines[i][2]) > RANKS.index(r)), end)
            lines[nxt:nxt] = [f"  {r}:"] + body
        else:
            if lines[head].rstrip().endswith("[]"):
                lines[head] = f"  {r}:"
            nxt = next((i for i in range(head + 1, end) if re.match(r"^  [SABCD]:", lines[i])), end)
            lines[nxt:nxt] = body
        end += len(body) + (1 if head is None else 0)
        added += len(new)
    path.write_text("\n".join(lines), encoding="utf-8")
    return added
