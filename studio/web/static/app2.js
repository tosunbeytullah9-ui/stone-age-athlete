/* Video Fabrikası — panel part 2: claims, packaging, publish record & retention, calendar, source library. */
"use strict";

const fmtN = (n) => (n == null || n === "" ? "–" : n >= 1e6 ? (n / 1e6).toFixed(1).replace(".0", "") + " M" : n >= 1e3 ? Math.round(n / 1e3) + " B" : String(n));
const BAND_CLS = (v, good = "high") => (v == null ? "" : (good === "high" ? v >= 4 : v <= 2) ? "ok" : (good === "high" ? v <= 2 : v >= 4) ? "bad" : "warn");

function signalCell(s) {
  if (!s) return '<span class="muted">ölçülmedi</span>';
  return `<div class="sig">${pill("talep " + s.demand, BAND_CLS(s.demand))} ${pill("rekabet " + s.competition, BAND_CLS(s.competition, "low"))} ${pill("boşluk " + s.gap, BAND_CLS(s.gap))}</div>
    <div class="muted" title="${esc(s.query)} · ${s.results} sonuç · ${s.checked}">medyan ${fmtN(s.median_views)} · en iyi ${fmtN(s.top_views)} · son 12 ay ${s.recent_12m}</div>`;
}

/* ------------------------------------------------------------ claims (script tab) */
function renderClaims(cid, slug, el) {
  const claims = P.claims || [];
  const verified = claims.filter((c) => c.verified).length;
  el.innerHTML = `<div class="spread"><h3 style="margin:0">İddialar <span class="muted small">${claims.length} iddia · ${verified} doğrulandı · kütüphanede ${P.library_size} kaynak</span></h3>
      <div class="row"><button class="sm" id="cl-copy">İddia istemini kopyala</button><button class="sm" id="cl-apply">Cevabı uygula</button></div></div>
    <p class="small muted" style="margin:6px 0 8px">Önce "Kaydet & böl" (shot numaraları için). İstemi Claude'a yapıştır → gelen YAML'ı buraya uygula: yeni kaynaklar <a href="#/library">ortak kütüphaneye</a>, iddialar cümlelere bağlanır. Her iddiayı kaynağıyla karşılaştırıp <b>doğrulandı</b> işaretle.</p>
    <div id="cl-box" class="hidden"><textarea id="cl-text" class="code" rows="8" placeholder="Claude'un iddia YAML cevabı"></textarea><div class="row" style="margin-top:6px"><button class="sm primary" id="cl-go">Uygula</button></div></div>
    ${claims.length ? `<div class="claims">${claims.map((c) => `<div class="claim ${c.overclaim ? "over" : ""}">
      <label class="check" style="padding:0"><input type="checkbox" data-cv="${esc(c.id)}" ${c.verified ? "checked" : ""}> <b>${esc(c.id)}</b></label>
      <div><div>${esc(c.text)}</div>
        <div class="small muted">${c.src ? `${esc(c.src.authors || "")} ${esc(c.src.year || "")} · ${esc(c.src.type || "")} · <a href="${esc(c.src.url || "")}" target="_blank">kaynak</a>` : `<span class="err">kaynak kütüphanede yok: ${esc(c.source || "—")}</span>`}
        ${(c.shots || []).length ? " · " + c.shots.map(esc).join(", ") : ""}${c.confidence ? " · güven: " + esc(c.confidence) : ""}</div>
        ${c.quote ? `<div class="small quote">“${esc(c.quote)}”</div>` : ""}
        ${c.caveat ? `<div class="small">Çekince: ${esc(c.caveat)}</div>` : ""}
        ${c.overclaim ? `<div class="small err">Senaryo kaynaktan fazlasını söylüyor. Öneri: ${esc(c.suggest || "")}</div>` : ""}</div></div>`).join("")}</div>` : '<p class="muted small">Henüz iddia kaydı yok.</p>'}`;
  $("#cl-copy").onclick = async () => copyText(await api(`/api/projects/${cid}/${slug}/prompt/claims`));
  $("#cl-apply").onclick = () => $("#cl-box").classList.toggle("hidden");
  $("#cl-go").onclick = async () => {
    try { const r = await api(`/api/projects/${cid}/${slug}/apply/claims`, { method: "POST", body: { text: $("#cl-text").value } }); toast(`${r.claims} iddia, ${r.sources_added} yeni kaynak`); viewProject(cid, slug, "script"); }
    catch (e) { toast(e.message, true); }
  };
  $$("[data-cv]").forEach((cb) => (cb.onchange = async () => { await api(`/api/projects/${cid}/${slug}/claims`, { method: "PUT", body: { id: cb.dataset.cv, verified: cb.checked } }); toast(cb.checked ? "Doğrulandı" : "İşaret kaldırıldı"); }));
}

