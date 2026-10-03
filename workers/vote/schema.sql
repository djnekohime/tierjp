-- 投票データ：1人（端末）×1Tier表で1行。再投票は上書き
CREATE TABLE IF NOT EXISTS votes (
  slug    TEXT NOT NULL,
  voter   TEXT NOT NULL,
  ranks   TEXT NOT NULL,      -- JSON配列。項目の順番どおりに "S"〜"D" か null
  created INTEGER NOT NULL,
  updated INTEGER NOT NULL,
  PRIMARY KEY (slug, voter)
);
-- 連打よけ：IPのハッシュ×1時間ごとの回数（個人は特定しない）
CREATE TABLE IF NOT EXISTS rate (
  k   TEXT PRIMARY KEY,
  n   INTEGER NOT NULL,
  win INTEGER NOT NULL
);
-- 一言コメント：承認制。status = pending（承認待ち）/ ok（公開）/ no（非公開）
CREATE TABLE IF NOT EXISTS comments (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  slug    TEXT NOT NULL,
  body    TEXT NOT NULL,
  status  TEXT NOT NULL DEFAULT 'pending',
  flag    TEXT,                -- 自動チェックで引っかかった理由（管理画面に表示）
  created INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS comments_slug_status ON comments (slug, status, created);
