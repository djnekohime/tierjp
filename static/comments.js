// 一言コメント：承認済みを表示＋投稿フォーム（本文はすべて textContent で出す＝タグは効かない）
(function () {
  const box = document.getElementById("comments");
  if (!box) return;
  const API = (box.dataset.api || "").replace(/\/$/, "");
  const slug = box.dataset.slug;
  const list = box.querySelector(".cm-list");
  const empty = box.querySelector(".cm-empty");
  const form = box.querySelector(".cm-form");
  const msg = box.querySelector(".cm-msg");
  const input = form.querySelector("[name=body]");
  const btn = form.querySelector("button");

  async function load() {
    try {
      const r = await fetch(`${API}/comments?slug=${encodeURIComponent(slug)}`);
      if (!r.ok) return;
      const { comments } = await r.json();
      list.replaceChildren(...comments.map(c => {
        const li = document.createElement("li");
        li.textContent = c.body;
        return li;
      }));
      empty.hidden = comments.length > 0;
    } catch (e) {}
  }

  form.addEventListener("submit", async ev => {
    ev.preventDefault();
    const body = input.value.trim();
    if (!body) { msg.textContent = "一言を書いてね"; return; }
    btn.disabled = true; msg.textContent = "送信中…";
    try {
      const r = await fetch(`${API}/comment`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slug, body, website: form.website.value }),
      });
      if (r.status === 429) msg.textContent = "続けて送ったので、少し時間をおいてね";
      else if (!r.ok) msg.textContent = "うまく送れませんでした。あとでもう一度ためしてね";
      else { input.value = ""; msg.textContent = "💬 ありがとう！管理人が確認したら表示されるよ"; }
    } catch (e) { msg.textContent = "通信できませんでした。あとでもう一度ためしてね"; }
    btn.disabled = false;
  });

  load();
})();
