#!/usr/bin/env python3
"""
TierJP — Tier表の巨大サイト用 静的サイトジェネレーター

使い方:
    python build.py            # dist/ に書き出し
    python build.py --serve    # ビルドしてローカルプレビュー (http://localhost:8010)
    python build.py --drafts   # draft: true のTier表も含めてビルド（確認用）

データの流れ:
    data/site.yaml        … サイト名・URL・おすすめTier
    data/categories.yaml  … カテゴリー一覧（並び順もここ）
    data/tags.yaml        … タグ → URL用スラッグ
    content/tiers/*.yaml  … Tier表（1ファイル = 1ページ。ファイル名がURLになる）
        ↓ build.py が読み込んで
    dist/                 … 完成したHTML一式（GitHub Pages / Cloudflare Pages にそのまま置ける）

方針:
    - データベースも管理画面も使わない。YAMLを1つ置けば1ページ増える。
    - 「理由のないTier表」はGoogleに薄いページと見なされるので、ビルド時に警告を出す。
    - 関連Tierは手で書いた分 + 同じカテゴリー・同じタグから自動で補う。
"""

from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import shutil
import socketserver
import sys
from dataclasses import dataclass, field
from datetime import date
from functools import partial
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).parent
DATA = ROOT / "data"
TIERS_DIR = ROOT / "content" / "tiers"
DIST = ROOT / "dist"
STATIC = ROOT / "static"
TEMPLATES = ROOT / "templates"

RANKS = ["S", "A", "B", "C", "D"]
# ランク帯の小さな一言。推しジャンルなど、Tier表ごとに labels: で上書きできる
DEFAULT_LABELS = {"S": "最強", "A": "優秀", "B": "ふつう", "C": "微妙", "D": "うーん"}
RELATED_MAX = 6
MIN_ITEMS = 15         # これ未満は「少ない」警告（比べて楽しい表にするため。さくら指定 2026-09-29）
PORT = 8010

warnings: list[str] = []


def warn(msg: str) -> None:
    warnings.append(msg)


def load_yaml(path: Path):
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def to_date(v) -> date | None:
    if v is None or v == "":
        return None
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v))


def short_name(name: str) -> str:
    import re
    n = re.sub(r"（\d{4}）$", "", name)
    n = re.split(r"〜|〈| -", n)[0]
    return n.strip() or name


# ---------------------------------------------------------------- データ構造

@dataclass
class Item:
    name: str
    rank: str
    reason: str = ""
    emoji: str = ""
    image: str = ""
    link: str = ""
    after: str = ""       # やってみたい系：挑戦後のランク（未挑戦なら空）
    done: date | None = None
    after_comment: str = ""

    short_name: str = ""

    @property
    def short(self) -> str:
        """タイル用の短い名前：副題（〜…〜・〈…〉・ -…）と末尾の（年）を省く。YAMLの short: が優先"""
        return self.short_name or short_name(self.name)

    @property
    def moved(self) -> int:
        """挑戦前→後でランクが何段動いたか（上がる=プラス）"""
        if not self.after:
            return 0
        return RANKS.index(self.rank) - RANKS.index(self.after)


@dataclass
class Tier:
    slug: str
    title: str
    description: str
    category: str
    tags: list[str]
    published: date
    updated: date
    type: str                         # normal / challenge
    criteria: str
    summary: str
    rank_notes: dict[str, str]
    labels: dict[str, str]
    rows: dict[str, list[Item]]
    related_slugs: list[str]
    eyecatch: str
    draft: bool
    related: list["Tier"] = field(default_factory=list)
    genre: str = ""                    # カテゴリーの中のジャンル（例：食べ物 > ラーメン）

    @property
    def ranks(self) -> list[str]:
        """表に出すランク：最後の空っぽの行（DやC）は省く"""
        last = max((i for i, r in enumerate(RANKS) if self.rows[r]), default=len(RANKS) - 1)
        return RANKS[:last + 1]

    @property
    def items(self) -> list[Item]:
        return [i for r in RANKS for i in self.rows[r]]

    @property
    def url(self) -> str:
        return f"/tier/{self.slug}/"

    @property
    def top_names(self) -> list[str]:
        return [i.name for i in self.items[:3]]


