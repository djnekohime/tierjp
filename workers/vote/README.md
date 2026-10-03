# ティアる。投票API（Cloudflare Worker + D1）

Tier表ごとに「S〜Dの並び」を集計する＋「一言コメント」（40字・名前なし・承認制）。画像は受け取らない。

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

## 一言コメントの運用
- 管理ページ: `https://tierjp-vote.tierjp.workers.dev/admin`（合言葉＝Workerのシークレット `ADMIN_TOKEN`。端末のブラウザに保存される。控えは `C:\Users\himic\HIMEKA避難所\ティアる\コメント管理の合言葉.txt`）
- 送られた一言は「承認待ち」。✅公開を押したものだけ、Tier表ページに出る。URL・連絡先・NGワードは自動で「非公開」に入る（管理ページの「非公開」タブで確認できる）。
- NGワード等の調整は `worker.js` 上部の `NG_WORDS` / `AUTO_REJECT`。
- 初回だけ: `npx wrangler d1 execute tierjp-vote --remote --file=schema.sql`（comments表を作る）→ `npx wrangler secret put ADMIN_TOKEN` → `npx wrangler deploy`
- メール通知: 毎晩21時（日本時間）に、承認待ちがある日だけ `NOTIFY_TO` へメール（Resend。送信元は onboarding@resend.dev＝Resendアカウントのメール宛にだけ送れる）。必要なシークレット `RESEND_API_KEY`。控えは `HIMEKA避難所\ティアる\` に置く。
