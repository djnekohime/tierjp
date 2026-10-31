あなたは「ティアる。」(tierjp.com)の担当。今日ぶんのTier表を **10本** 作って公開する。確認質問はしない。自分で最善を判断して最後まで進める。
作業場所: C:\Users\himic\tier-site

## 手順
1. メモを読む: C:\Users\himic\HIMEKA避難所\ティアる\2026-09-29 Tier表巨大サイト Tier World.md と C:\Users\himic\.claude\projects\C--Users-himic\memory\tier-world-site.md (品質ルール・禁止事項が書いてある)
2. 直近の例を見る: scripts/batch_20261031_kurashi.py (書式の手本。b.page(...)を使う)
3. 重複チェック: content/tiers/*.yaml のタイトルと、data/categories.yaml・data/series.yaml・scripts/season.py を見て、**まだ無いお題を10本**選ぶ。カテゴリーが偏らないように。季節・今日の日付に合うものを優先。
4. scripts/batch_<今日の日付>_daily.py を作って実行(YAML生成)。各表は **15項目以上・全項目に理由と emoji・総評600字以上**。
5. 実在の人・作品・商品・法律・健康に関わる表は、書く前に Web検索で最新を確認(知識は2025年まで)。健康・安全系は「専門家の助言ではなく目安」を明記。BTS等は D を使わず labels。歌詞は載せない。国旗絵文字・ZWJ絵文字は使わない。
6. python scripts/make_images.py → python build.py でビルド。エラーなら直す。
7. 10本とも公開品質か自己点検(薄いもの・重複・誤情報は直すか差し替える)。
8. git add -A → commit(「Tier表10本を追加(日次)：お題を列挙」) → push。Worker再デプロイが必要な場合は workers/vote の手順に従う(メモ参照)。
9. C:\Users\himic\HIMEKA避難所\ティアる\日次更新ログ.md の先頭に「日付・作った10本のslug・気づき」を追記。

## 禁止
- 公開物に「さくら」と書かない(管理人)。年金・障害の語を出さない。
- 既存ファイルを消さない。他のサイト・設定をいじらない。
- 失敗したら原因をログに書いて終了(無理に壊れた状態でpushしない)。
