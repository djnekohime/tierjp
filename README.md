# Tier World（仮）— AIが本気でS〜Dを決める、Tier表の図鑑

ランク・理由・総評はすべてAI（くろ）が担当。データベースも管理画面もなし。
**YAMLを1つ置く → ビルド → 1ページ増える** だけの仕組み。

## いつもの流れ
```
python scripts/make_images.py   # 新しいTier表の画像を作る（og/ と sns/）
python build.py --serve         # ビルドして http://localhost:8010/ で確認
```

## フォルダ
| 場所 | 中身 |
|---|---|
| content/tiers/*.yaml | Tier表1つ＝1ファイル。ファイル名がURL（/tier/ファイル名/）。ひな形は `_template.yaml` |
| data/categories.yaml | カテゴリー（Tier表は必ず1つに所属） |
| data/tags.yaml | 日本語タグ → URL用英字。無いとビルド時に警告 |
| data/site.yaml | サイト名・公開URL・おすすめTier |
| og/ | シェア用画像 1200x630（公開される） |
| sns/ | リール・TikTok・ショート用 1080x1920（gitに入れない） |
| dist/ | 完成したサイト（自動生成。直接触らない） |

## 品質ルール（Googleに薄いページと見なされないため）
- 全項目に `reason`（理由）を書く／項目は5個以上／`summary`（総評）必須
- 守れていないとビルド時に ⚠ 警告が出る
- 実在人物（選手・芸能人）のTierは写真を使わない（肖像権）

## 関連Tier
`related:` に書いた分＋同じカテゴリー・共通タグから自動で最大6件。
