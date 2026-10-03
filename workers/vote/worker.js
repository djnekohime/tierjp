// ティアる。投票＋一言コメントAPI（Cloudflare Worker + D1）。ログインなし。投票は記号だけ、コメントは承認制（名前なし）
import ADMIN_HTML from "./admin.html";   // 管理ページ（Workerと一緒に配る）
import SLUGS from "./slugs.json";   // build.py が作る { slug: 項目数 }。ここに無いTier表への投票は受けない

const RANKS = ["S", "A", "B", "C", "D"];
const ORIGINS = ["https://tierjp.com", "https://www.tierjp.com", "http://localhost:8010", "http://127.0.0.1:8010"];
const LIMIT_PER_HOUR = 60;   // 同じ回線から1時間に受ける投票数（家族・学校の共有回線を考えてゆるめ）
const COMMENT_MAX = 40;        // 一言は40字まで
const COMMENT_PER_HOUR = 5;    // 同じ回線から1時間に受けるコメント数
const SHOW_MAX = 30;           // 1ページに出す承認済みコメントの上限（新しい順）
// 自動で非公開にする：URL・メール・電話番号らしきもの、強い悪口（足せば増やせる）
const AUTO_REJECT = [/https?:|www\.|\.(com|jp|net|org|co)\b|ｈｔｔｐ/i, /[\w.+-]+@[\w-]+\./, /\d{2,4}[-ー−\s]?\d{2,4}[-ー−\s]?\d{3,4}/];
const NG_WORDS = ["死ね", "しね", "殺す", "ころす", "きもい", "キモい", "うざい", "ウザい", "消えろ", "ばか", "バカ", "馬鹿", "あほ", "アホ", "くそ", "クソ", "ガイジ", "障害者", "チョン", "支那"];

async function safeEqual(a, b) {   // 合言葉の比較（ハッシュして比べる）
  const [x, y] = await Promise.all([sha(a), sha(b)]);
  return x === y;
}

const json = (obj, status, cors) =>
  new Response(JSON.stringify(obj), { status, headers: { "Content-Type": "application/json; charset=utf-8", ...cors } });

async function sha(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("").slice(0, 32);
}

async function results(db, slug) {
  const n = SLUGS[slug];
  const counts = Array.from({ length: n }, () => ({ S: 0, A: 0, B: 0, C: 0, D: 0 }));
  const { results: rows } = await db
    .prepare("SELECT CAST(j.key AS INTEGER) AS idx, j.value AS r, COUNT(*) AS c FROM votes v, json_each(v.ranks) j WHERE v.slug = ?1 AND j.value IS NOT NULL GROUP BY idx, r")
    .bind(slug).all();
  for (const row of rows) if (counts[row.idx] && RANKS.includes(row.r)) counts[row.idx][row.r] = row.c;
  const v = await db.prepare("SELECT COUNT(*) AS c FROM votes WHERE slug = ?1").bind(slug).first();
  return { voters: v.c, counts };
}