def parse_tier(path: Path) -> Tier | None:
    slug = path.stem
    where = f"content/tiers/{path.name}"
    try:
        d = load_yaml(path)
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        warn(f"{where}: YAMLの書き方エラー（{mark.line + 1 if mark else '?'}行目）→ スキップ。"
             "文中に「: 」があるなら行全体を ' ' で囲む")
        return None
    for key in ("title", "category", "tiers"):
        if not d.get(key):
            warn(f"{where}: 「{key}」がありません → スキップ")
            return None

    raw_tiers = d["tiers"] or {}
    unknown = [k for k in raw_tiers if str(k) not in RANKS]
    if unknown:
        warn(f"{where}: 使えないランク {unknown}（S/A/B/C/Dのみ）")

    rows: dict[str, list[Item]] = {r: [] for r in RANKS}
    for r in RANKS:
        for x in raw_tiers.get(r) or []:
            if isinstance(x, str):
                x = {"name": x}
            after = str(x.get("after") or "")
            if after and after not in RANKS:
                warn(f"{where}: 「{x.get('name')}」の after が不正: {after}")
                after = ""
            rows[r].append(Item(
                name=str(x["name"]),
                rank=r,
                reason=str(x.get("reason") or "").strip(),
                emoji=str(x.get("emoji") or ""),
                short_name=str(x.get("short") or ""),
                image=x.get("image") or "",
                link=x.get("link") or "",
                after=after,
                done=to_date(x.get("done")),
                after_comment=str(x.get("after_comment") or "").strip(),
            ))

    published = to_date(d.get("published")) or date.today()
    t = Tier(
        slug=slug,
        title=d["title"],
        description=str(d.get("description") or "").strip(),
        category=d["category"],
        tags=[str(x) for x in d.get("tags") or []],
        published=published,
        updated=to_date(d.get("updated")) or published,
        type=d.get("type") or "normal",
        criteria=str(d.get("criteria") or "").strip(),
        summary=str(d.get("summary") or "").strip(),
        rank_notes={str(k): str(v).strip() for k, v in (d.get("rank_notes") or {}).items()},
        labels={**DEFAULT_LABELS, **{str(k): str(v) for k, v in (d.get("labels") or {}).items()}},
        rows=rows,
        related_slugs=d.get("related") or [],
        eyecatch=d.get("eyecatch") or "",
        draft=bool(d.get("draft")),
        genre=str(d.get("genre") or ""),
    )

    # 薄いページ対策のチェック
    n = len(t.items)
    no_reason = [i.name for i in t.items if not i.reason]
    if n < MIN_ITEMS:
        warn(f"{where}: 項目が{n}個だけ（{MIN_ITEMS}個以上推奨）")
    if no_reason:
        warn(f"{where}: 理由がない項目 {len(no_reason)}個: {'、'.join(no_reason[:5])}")
    if not t.summary:
        warn(f"{where}: 総評(summary)がありません")
    if not t.description:
        warn(f"{where}: 説明(description)がありません")
    return t


# ---------------------------------------------------------------- 組み立て

def tag_slug(tag: str, tag_map: dict[str, str]) -> str:
    if tag in tag_map:
        return tag_map[tag]
    if tag.isascii():
        return tag.lower().replace(" ", "-")
    warn(f"data/tags.yaml にタグ「{tag}」のスラッグがありません（仮のURLを使用）")
    tag_map[tag] = "t-" + hashlib.md5(tag.encode()).hexdigest()[:6]
    return tag_map[tag]


def attach_related(tiers: list[Tier]) -> None:
    by_slug = {t.slug: t for t in tiers}
    for t in tiers:
        picked: list[Tier] = []
        for s in t.related_slugs:
            if s in by_slug and s != t.slug:
                picked.append(by_slug[s])
            elif s not in by_slug:
                warn(f"{t.slug}: 関連Tier「{s}」が見つかりません")
        scored = []
        for o in tiers:
            if o is t or o in picked:
                continue
            score = 2 * len(set(t.tags) & set(o.tags)) + (1 if o.category == t.category else 0)
            if score:
                scored.append((score, o.published, o))
        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        picked += [o for _, _, o in scored]
        t.related = picked[:RELATED_MAX]