/* ------------------------------------------------------------ packaging (thumbnails + titles) */
function projPackage(cid, slug, el) {
  const pub = P.publish;
  const langs = P.languages;
  el.innerHTML = `<div class="grid" style="grid-template-columns:minmax(0,3fr) minmax(280px,2fr)">
    <div>
      <div class="card"><div class="spread"><h3 style="margin:0">Kapak görselleri (A/B/C)</h3>
        <div class="row"><button class="sm" id="pk-copy">Paket istemini kopyala</button><button class="sm" id="pk-apply">Cevabı uygula</button><button class="sm primary" id="pk-render">Kapakları üret</button></div></div>
        <p class="small muted">Üç farklı fikir üret, YouTube Studio'da "Test & Compare" ile dene (kazananı izlenme süresi belirler). Kapakta yazı olabilir (en fazla 4 kelime); karakterler telefonda okunacak kadar büyük olmalı: <span class="kbd">frame</span> ile yakın çekim.</p>
        <div id="pk-box" class="hidden" style="margin-bottom:10px"><textarea id="pk-text" class="code" rows="8" placeholder="Claude'un paket YAML cevabı (titles, thumbnails, hooks...)"></textarea><div class="row" style="margin-top:6px"><button class="sm primary" id="pk-go">Uygula</button></div></div>
        ${langs.map((lg) => `<div style="margin-top:8px"><div class="small muted">${LANG_TR[lg] || lg}</div>
          <div class="thumbs">${(P.thumbs[lg] || []).map((u, i) => `<figure><img src="${u}"><figcaption>${String.fromCharCode(65 + i)}</figcaption></figure>`).join("") || '<span class="muted small">henüz kapak yok</span>'}</div>
          ${P.outputs[lg].thumb_preview ? `<div class="small" style="margin-top:6px"><a href="${P.outputs[lg].thumb_preview}" target="_blank">Telefon boyutunda karşılaştır →</a></div>` : ""}</div>`).join("")}
        <div id="live-box" class="hidden" style="margin-top:10px"><div id="live-status" class="small muted"></div><div class="log" id="live-log" style="height:120px"></div></div>
      </div>
      <div class="card" style="margin-top:14px"><div class="spread"><h3 style="margin:0">Kapak tarifleri (YAML)</h3><button class="sm" id="th-save">Kaydet</button></div>
        <textarea id="th-yaml" class="code" rows="16" spellcheck="false" placeholder="- visual: {bg: underwater, figures: [...]}\n  frame: {x: 900, y: 560, zoom: 1.8}\n  text: {en: BIGGER SPLEENS, tr: DEV DALAK}\n  text_pos: left">${esc(P.thumbnails_yaml)}</textarea></div>
    </div>
    <div>
      <div class="card"><h3>Başlık adayları</h3>
        <p class="small muted" style="margin-top:0">Birini seç: videonun başlığı ve açıklaması onu kullanır. En fazla 60 karakter, iddialardan büyük söz vermeden.</p>
        <div id="titles">${(pub.title_variants || []).map((t, i) => `<label class="check title-opt"><input type="radio" name="title" value="${i}" ${t === P.meta.title ? "checked" : ""}> <span>${esc(t)} <span class="muted small">${t.length}</span></span></label>`).join("") || '<p class="muted small">Paket istemiyle 10 başlık üret.</p>'}</div>
        <div class="row" style="margin-top:8px"><input id="t-new" placeholder="Kendi başlığın" style="flex:1"><button class="sm" id="t-add">Ekle</button></div></div>
      ${(pub.hook_options || []).length ? `<div class="card" style="margin-top:14px"><h3>Açılış (ilk 8 sn) önerileri</h3>${pub.hook_options.map((h) => `<div class="hook"><span class="pill">${esc((P.hook_types || {})[h.type] || h.type || "")}</span> ${esc(h.text || "")}</div>`).join("")}
        <p class="small muted">Beğendiğini senaryonun ilk paragrafına al ve Yayın sekmesinde açılış tipini işaretle.</p></div>` : ""}
      ${(pub.shorts_ideas || []).length ? `<div class="card" style="margin-top:14px"><h3>Shorts fikirleri</h3>${pub.shorts_ideas.map((s) => `<div class="hook"><b>${esc(s.hook || "")}</b><div class="small muted">${esc(s.shows || "")} · döngü: ${esc(s.loop || "")}</div></div>`).join("")}</div>` : ""}
    </div></div>`;
  $("#pk-copy").onclick = async () => copyText(await api(`/api/projects/${cid}/${slug}/prompt/package`));
  $("#pk-apply").onclick = () => $("#pk-box").classList.toggle("hidden");
  $("#pk-go").onclick = async () => {
    try { const r = await api(`/api/projects/${cid}/${slug}/apply/package`, { method: "POST", body: { text: $("#pk-text").value } }); toast(`${r.titles} başlık, ${r.thumbnails} kapak tarifi`); viewProject(cid, slug, "pack"); }
    catch (e) { toast(e.message, true); }
  };
  const saveThumbs = async (render) => {
    try { const r = await api(`/api/projects/${cid}/${slug}/thumbnails`, { method: "PUT", body: { yaml: $("#th-yaml").value, render } });
      if (r.job) { watch(r.job, "Kapak görselleri"); state.onJobsDone = () => viewProject(cid, slug, "pack"); } else toast("Kaydedildi"); }
    catch (e) { toast(e.message, true); }
  };
  $("#th-save").onclick = () => saveThumbs(false);
  $("#pk-render").onclick = () => saveThumbs(true);
  $$('#titles input[name="title"]').forEach((r) => (r.onchange = async () => {
    const t = pub.title_variants[+r.value];
    await api(`/api/projects/${cid}/${slug}/publish`, { method: "PUT", body: { title_used: t } });
    toast("Başlık seçildi"); viewProject(cid, slug, "pack");
  }));
  $("#t-add").onclick = async () => {
    const t = $("#t-new").value.trim(); if (!t) return;
    await api(`/api/projects/${cid}/${slug}/publish`, { method: "PUT", body: { title_variants: [...(pub.title_variants || []), t] } });
    viewProject(cid, slug, "pack");
  };
}

