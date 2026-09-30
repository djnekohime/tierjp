// 「あなたのTier表を作る」：並べ替え → 画像にしてシェア。データはこの端末の中だけ（サーバーへは送らない）
(function () {
  const root = document.getElementById("my-tier");
  const dataEl = document.getElementById("my-tier-data");
  if (!root || !dataEl) return;
  const D = JSON.parse(dataEl.textContent);
  const N = D.items.length;
  const KEY = "mytier:" + D.slug;
  const COLORS = { S: ["#ff4f8b", "#ff9a5a"], A: ["#ff9f43", "#ffd166"], B: ["#ffe45c", "#fff3a8"],
                   C: ["#5ef0b0", "#b4ffd9"], D: ["#62b8ff", "#b8e0ff"] };

  let place = new Array(N).fill(null);   // 各項目のランク（null=まだ決めてない）
  let picked = null;                      // タップで選んでいる項目
  try {
    const s = JSON.parse(localStorage.getItem(KEY) || "null");
    if (Array.isArray(s) && s.length === N) place = s.map(r => (D.ranks.includes(r) ? r : null));
  } catch (e) {}
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(place)); } catch (e) {} };

  const board = root.querySelector(".my-board");
  const pool = root.querySelector(".my-pool");
  const diffEl = root.querySelector(".my-diff");
  const out = root.querySelector(".my-out");

  function tile(i) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "tile my-tile" + (picked === i ? " picked" : "");
    b.draggable = true;
    b.dataset.i = i;
    b.innerHTML = (D.emoji[i] ? '<span class="tile-emoji"></span>' : "") + '<span class="tile-name"></span>';
    if (D.emoji[i]) b.querySelector(".tile-emoji").textContent = D.emoji[i];
    b.querySelector(".tile-name").textContent = D.items[i];
    if (place[i] && place[i] !== D.ai[i]) {
      const m = document.createElement("span");
      m.className = "ai-mark";
      m.textContent = "AI:" + D.ai[i];
      b.appendChild(m);
    }
    return b;
  }

  function render() {
    board.innerHTML = "";
    D.ranks.forEach(r => {
      const row = document.createElement("div");
      row.className = "tier-row my-row" + (picked !== null ? " droppable" : "");
      row.dataset.r = r;
      row.innerHTML = `<div class="tier-label r-${r}">${r}<small></small></div><div class="tier-items"></div>`;
      row.querySelector("small").textContent = D.labels[r] || "";
      const box = row.querySelector(".tier-items");
      place.forEach((p, i) => { if (p === r) box.appendChild(tile(i)); });
      board.appendChild(row);
    });
    pool.innerHTML = "";
    pool.dataset.r = "";
    pool.classList.toggle("droppable", picked !== null);
    place.forEach((p, i) => { if (!p) pool.appendChild(tile(i)); });
    if (!pool.children.length) pool.innerHTML = '<span class="none">ぜんぶ並べたね！</span>';

    const done = place.filter(Boolean).length;
    const diff = place.filter((p, i) => p && p !== D.ai[i]).length;
    diffEl.textContent = done ? `並べた数 ${done}/${N}　AIとちがう所 ${diff}個` : "";
  }

  function moveTo(i, r) {
    place[i] = r || null;
    picked = null;
    save();
    render();
    out.hidden = true;
  }

  // タップ操作：タイル → 段
  root.addEventListener("click", e => {
    const t = e.target.closest(".my-tile");
    if (t) {
      const i = +t.dataset.i;
      const r = t.closest(".my-row, .my-pool").dataset.r || null;
      if (picked !== null && picked !== i && place[picked] !== r) { moveTo(picked, r); return; }
      picked = picked === i ? null : i;
      render();
      return;
    }
    const zone = e.target.closest(".my-row, .my-pool");
    if (zone && picked !== null) { moveTo(picked, zone.dataset.r); return; }

    const act = e.target.closest("[data-act]")?.dataset.act;
    if (act === "ai") { place = D.ai.slice(); picked = null; save(); render(); out.hidden = true; }
    if (act === "reset") { place = new Array(N).fill(null); picked = null; save(); render(); out.hidden = true; }
    if (act === "make") makeImage();
    if (act === "share") share();
  });

  // ドラッグ操作（パソコン）
  root.addEventListener("dragstart", e => {
    const t = e.target.closest(".my-tile");
    if (t) e.dataTransfer.setData("text/plain", t.dataset.i);
  });
  root.addEventListener("dragover", e => { if (e.target.closest(".my-row, .my-pool")) e.preventDefault(); });
  root.addEventListener("drop", e => {
    const zone = e.target.closest(".my-row, .my-pool");
    const i = e.dataTransfer.getData("text/plain");
    if (zone && i !== "") { e.preventDefault(); moveTo(+i, zone.dataset.r); }
  });

  // ---------------------------------------------------------------- 画像づくり
  const FONT = '"M PLUS Rounded 1c","Hiragino Maru Gothic ProN","Yu Gothic UI",sans-serif';
  const EMOJI = '"Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji",sans-serif';
  let blob = null;

  function fitFont(ctx, text, maxW, size, min, weight = 800) {
    for (let s = size; s >= min; s -= 2) {
      ctx.font = `${weight} ${s}px ${FONT}`;
      if (ctx.measureText(text).width <= maxW) return s;
    }
    return min;
  }
  function wrap(ctx, text, maxW) {   // 2行まで折り返し
    const lines = [""];
    for (const ch of text) {
      const cur = lines[lines.length - 1];
      if (ctx.measureText(cur + ch).width > maxW && cur) {
        if (lines.length === 2) { lines[1] = cur.slice(0, -1) + "…"; return lines; }
        lines.push(ch);
      } else lines[lines.length - 1] = cur + ch;
    }
    return lines;
  }
  function rrect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.roundRect ? ctx.roundRect(x, y, w, h, r) : ctx.rect(x, y, w, h);
  }

  async function makeImage() {
    if (!place.some(Boolean)) { diffEl.textContent = "先にタイルを1つ以上並べてね"; return; }
    const btn = root.querySelector(".my-make");
    if (btn.disabled) return;
    btn.disabled = true; btn.textContent = "⏳ 作成中…";
    try { await document.fonts.load(`800 40px "M PLUS Rounded 1c"`, D.title + D.items.join("") + "わたしのTier表AIとちがう所個ティアる。"); } catch (e) {}

    const W = 1080, PAD = 40, LABEL = 130, TW = 142, TH = 142, GAP = 12;
    const perLine = Math.floor((W - PAD * 2 - LABEL - GAP) / (TW + GAP));
    // 最後の空っぽの段（DやC）は省く（サイトの表と同じ）
    const last = Math.max(...D.ranks.map((r, k) => (place.includes(r) ? k : -1)));
    const ranks = D.ranks.slice(0, last + 1);
    const rows = ranks.map(r => place.map((p, i) => (p === r ? i : -1)).filter(i => i >= 0));
    const heights = rows.map(it => Math.max(1, Math.ceil(it.length / perLine)) * (TH + GAP) + GAP);
    const TOP = 330, BOTTOM = 190;
    const H = TOP + heights.reduce((a, b) => a + b + 12, 0) + BOTTOM;

    const c = document.createElement("canvas");
    c.width = W; c.height = H;
    const ctx = c.getContext("2d");

    // 背景：夜空×ピンク
    const bg = ctx.createLinearGradient(0, 0, W, H);
    bg.addColorStop(0, "#140f33"); bg.addColorStop(.55, "#2a1150"); bg.addColorStop(1, "#5a1a66");
    ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);
    let seed = [...D.slug].reduce((a, ch) => a + ch.charCodeAt(0), 7);
    const rnd = () => (seed = (seed * 9301 + 49297) % 233280) / 233280;
    for (let k = 0; k < 140; k++) {
      ctx.globalAlpha = .25 + rnd() * .6; ctx.fillStyle = "#fff";
      ctx.beginPath(); ctx.arc(rnd() * W, rnd() * H, rnd() * 2.2 + .4, 0, Math.PI * 2); ctx.fill();
    }
    ctx.globalAlpha = 1;

    // 見出し
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillStyle = "#ff9ad5"; ctx.font = `800 40px ${FONT}`;
    ctx.fillText("わたしが決めた", W / 2, 80);
    const title = D.title.replace(/\s*Tier表/, "");
    const s = fitFont(ctx, title, W - PAD * 2, 76, 40);
    ctx.shadowColor = "#ff5fb8"; ctx.shadowBlur = 24; ctx.fillStyle = "#fff";
    ctx.fillText(title, W / 2, 165);
    ctx.shadowBlur = 0;
    ctx.fillStyle = "#ffd6ef"; ctx.font = `800 48px ${FONT}`;
    ctx.fillText("Tier表", W / 2, 240);
    const diff = place.filter((p, i) => p && p !== D.ai[i]).length;
    ctx.fillStyle = "#7fe7ff"; ctx.font = `800 32px ${FONT}`;
    ctx.fillText(diff ? `AIとちがう所 ${diff}個` : "AIと完全一致！", W / 2, 298);

    // 表
    let y = TOP;
    ranks.forEach((r, ri) => {
      const h = heights[ri];
      rrect(ctx, PAD, y, W - PAD * 2, h, 22); ctx.fillStyle = "rgba(40,28,78,.82)"; ctx.fill();
      const g = ctx.createLinearGradient(PAD, y, PAD + LABEL, y + h);
      g.addColorStop(0, COLORS[r][0]); g.addColorStop(1, COLORS[r][1]);
      rrect(ctx, PAD, y, LABEL, h, [22, 0, 0, 22]); ctx.fillStyle = g; ctx.fill();
      ctx.fillStyle = "#1a1030"; ctx.font = `800 72px ${FONT}`;
      ctx.fillText(r, PAD + LABEL / 2, y + h / 2 - 12);
      const lab = D.labels[r] || "";
      const ls = fitFont(ctx, lab, LABEL - 14, 22, 15);
      if (ls > 15 || lab.length <= 6) ctx.fillText(lab, PAD + LABEL / 2, y + h / 2 + 38);
      else {   // 長い一言は2行に
        const half = Math.ceil(lab.length / 2);
        fitFont(ctx, lab.slice(0, half), LABEL - 14, 20, 14);
        ctx.fillText(lab.slice(0, half), PAD + LABEL / 2, y + h / 2 + 34);
        ctx.fillText(lab.slice(half), PAD + LABEL / 2, y + h / 2 + 58);
      }

      rows[ri].forEach((i, k) => {
        const x = PAD + LABEL + GAP + (k % perLine) * (TW + GAP);
        const ty = y + GAP + Math.floor(k / perLine) * (TH + GAP);
        rrect(ctx, x, ty, TW, TH, 16); ctx.fillStyle = "rgba(255,255,255,.1)"; ctx.fill();
        ctx.strokeStyle = "rgba(255,255,255,.18)"; ctx.lineWidth = 2; ctx.stroke();
        const hasEmoji = !!D.emoji[i];
        if (hasEmoji) {
          ctx.font = `52px ${EMOJI}`; ctx.fillStyle = "#fff";
          ctx.fillText(D.emoji[i], x + TW / 2, ty + 48);
        }
        ctx.font = `800 22px ${FONT}`;
        let fs = 22;
        let lines = wrap(ctx, D.items[i], TW - 14);
        if (lines.length === 2) { fs = 19; ctx.font = `800 ${fs}px ${FONT}`; lines = wrap(ctx, D.items[i], TW - 14); }
        ctx.fillStyle = "#fff";
        const base = hasEmoji ? ty + 104 : ty + TH / 2;
        lines.forEach((ln, li) => ctx.fillText(ln, x + TW / 2, base + (li - (lines.length - 1) / 2) * (fs + 4)));
        if (D.ai[i] !== r) {   // AIとちがう項目に小さな印
          ctx.font = `800 17px ${FONT}`;
          rrect(ctx, x + TW - 58, ty + 6, 52, 24, 12); ctx.fillStyle = "rgba(127,231,255,.9)"; ctx.fill();
          ctx.fillStyle = "#1a1030"; ctx.fillText("AI:" + D.ai[i], x + TW - 32, ty + 19);
        }
      });
      y += h + 12;
    });

    // フッター
    ctx.fillStyle = "#fff"; ctx.font = `800 44px ${FONT}`;
    ctx.fillText("ティアる。  tierjp.com", W / 2, H - 120);
    ctx.fillStyle = "#b9acd9"; ctx.font = `800 28px ${FONT}`;
    ctx.fillText("AIの答えと理由はサイトで →", W / 2, H - 66);

    c.toBlob(b => {
      blob = b;
      const url = URL.createObjectURL(b);
      out.querySelector("img").src = url;
      out.querySelector(".dl").href = url;
      out.querySelector(".x").href = "https://x.com/intent/post?text=" +
        encodeURIComponent(`わたしの「${D.title}」できた！AIとちがう所は${diff}個🐈‍⬛\n#ティアる #Tier表\n`) +
        "&url=" + encodeURIComponent(D.url);
      btn.disabled = false; btn.textContent = "🖼 画像を作り直す";
      out.hidden = false;
      out.scrollIntoView({ behavior: "smooth", block: "center" });
    }, "image/png");
  }

  async function share() {
    if (!blob) return;
    const file = new File([blob], `tierjp-${D.slug}.png`, { type: "image/png" });
    if (navigator.canShare && navigator.canShare({ files: [file] })) {
      try {
        await navigator.share({ files: [file], text: `わたしの「${D.title}」 #ティアる ${D.url}` });
        return;
      } catch (e) { if (e.name === "AbortError") return; }
    }
    out.querySelector(".dl").click();
  }

  render();
})();
