// Tier表の検索（search.json を読み込んで、ブラウザ内で絞り込む）
(async () => {
  const box = document.getElementById("q"), out = document.getElementById("results"), info = document.getElementById("info");
  const data = await (await fetch("/search.json")).json();
  const esc = s => s.replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  const run = () => {
    const words = box.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
    if (!words.length) { out.innerHTML = ""; info.textContent = `${data.length}個のTier表から探せます`; return; }
    const hits = data.map(d => {
      const hay = [d.t, d.d, d.c, ...d.g, ...d.i].join(" ").toLowerCase();
      if (!words.every(w => hay.includes(w))) return null;
      const score = words.reduce((s, w) => s + (d.t.toLowerCase().includes(w) ? 3 : 0) + (d.g.join(" ").toLowerCase().includes(w) ? 2 : 0), 0);
      return { d, score };
    }).filter(Boolean).sort((a, b) => b.score - a.score);
    info.textContent = `${hits.length}件ヒット`;
    out.innerHTML = hits.slice(0, 100).map(({ d }) =>
      `<a href="${d.u}"><b>${esc(d.t)}</b><br><small>${esc(d.c)} ・ ${d.g.map(g => "#" + esc(g)).join(" ")}</small></a>`).join("");
  };
  box.value = new URLSearchParams(location.search).get("q") || "";
  box.addEventListener("input", run);
  run();
})();