export default {
  async fetch(req, env) {
    const origin = req.headers.get("Origin");
    const cors = {
      "Access-Control-Allow-Origin": ORIGINS.includes(origin) ? origin : ORIGINS[0],
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, X-Admin-Key",
      "Vary": "Origin",
    };
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    const url = new URL(req.url);

    if (req.method === "GET" && url.pathname === "/results") {
      const slug = url.searchParams.get("slug") || "";
      if (!(slug in SLUGS)) return json({ error: "unknown slug" }, 404, cors);
      return json(await results(env.DB, slug), 200, { ...cors, "Cache-Control": "public, max-age=60" });
    }

    if (req.method === "POST" && url.pathname === "/vote") {
      if (origin && !ORIGINS.includes(origin)) return json({ error: "forbidden" }, 403, cors);
      const text = await req.text();
      if (text.length > 4000) return json({ error: "too large" }, 413, cors);
      let b;
      try { b = JSON.parse(text); } catch { return json({ error: "bad json" }, 400, cors); }
      const { slug, voter, ranks } = b || {};
      if (typeof slug !== "string" || !(slug in SLUGS)) return json({ error: "unknown slug" }, 404, cors);
      if (typeof voter !== "string" || !/^[A-Za-z0-9-]{16,64}$/.test(voter)) return json({ error: "bad voter" }, 400, cors);
      if (!Array.isArray(ranks) || ranks.length !== SLUGS[slug] || !ranks.every(r => r === null || RANKS.includes(r)) || !ranks.some(Boolean))
        return json({ error: "bad ranks" }, 400, cors);

      // 連打よけ（IPは1時間で消えるハッシュとしてだけ持つ）
      const now = Math.floor(Date.now() / 1000), hour = Math.floor(now / 3600);
      const ip = req.headers.get("CF-Connecting-IP") || "?";
      const key = (await sha(ip + (env.IP_SALT || "tierjp"))) + ":" + hour;
      const r = await env.DB.prepare("INSERT INTO rate (k, n, win) VALUES (?1, 1, ?2) ON CONFLICT(k) DO UPDATE SET n = n + 1 RETURNING n").bind(key, hour).first();
      if (r.n > LIMIT_PER_HOUR) return json({ error: "too many" }, 429, cors);
      if (Math.random() < 0.02) await env.DB.prepare("DELETE FROM rate WHERE win < ?1").bind(hour - 2).run();

      await env.DB.prepare(
        "INSERT INTO votes (slug, voter, ranks, created, updated) VALUES (?1, ?2, ?3, ?4, ?4) ON CONFLICT(slug, voter) DO UPDATE SET ranks = excluded.ranks, updated = excluded.updated"
      ).bind(slug, voter, JSON.stringify(ranks), now).run();
      return json(await results(env.DB, slug), 200, cors);
    }

    // ---------------------------------------------------------------- 一言コメント（承認制）
    if (req.method === "GET" && url.pathname === "/comments") {
      const slug = url.searchParams.get("slug") || "";
      if (!(slug in SLUGS)) return json({ error: "unknown slug" }, 404, cors);
      const { results: rows } = await env.DB
        .prepare("SELECT body, created FROM comments WHERE slug = ?1 AND status = 'ok' ORDER BY created DESC LIMIT ?2")
        .bind(slug, SHOW_MAX).all();
      return json({ comments: rows }, 200, { ...cors, "Cache-Control": "public, max-age=60" });
    }

    if (req.method === "POST" && url.pathname === "/comment") {
      if (origin && !ORIGINS.includes(origin)) return json({ error: "forbidden" }, 403, cors);
      const text = await req.text();
      if (text.length > 2000) return json({ error: "too large" }, 413, cors);
      let b;
      try { b = JSON.parse(text); } catch { return json({ error: "bad json" }, 400, cors); }
      const { slug, body, website } = b || {};
      if (typeof slug !== "string" || !(slug in SLUGS)) return json({ error: "unknown slug" }, 404, cors);
      if (website) return json({ ok: true }, 200, cors);   // ボットだけが埋める罠欄。成功したふりをして捨てる
      const msg = typeof body === "string" ? body.replace(/\s+/g, " ").trim() : "";
      if (!msg) return json({ error: "empty" }, 400, cors);
      if ([...msg].length > COMMENT_MAX) return json({ error: "too long" }, 400, cors);

      const now = Math.floor(Date.now() / 1000), hour = Math.floor(now / 3600);
      const ip = req.headers.get("CF-Connecting-IP") || "?";
      const key = "c:" + (await sha(ip + (env.IP_SALT || "tierjp"))) + ":" + hour;
      const r = await env.DB.prepare("INSERT INTO rate (k, n, win) VALUES (?1, 1, ?2) ON CONFLICT(k) DO UPDATE SET n = n + 1 RETURNING n").bind(key, hour).first();
      if (r.n > COMMENT_PER_HOUR) return json({ error: "too many" }, 429, cors);

      const dup = await env.DB.prepare("SELECT 1 FROM comments WHERE slug = ?1 AND body = ?2 LIMIT 1").bind(slug, msg).first();
      if (dup) return json({ ok: true }, 200, cors);   // 同じ文の連投は黙って1件にまとめる

      let status = "pending", flag = null;
      if (AUTO_REJECT.some(re => re.test(msg))) { status = "no"; flag = "URL・連絡先らしきもの"; }
      else if (NG_WORDS.some(w => msg.includes(w))) { status = "no"; flag = "NGワード"; }
      await env.DB.prepare("INSERT INTO comments (slug, body, status, flag, created) VALUES (?1, ?2, ?3, ?4, ?5)").bind(slug, msg, status, flag, now).run();
      return json({ ok: true }, 200, cors);   // 自動で非公開にした場合も、本人には「承認待ち」と同じ返事
    }

    // ---------------------------------------------------------------- 管理ページ（さくら専用。合言葉＝ADMIN_TOKEN）
    if (url.pathname === "/admin") {
      return new Response(ADMIN_HTML, { headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store", "X-Robots-Tag": "noindex" } });
    }
    if (url.pathname.startsWith("/admin/")) {
      const given = (req.headers.get("X-Admin-Key") || "").trim();
      const secret = (env.ADMIN_TOKEN || "").trim();   // 登録時に改行が付いても通るように
      if (!secret || !(await safeEqual(given, secret))) return json({ error: "unauthorized" }, 401, cors);
      if (req.method === "GET" && url.pathname === "/admin/list") {
        const q = url.searchParams.get("status");
        const st = ["pending", "ok", "no"].includes(q) ? q : "pending";
        const { results: rows } = await env.DB
          .prepare("SELECT id, slug, body, status, flag, created FROM comments WHERE status = ?1 ORDER BY created DESC LIMIT 200").bind(st).all();
        const cnt = await env.DB.prepare("SELECT status, COUNT(*) AS c FROM comments GROUP BY status").all();
        return json({ rows, counts: Object.fromEntries(cnt.results.map(x => [x.status, x.c])) }, 200, cors);
      }
      if (req.method === "POST" && url.pathname === "/admin/set") {
        let b;
        try { b = await req.json(); } catch { return json({ error: "bad json" }, 400, cors); }
        const { ids, status } = b || {};
        if (!Array.isArray(ids) || !ids.every(Number.isInteger) || !["ok", "no", "pending", "delete"].includes(status)) return json({ error: "bad" }, 400, cors);
        for (const id of ids.slice(0, 200)) {
          if (status === "delete") await env.DB.prepare("DELETE FROM comments WHERE id = ?1").bind(id).run();
          else await env.DB.prepare("UPDATE comments SET status = ?1 WHERE id = ?2").bind(status, id).run();
        }
        return json({ ok: true }, 200, cors);
      }
    }

    return json({ error: "not found" }, 404, cors);
  },
};
