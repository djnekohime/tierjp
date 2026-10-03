// ティアる。投票API（Cloudflare Worker + D1）。ログインなし・コメントなし・数字だけ保存
import SLUGS from "./slugs.json";   // build.py が作る { slug: 項目数 }。ここに無いTier表への投票は受けない

const RANKS = ["S", "A", "B", "C", "D"];
const ORIGINS = ["https://tierjp.com", "https://www.tierjp.com", "http://localhost:8010", "http://127.0.0.1:8010"];
const LIMIT_PER_HOUR = 60;   // 同じ回線から1時間に受ける投票数（家族・学校の共有回線を考えてゆるめ）

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
      "Access-Control-Allow-Headers": "Content-Type",
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

    return json({ error: "not found" }, 404, cors);
  },
};