/* ------------------------------------------------------------ publish record + retention */
function projPublish(cid, slug, el) {
  const pub = P.publish, pred = pub.prediction || {};
  const series = P.series || {};
  const langs = P.languages;
  const m = pub.metrics || [];
  el.innerHTML = `<div class="grid g2">
    <div class="card"><h3>Yayın kaydı</h3>
      <p class="small muted" style="margin-top:0">Yayından <b>önce</b> tahminini yaz: 30 video sonra sezginin mi, sinyallerin mi daha iyi tahmin ettiğini göreceksin.</p>
      <div class="form2">
        <label>Seri<select id="pb-series"><option value="">–</option>${Object.entries(series).map(([k, s]) => `<option value="${k}" ${pub.series === k ? "selected" : ""}>${esc(s.name)}</option>`).join("")}</select></label>
        <label>Tür<select id="pb-slot">${["long", "short"].map((t) => `<option ${pub.slot === t ? "selected" : ""} value="${t}">${t === "long" ? "Uzun video" : "Short"}</option>`).join("")}</select></label>
        <label>Açılış tipi<select id="pb-hook"><option value="">–</option>${Object.entries(P.hook_types).map(([k, v]) => `<option value="${k}" ${pub.hook_type === k ? "selected" : ""}>${esc(v)}</option>`).join("")}</select></label>
        <label>Planlanan tarih<input type="date" id="pb-planned" value="${esc(pub.planned_date || "")}"></label>
        <label>Kullanılan başlık<input id="pb-title" value="${esc(pub.title_used || P.meta.title || "")}"></label>
        <label>Canlı kapak<select id="pb-thumb">${[1, 2, 3].map((n) => `<option value="${n}" ${pub.thumbnail_used == n ? "selected" : ""}>${String.fromCharCode(64 + n)}</option>`).join("")}</select></label>
        <label>YouTube video id<input id="pb-yt" value="${esc(pub.youtube_id || "")}" placeholder="11 karakterlik id ya da video linki"></label>
        <label>Yayın tarihi<input type="date" id="pb-date" value="${esc(pub.published_at || "")}"></label>
        <label>Tahmin: 28 günde en az<input type="number" id="pb-lo" value="${pred.views_28d_low ?? ""}"></label>
        <label>Tahmin: 28 günde en çok<input type="number" id="pb-hi" value="${pred.views_28d_high ?? ""}"></label>
        <label>Sezgi (1–5)<select id="pb-gut"><option value="">–</option>${[1, 2, 3, 4, 5].map((n) => `<option ${pred.gut == n ? "selected" : ""}>${n}</option>`).join("")}</select></label>
      </div>
      <label class="f">Notlar</label><textarea id="pb-notes" rows="3">${esc(pub.notes || "")}</textarea>
      <div class="row" style="margin-top:10px"><button class="primary" id="pb-save">Kaydet</button>${pub.youtube_id ? `<a class="btn" target="_blank" href="https://studio.youtube.com/video/${esc(pub.youtube_id)}/analytics">YouTube Studio'da aç</a>` : ""}</div></div>
    <div class="card"><h3>Performans ölçümleri</h3>
      <p class="small muted" style="margin-top:0">YouTube Studio → Analytics'ten 2., 7. ve 28. günde bir satır gir.</p>
      <table class="mini"><thead><tr><th>Tarih</th><th>Gün</th><th>İzlenme</th><th>Gösterim</th><th>TO %</th><th>Ort. süre</th><th>İzleme %</th><th>Abone</th></tr></thead>
        <tbody>${m.map((r) => `<tr><td>${esc(r.date)}</td><td>${r.day ?? ""}</td><td>${fmtN(r.views)}</td><td>${fmtN(r.impressions)}</td><td>${r.ctr ?? ""}</td><td>${r.avd_sec ? Math.floor(r.avd_sec / 60) + ":" + String(r.avd_sec % 60).padStart(2, "0") : ""}</td><td>${r.avg_pct ?? ""}</td><td>${r.subs ?? ""}</td></tr>`).join("") || '<tr><td colspan="8" class="muted">Henüz ölçüm yok</td></tr>'}</tbody></table>
      <div class="form2" style="margin-top:10px">
        <label>Tarih<input type="date" id="mt-date" value="${new Date().toISOString().slice(0, 10)}"></label>
        <label>İzlenme<input type="number" id="mt-views"></label>
        <label>Gösterim<input type="number" id="mt-imp"></label>
        <label>Tıklama oranı %<input type="number" step="0.1" id="mt-ctr"></label>
        <label>Ort. izleme süresi (sn)<input type="number" id="mt-avd"></label>
        <label>Ort. izlenme %<input type="number" step="0.1" id="mt-pct"></label>
        <label>Kazanılan abone<input type="number" id="mt-subs"></label>
      </div><div class="row" style="margin-top:8px"><button id="mt-add">Ölçümü ekle</button></div></div></div>
    <div class="card" style="margin-top:14px"><div class="spread"><h3 style="margin:0">İzlenme eğrisi → shot haritası</h3>
      <div class="row"><select id="rt-lang">${langs.map((l) => `<option value="${l}">${LANG_TR[l] || l}</option>`).join("")}</select><button class="sm" id="rt-open">Veri yapıştır</button></div></div>
      <p class="small muted">YouTube Studio → videonun Analytics'i → Etkileşim → Kitleyi elde tutma → Gelişmiş mod → dışa aktar (CSV), ya da tablodan iki sütunu (konum, elde tutma %) kopyala.</p>
      <div id="rt-box" class="hidden"><textarea id="rt-text" class="code" rows="6" placeholder="Video konumu (%)\tMutlak kitleyi elde tutma (%)&#10;0\t100&#10;1\t92 ..."></textarea><div class="row" style="margin-top:6px"><button class="sm primary" id="rt-go">İçe aktar</button></div></div>
      <div id="rt-view"></div></div>`;
  const val = (id) => $(id).value;
  $("#pb-save").onclick = async () => {
    const body = { series: val("#pb-series"), slot: val("#pb-slot"), hook_type: val("#pb-hook"), planned_date: val("#pb-planned"), title_used: val("#pb-title"),
      thumbnail_used: +val("#pb-thumb"), youtube_id: val("#pb-yt").trim().replace(/.*(?:v=|youtu\.be\/|video\/)([\w-]{11}).*/, "$1"), published_at: val("#pb-date"), notes: val("#pb-notes"),
      prediction: { views_28d_low: val("#pb-lo") ? +val("#pb-lo") : null, views_28d_high: val("#pb-hi") ? +val("#pb-hi") : null, gut: val("#pb-gut") ? +val("#pb-gut") : null } };
    try { await api(`/api/projects/${cid}/${slug}/publish`, { method: "PUT", body }); toast("Yayın kaydı kaydedildi"); viewProject(cid, slug, "pub"); } catch (e) { toast(e.message, true); }
  };
  $("#mt-add").onclick = async () => {
    const n = (id) => (val(id) === "" ? null : +val(id));
    try { await api(`/api/projects/${cid}/${slug}/metrics`, { method: "POST", body: { date: val("#mt-date"), views: n("#mt-views"), impressions: n("#mt-imp"), ctr: n("#mt-ctr"), avd_sec: n("#mt-avd"), avg_pct: n("#mt-pct"), subs: n("#mt-subs") } }); toast("Ölçüm eklendi"); viewProject(cid, slug, "pub"); }
    catch (e) { toast(e.message, true); }
  };
  const draw = () => retentionView($("#rt-view"), P.retention[$("#rt-lang").value]);
  $("#rt-lang").onchange = draw; draw();
  $("#rt-open").onclick = () => $("#rt-box").classList.toggle("hidden");
  $("#rt-go").onclick = async () => {
    try { const r = await api(`/api/projects/${cid}/${slug}/retention`, { method: "POST", body: { lang: $("#rt-lang").value, text: $("#rt-text").value } }); P.retention[r.lang] = r; $("#rt-box").classList.add("hidden"); draw(); toast("Eğri içe aktarıldı"); }
    catch (e) { toast(e.message, true); }
  };
}

function retentionView(el, r) {
  if (!r) { el.innerHTML = '<p class="muted small">Bu dil için izlenme verisi yok.</p>'; return; }
  const W = 1000, H = 260, pad = 36, dur = r.duration || 1;
  const X = (t) => pad + (t / dur) * (W - pad - 8), Y = (v) => 10 + (1 - Math.min(v, 110) / 110) * (H - 40);
  const shotById = Object.fromEntries(P.shots.map((s) => [s.id, s]));
  const line = r.points.map((p, i) => `${i ? "L" : "M"}${X(p.t).toFixed(1)},${Y(p.ret).toFixed(1)}`).join(" ");
  const area = `${line} L${X(r.points[r.points.length - 1].t).toFixed(1)},${Y(0)} L${X(r.points[0].t).toFixed(1)},${Y(0)} Z`;
  const grid = [0, 25, 50, 75, 100].map((v) => `<line x1="${pad}" x2="${W - 8}" y1="${Y(v)}" y2="${Y(v)}" class="rt-grid"/><text x="${pad - 6}" y="${Y(v) + 4}" text-anchor="end" class="rt-lbl">${v}</text>`).join("");
  const paraBands = (r.paragraphs || []).map((p, i) => `<rect x="${X(p.start)}" y="${Y(110)}" width="${Math.max(0, X(p.end) - X(p.start))}" height="${Y(0) - Y(110)}" class="${i % 2 ? "rt-band2" : "rt-band"}"><title>Paragraf ${p.para + 1}: ${p.lost ?? "?"} puan kayıp</title></rect>`).join("");
  const ticks = r.shots.map((s) => `<line x1="${X(s.start)}" x2="${X(s.start)}" y1="${Y(0)}" y2="${Y(0) + 6}" class="rt-tick"/>`).join("");
  const drops = r.drops.map((d, i) => `<g><rect x="${X(d.from)}" y="${Y(110)}" width="${Math.max(3, X(d.to) - X(d.from))}" height="${Y(0) - Y(110)}" class="rt-drop"/><text x="${X(d.from) + 3}" y="${Y(110) + 14}" class="rt-num">${i + 1}</text></g>`).join("");
  const mm = (t) => `${Math.floor(t / 60)}:${String(Math.round(t % 60)).padStart(2, "0")}`;
  el.innerHTML = `<div class="row" style="margin:6px 0 10px">${pill("30. sn: %" + (r.at30 ?? "–"), r.at30 >= 70 ? "ok" : r.at30 >= 55 ? "warn" : "bad")} ${pill("1. dk: %" + (r.at60 ?? "–"))} ${pill("son: %" + (r.end ?? "–"))} <span class="small muted">süre ${mm(dur)} · ${r.shots.length} shot</span></div>
    <div class="rt-wrap"><svg viewBox="0 0 ${W} ${H}" class="rt" id="rt-svg">${paraBands}${grid}${drops}<path d="${area}" class="rt-area"/><path d="${line}" class="rt-line"/>${ticks}<line id="rt-cursor" x1="0" x2="0" y1="${Y(110)}" y2="${Y(0)}" class="rt-cursor hidden"/></svg></div>
    <div id="rt-hover" class="small muted" style="min-height:22px"></div>
    <h3 style="margin-top:10px">En büyük düşüşler</h3>
    <div class="drops">${r.drops.map((d, i) => { const s = shotById[d.shot] || {}; return `<div class="drop"><div class="drop-img" style="${s.image ? `background-image:url('${s.image}')` : ""}"></div>
      <div><b>${i + 1}.</b> ${mm(d.from)}–${mm(d.to)} · <b>−${d.lost}</b> puan · ${esc(d.shot)} (paragraf ${(d.para ?? 0) + 1})<div>“${esc(d.text)}”</div></div></div>`; }).join("") || '<p class="muted small">Belirgin düşüş yok.</p>'}</div>`;
  const svg = $("#rt-svg");
  svg.onmousemove = (e) => {
    const b = svg.getBoundingClientRect();
    const t = ((e.clientX - b.left) / b.width * W - pad) / (W - pad - 8) * dur;
    if (t < 0 || t > dur) return;
    const s = r.shots.find((x) => x.start <= t && t < x.end) || r.shots[r.shots.length - 1];
    const p = r.points.reduce((a, q) => (Math.abs(q.t - t) < Math.abs(a.t - t) ? q : a), r.points[0]);
    const c = $("#rt-cursor"); c.classList.remove("hidden"); c.setAttribute("x1", X(t)); c.setAttribute("x2", X(t));
    $("#rt-hover").textContent = `${mm(t)} · %${p.ret} · ${s.id}: ${(shotById[s.id] || {}).text || ""}`;
  };
}

/* ------------------------------------------------------------ calendar */
async function channelCalendar(cid, el, d) {
  let offset = state.calOffset || 0;
  const cal = await api(`/api/channels/${cid}/calendar?weeks=6&offset=${offset}`);
  const st = cal.settings;
  const types = st.slot_types || [];
  el.innerHTML = `<div class="spread" style="margin-bottom:10px">
      <div class="row">${pill(`haftada ${st.days.length} video: ${st.days.join(", ")}`)} ${pill(`~${cal.hours_per_week} saat/hafta`, cal.hours_per_week > 12 ? "warn" : "ok")} ${pill(`önümüzdeki 4 hafta: ${cal.filled_4w}/${cal.slots_4w} dolu`, cal.filled_4w >= cal.slots_4w ? "ok" : "warn")}</div>
      <div class="row"><button class="sm" id="cal-prev">← Önceki</button><button class="sm" id="cal-now">Bugün</button><button class="sm" id="cal-next">Sonraki →</button></div></div>
    ${cal.hours_per_week > 12 ? `<div class="help small">Bu ritim haftada yaklaşık <b>${cal.hours_per_week} saat</b> demek (video başına ${st.hours_per_video} saat). Kanal ayarlarında <span class="kbd">schedule.slot_types</span> ile bazı günleri <span class="kbd">short</span> yapabilir ya da ilk 10 videodan sonra gerçek süreni <span class="kbd">hours_per_video</span>'ya yazabilirsin.</div>` : ""}
    <div class="cal">${cal.weeks.map((w) => `<div class="cal-week"><div class="cal-wk">${esc(w.start.slice(5).split("-").reverse().join("."))}</div>
      ${w.slots.map((s) => `<div class="cal-slot ${s.past ? "past" : ""} ${s.items.length ? "full" : "empty"}" data-date="${s.date}">
        <div class="spread small"><b>${esc(s.day)} ${esc(s.date.slice(8))}.${esc(s.date.slice(5, 7))}</b><span class="pill ${s.type === "short" ? "info" : ""}">${s.type === "short" ? "short" : "uzun"}</span></div>
        ${s.items.map((it) => `<a class="cal-item ${it.risk ? "risk" : ""}" href="#/p/${cid}/${it.slug}"><div class="t">${esc(it.title)}</div>
          <div class="progress" style="margin:4px 0"><span style="width:${it.progress}%;background:${it.progress === 100 ? "var(--ok)" : it.risk ? "var(--accent)" : "var(--warn)"}"></span></div>
          <div class="small muted">${esc(it.stage)}${it.series_name ? " · " + esc(it.series_name) : ""}</div></a>
          <button class="ghost sm cal-un" data-slug="${it.slug}" title="Takvimden çıkar">×</button>`).join("")}
        ${!s.items.length && !s.past ? `<select class="cal-pick" data-date="${s.date}"><option value="">+ proje yerleştir</option>${cal.unscheduled.map((p) => `<option value="${p.slug}">${esc(p.title)}</option>`).join("")}</select>` : ""}
      </div>`).join("")}</div>`).join("")}</div>
    <h3 style="margin-top:18px">Takvimde olmayan projeler (${cal.unscheduled.length})</h3>
    <div class="small">${cal.unscheduled.map((p) => `<a href="#/p/${cid}/${p.slug}">${esc(p.title)}</a>`).join(" · ") || '<span class="muted">Hepsi takvimde. Fikir havuzundan yeni proje aç.</span>'}</div>`;
  const go = (o) => { state.calOffset = o; channelCalendar(cid, el, d); };
  $("#cal-prev").onclick = () => go(offset - 4);
  $("#cal-next").onclick = () => go(offset + 4);
  $("#cal-now").onclick = () => go(0);
  $$(".cal-pick").forEach((s) => (s.onchange = async () => { if (!s.value) return; await api(`/api/channels/${cid}/calendar/assign`, { method: "POST", body: { slug: s.value, date: s.dataset.date } }); toast("Takvime eklendi"); go(offset); }));
  $$(".cal-un").forEach((b) => (b.onclick = async (e) => { e.preventDefault(); await api(`/api/channels/${cid}/calendar/assign`, { method: "POST", body: { slug: b.dataset.slug, date: "" } }); go(offset); }));
}

/* ------------------------------------------------------------ source library */
async function viewLibrary() {
  const lib = await api("/api/library");
  const f = { q: "" };
  app.innerHTML = `<div class="spread"><h1>Kaynak kütüphanesi</h1><div class="row"><button id="lb-check">Bağlantıları kontrol et</button><button id="lb-edit">YAML düzenle</button></div></div>
    <p class="sub">Tüm kanalların tüm videoları kaynaklarını buradan id ile gösterir. Bir çalışma bir kez girilir, her videoda yeniden kullanılır. Tercih sırası: meta-analiz / derleme / birincil çalışma; haber yazıları sadece yardımcı.</p>
    <div id="lb-yaml" class="card hidden" style="margin-bottom:12px"><textarea id="lb-text" class="code" rows="22" spellcheck="false">${esc(lib.yaml)}</textarea><div class="row" style="margin-top:8px"><button class="primary" id="lb-save">Kaydet</button></div></div>
    <div id="live-box" class="hidden" style="margin-bottom:12px"><div id="live-status" class="small muted"></div><div class="log" id="live-log" style="height:160px"></div></div>
    <input id="lb-q" placeholder="Ara (yazar, konu, id)…" style="width:320px;margin-bottom:10px">
    <table><thead><tr><th>Kaynak</th><th style="width:110px">Tür</th><th>Neyi gösteremez</th><th style="width:170px">Kullanan videolar</th><th style="width:90px">Bağlantı</th></tr></thead><tbody id="lb-body"></tbody></table>`;
  const render = () => {
    const rows = lib.sources.filter((s) => !f.q || JSON.stringify(s).toLowerCase().includes(f.q));
    $("#lb-body").innerHTML = rows.map((s) => `<tr><td><div class="t">${esc(s.title || s.id)}</div><div class="a">${esc(s.id)} · ${esc(s.authors || "")} ${esc(s.year || "")} ${s.venue ? "· " + esc(s.venue) : ""} ${s.url ? `· <a href="${esc(s.url)}" target="_blank">aç</a>` : ""}</div>${s.population ? `<div class="a">Örneklem: ${esc(s.population)}</div>` : ""}</td>
      <td>${pill(s.type || "?", ["primary", "review", "meta-analysis"].includes(s.type) ? "ok" : s.type === "news" ? "warn" : "")}</td>
      <td class="small">${esc(s.limits || "")}</td>
      <td class="small">${(s.used_by || []).map((u) => `<a href="#/p/${u}">${esc(u.split("/")[1])}</a>`).join("<br>") || '<span class="muted">–</span>'}</td>
      <td>${s.link ? pill(s.link.ok ? "açılıyor" : String(s.link.status), s.link.ok ? "ok" : "bad") : '<span class="muted small">bakılmadı</span>'}</td></tr>`).join("");
  };
  $("#lb-q").oninput = (e) => { f.q = e.target.value.toLowerCase(); render(); };
  $("#lb-edit").onclick = () => $("#lb-yaml").classList.toggle("hidden");
  $("#lb-save").onclick = async () => { try { await api("/api/library", { method: "PUT", body: { yaml: $("#lb-text").value } }); toast("Kaydedildi"); viewLibrary(); } catch (e) { toast(e.message, true); } };
  $("#lb-check").onclick = async () => { const r = await api("/api/tools/check-links", { method: "POST", body: {} }); watch(r.job, "Bağlantı kontrolü"); state.onJobsDone = viewLibrary; };
  render();
}
