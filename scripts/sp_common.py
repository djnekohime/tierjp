# -*- coding: utf-8 -*-
"""都道府県別スーパー Tier表の共通部品。元データ＝Wikipedia「日本のスーパーマーケット一覧」＋各社記事の概要（2026-10-09取得）。
項目名に「〜」「/」を使わない（タイル名が途中で切れるため）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import batch_20261007_food_travel as b  # noqa: E402

b.DATE = "2026-10-09"
LAB = {"S": "県の顔", "A": "地域の主役", "B": "頼れる地元チェーン", "C": "こぢんまり個性派", "D": "ニッチ・特化型"}
NOTE = ("※ AIは全店を回ったわけではありません。公開されている企業情報（本社・展開地域・規模など）とAIの印象で並べています。"
        "ランクは値段の安さやお店の良し悪しではなく、「県内での存在感・使い勝手・個性」の目立ち方です。"
        "店舗数や運営会社は変わるので、お出かけ前に公式サイトで確認してください（2026年10月時点）")
CRIT = ("① 県内での存在感（店舗網・知名度・地域への根づき）\n② 使い勝手と個性（品ぞろえ・業態・特色）\n③ 気軽さ（行きやすさ・親しみやすさ）\n" + NOTE)
RN = {"S": "この県ならまず思い浮かぶ", "D": "特定の地域や用途に特化"}


def sp(slug, pref, tags_extra, summary, related, items, area=None):
    """都道府県スーパーのページを1つ追加。area は「北海道」など、題名に使う地名（省略時 pref）。"""
    a = area or pref
    b.page(f"sp-{slug}", f"{a}のスーパー Tier表",
           f"{a}の地元スーパーや生協、全国チェーンを、AIが「県内での存在感×使い勝手と個性×気軽さ」でS〜Dにランク付け。",
           "super", None, ["グルメ", "あるある"] + tags_extra, LAB, CRIT, RN, summary, related, items)