def build(include_drafts: bool) -> None:
    site = load_yaml(DATA / "site.yaml")
    categories = load_yaml(DATA / "categories.yaml")["categories"]
    tag_map: dict[str, str] = load_yaml(DATA / "tags.yaml").get("tags") or {}
    cat_by_slug = {c["slug"]: c for c in categories}

    tiers: list[Tier] = []
    for p in sorted(TIERS_DIR.glob("*.yaml")):
        if p.name.startswith("_"):
            continue
        t = parse_tier(p)
        if not t:
            continue
        if t.draft and not include_drafts:
            continue
        if t.category not in cat_by_slug:
            warn(f"{p.name}: カテゴリー「{t.category}」が data/categories.yaml にありません → スキップ")
            continue
        tiers.append(t)

    tiers.sort(key=lambda t: (t.published, t.slug), reverse=True)
    attach_related(tiers)

    # カテゴリー・タグの集計
    for c in categories:
        c["tiers"] = [t for t in tiers if t.category == c["slug"]]
        c["url"] = f"/c/{c['slug']}/"
    tags: dict[str, dict] = {}
    for t in tiers:
        for tg in t.tags:
            e = tags.setdefault(tg, {"name": tg, "slug": tag_slug(tg, tag_map), "tiers": []})
            e["tiers"].append(t)
    for e in tags.values():
        e["url"] = f"/tag/{e['slug']}/"
    tag_list = sorted(tags.values(), key=lambda e: (-len(e["tiers"]), e["name"]))

    by_slug = {t.slug: t for t in tiers}

    # シリーズ（data/series.yaml）：特集ページ用に、slug をTierに解決する
    series_list: list[dict] = []
    series_by_tier: dict[str, list[dict]] = {}
    sp = DATA / "series.yaml"
    for sr in (load_yaml(sp).get("series") or []) if sp.exists() else []:
        groups, members = [], []
        for g in sr.get("groups") or []:
            ts = []
            for slug in g.get("tiers") or []:
                if slug in by_slug:
                    ts.append(by_slug[slug])
                else:
                    warn(f"series {sr['slug']}: Tier表「{slug}」が見つかりません")
            groups.append({"name": g["name"], "emoji": g.get("emoji", ""), "tiers": ts})
            members += ts
        entry = {"slug": sr["slug"], "name": sr["name"], "emoji": sr.get("emoji", "📚"),
                 "lead": sr.get("lead", ""), "groups": groups, "tiers": members,
                 "count": len(members), "url": f"/series/{sr['slug']}/"}
        series_list.append(entry)
        for t in members:
            series_by_tier.setdefault(t.slug, []).append(entry)

    featured = [by_slug[s] for s in site.get("featured") or [] if s in by_slug]

    # 出力
    # dist/ の中身だけ消す（プレビュー用サーバーが dist/ を開いていても失敗しないように）
    DIST.mkdir(exist_ok=True)
    for child in DIST.iterdir():
        shutil.rmtree(child) if child.is_dir() else child.unlink()
    shutil.copytree(STATIC, DIST / "static")

    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape())
    env.globals.update(site=site, categories=categories, cat_by_slug=cat_by_slug,
                       tags=tags, RANKS=RANKS, year=date.today().year,
                       series_list=series_list, series_by_tier=series_by_tier)

    def render(tpl: str, out: str, **ctx) -> None:
        path = DIST / out
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(env.get_template(tpl).render(**ctx), encoding="utf-8")

    render("index.html", "index.html", tiers=tiers, featured=featured,
           latest=tiers[:12], tag_list=tag_list[:30], canonical="/")
    for t in tiers:
        og = f"/og/{t.slug}.png" if (STATIC.parent / "og" / f"{t.slug}.png").exists() else ""
        render("tier.html", f"tier/{t.slug}/index.html", t=t,
               cat=cat_by_slug[t.category], og=t.eyecatch or og, canonical=t.url)
    for c in categories:
        # ジャンルがあるカテゴリーは、ジャンルごとにまとめて表示（categories.yaml の genres の順）
        groups = []
        if c.get("genres"):
            known = [g["name"] for g in c["genres"]]
            for g in c["genres"]:
                groups.append({**g, "tiers": [t for t in c["tiers"] if t.genre == g["name"]]})
            rest = [t for t in c["tiers"] if t.genre not in known]
            if rest:
                groups.append({"name": "その他", "emoji": "📦", "tiers": rest})
            for t in c["tiers"]:
                if t.genre and t.genre not in known:
                    warn(f"{t.slug}: ジャンル「{t.genre}」が categories.yaml の {c['slug']} にありません")
        render("list.html", f"c/{c['slug']}/index.html", heading=f"{c['emoji']} {c['name']}のTier表",
               lead=c.get("description", ""), items=c["tiers"], groups=groups, canonical=c["url"])
    for e in tags.values():
        render("list.html", f"tag/{e['slug']}/index.html", heading=f"#{e['name']} のTier表",
               lead="", items=e["tiers"], groups=[], canonical=e["url"])
    for sr in series_list:
        render("list.html", f"series/{sr['slug']}/index.html", heading=f"{sr['emoji']} {sr['name']}",
               lead=sr["lead"], items=sr["tiers"], groups=sr["groups"], canonical=sr["url"])
    render("categories.html", "categories/index.html", tag_list=tag_list, canonical="/categories/")
    render("search.html", "search/index.html", canonical="/search/")
    for page in ("about", "privacy", "contact"):   # サイトポリシー系の固定ページ
        render(f"{page}.html", f"{page}/index.html", canonical=f"/{page}/")
    render("404.html", "404.html", canonical="/404.html")

    # 画像（scripts/make_images.py が作ったもの）
    if (ROOT / "og").exists():
        shutil.copytree(ROOT / "og", DIST / "og")

    # 検索用データ（ページ側のJSで読む）
    search = [{
        "u": t.url, "t": t.title, "d": t.description,
        "c": cat_by_slug[t.category]["name"], "g": t.tags,
        "i": [i.name for i in t.items],
    } for t in tiers]
    # 投票API(workers/vote)が受け付けるTier表の一覧 { slug: 項目数 }
    (ROOT / "workers" / "vote" / "slugs.json").write_text(
        json.dumps({t.slug: len(t.items) for t in tiers}, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    (DIST / "search.json").write_text(json.dumps(search, ensure_ascii=False), encoding="utf-8")

    # sitemap / robots
    base = site["base_url"].rstrip("/")
    urls = ["/", "/categories/", "/about/", "/privacy/", "/contact/"] + [t.url for t in tiers] \
        + [c["url"] for c in categories if c["tiers"]] + [e["url"] for e in tags.values()] \
        + [sr["url"] for sr in series_list]
    lastmod = {t.url: t.updated.isoformat() for t in tiers}
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        lm = f"<lastmod>{lastmod[u]}</lastmod>" if u in lastmod else ""
        sm.append(f"  <url><loc>{base}{u}</loc>{lm}</url>")
    sm.append("</urlset>")
    (DIST / "sitemap.xml").write_text("\n".join(sm), encoding="utf-8")
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n",
                                     encoding="utf-8")

    print(f"✅ ビルド完了: Tier表 {len(tiers)}件 / カテゴリー {sum(1 for c in categories if c['tiers'])}件 "
          f"/ タグ {len(tags)}件 → dist/")
    if warnings:
        print(f"\n⚠ 注意 {len(warnings)}件")
        for w in warnings:
            print("  -", w)


def serve() -> None:
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(DIST))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"\n👀 プレビュー: http://localhost:{PORT}/  （Ctrl+Cで終了）")
        httpd.serve_forever()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--serve", action="store_true")
    ap.add_argument("--drafts", action="store_true")
    a = ap.parse_args()
    build(a.drafts)
    if a.serve:
        serve()
