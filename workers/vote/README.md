# ティアる。投票API（Cloudflare Worker + D1）

Tier表ごとに「S〜Dの並び」を集計する。名前・コメント・画像は受け取らない。

## 初回デプロイ（さくらのCloudflareアカウントで）
1. `npx wrangler login`（ブラウザで許可を押す）
2. `npx wrangler d1 create tierjp-vote` → 出た database_id を wrangler.toml に貼る
3. `npx wrangler d1 execute tierjp-vote --remote --file=schema.sql`
4. `python ../../build.py` で slugs.json を更新 → `npx wrangler deploy`
5. 出た URL（https://tierjp-vote.<アカウント>.workers.dev）を `data/site.yaml` の `vote_api:` に入れてビルド＆push

## Tier表を増やしたとき
slugs.json に無いTier表への投票は拒否される。`python build.py` → `npx wrangler deploy` を再実行（ログイン済みなら1分）。

## ローカルテスト
`npx wrangler d1 execute tierjp-vote --local --file=schema.sql` → `npx wrangler dev --local --port 8787`
サイト側は `vote_api: "http://127.0.0.1:8787"` にして `python build.py --serve`（:8010のみ許可）。
