// ティアる。おすすめ商品カード：見に来た人のブラウザが楽天市場APIから直接商品を取って表示する。
// 商品情報は保存しない（楽天ウェブサービス規約）。効能は書かない・価格は載せない。ルールは data/affiliate.yaml。
(function () {
  var box = document.getElementById("aff-box");
  if (!box) return;
  var d = box.dataset;
  var queries = JSON.parse(d.queries), ng = JSON.parse(d.ng);
  var max = +d.max, minAvg = +d.minAvg, minCount = +d.minCount;
  var list = box.querySelector(".aff-list");
  var CACHE_KEY = "aff:" + location.pathname, TTL = 6 * 3600 * 1000;
  var EP = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701";

  function render(picks) {
    if (!picks.length) return;
    picks.forEach(function (p) {
      var li = document.createElement("li");
      var a1 = document.createElement("a");
      a1.href = p.url; a1.rel = "sponsored noopener"; a1.target = "_blank";
      var img = document.createElement("img");
      img.src = p.image; img.alt = ""; img.width = 96; img.height = 96; img.loading = "lazy";
      a1.appendChild(img);
      var div = document.createElement("div");
      var a2 = document.createElement("a");
      a2.className = "aff-name"; a2.href = p.url; a2.rel = "sponsored noopener"; a2.target = "_blank"; a2.textContent = p.name;
      var meta = document.createElement("p");
      meta.className = "aff-meta"; meta.textContent = p.shop + "｜レビュー ★" + p.avg + "（" + p.count + "件）";
      var a3 = document.createElement("a");
      a3.className = "link-btn"; a3.href = p.url; a3.rel = "sponsored noopener"; a3.target = "_blank"; a3.textContent = "楽天市場で見る →";
      div.appendChild(a2); div.appendChild(meta); div.appendChild(a3);
      li.appendChild(a1); li.appendChild(div); list.appendChild(li);
    });
    box.hidden = false;
  }

  try {
    var c = JSON.parse(localStorage.getItem(CACHE_KEY) || "null");
    if (c && Date.now() - c.t < TTL) { render(c.p); return; }
  } catch (e) {}

  function firstImage(it) {
    var m = it.mediumImageUrls || [];
    if (!m.length) return "";
    return typeof m[0] === "string" ? m[0] : (m[0].imageUrl || "");
  }
  function clean(n) {
    return n.replace(/【[^】]*】|［[^］]*］|\[[^\]]*\]|＼[^／]*／|★[^★\s]*★?/g, " ").replace(/\s+/g, " ").trim().slice(0, 48);
  }
  function pick(items, shops, core) {
    var best = null;
    items.forEach(function (it) {
      it = it.Item || it;
      var name = it.itemName || "";
      if (ng.some(function (w) { return name.indexOf(w) >= 0; })) return;
      if (name.indexOf(core) < 0) return;  // 検索語の先頭（いちばん大事な言葉）が商品名に入っているものだけ
      var avg = +it.reviewAverage || 0, cnt = +it.reviewCount || 0;
      if (avg < minAvg || cnt < minCount) return;
      if (!it.affiliateUrl || !firstImage(it) || shops[it.shopName]) return;
      if (!best || cnt > best.count) best = { name: clean(name), url: it.affiliateUrl, image: firstImage(it), shop: it.shopName || "", avg: avg, count: cnt };
    });
    return best;
  }

  var picks = [], shops = {};
  (function next(i) {
    if (i >= queries.length || picks.length >= max) {
      try { localStorage.setItem(CACHE_KEY, JSON.stringify({ t: Date.now(), p: picks })); } catch (e) {}
      render(picks); return;
    }
    var u = EP + "?applicationId=" + encodeURIComponent(d.appId) + "&accessKey=" + encodeURIComponent(d.accessKey) +
      "&affiliateId=" + encodeURIComponent(d.affiliateId) + "&keyword=" + encodeURIComponent(queries[i]) +
      "&hits=30&imageFlag=1&availability=1&format=json";
    fetch(u).then(function (r) { return r.ok ? r.json() : { Items: [] }; }).catch(function () { return { Items: [] }; })
      .then(function (j) {
        var b = pick(j.Items || [], shops, queries[i].split(" ")[0]);
        if (b) { picks.push(b); shops[b.shop] = 1; }
        setTimeout(function () { next(i + 1); }, 1100);
      });
  })(0);
})();
