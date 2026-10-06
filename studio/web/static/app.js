/* Video Fabrikası — single-page control panel (vanilla JS, no build step). */
"use strict";

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const app = $("#app");
const STATUS_TR = { idea: "Fikir", researching: "Araştırma", scripting: "Senaryo", production: "Üretim", published: "Yayında", dropped: "Bırakıldı" };
const STATUS_COLOR = { idea: "#cfc6b4", researching: "#8fb3c9", scripting: "#e3a447", production: "#d8342c", published: "#4f8a3c", dropped: "#999" };
const LANG_TR = { en: "İngilizce", tr: "Türkçe", es: "İspanyolca", pt: "Portekizce", de: "Almanca", fr: "Fransızca" };
let state = { overview: null, polling: null, watchJob: null };

async function api(path, opts = {}) {
  const o = { headers: { "Content-Type": "application/json" }, ...opts };
  if (o.body && typeof o.body !== "string") o.body = JSON.stringify(o.body);
  const r = await fetch(path, o);
  const ct = r.headers.get("content-type") || "";
  const data = ct.includes("json") ? await r.json() : await r.text();
  if (!r.ok) throw new Error(typeof data === "string" ? data : data.detail || JSON.stringify(data));
  return data;
}
function toast(msg, err = false) {
  const t = $("#toast");
  t.textContent = msg; t.className = "show" + (err ? " err" : "");
  clearTimeout(t._h); t._h = setTimeout(() => (t.className = ""), err ? 5000 : 2200);
}
async function copyText(text) {
  try { await navigator.clipboard.writeText(text); toast("Panoya kopyalandı"); }
  catch { const ta = document.createElement("textarea"); ta.value = text; document.body.appendChild(ta); ta.select(); document.execCommand("copy"); ta.remove(); toast("Panoya kopyalandı"); }
}
function pill(text, cls = "") { return `<span class="pill ${cls}">${esc(text)}</span>`; }
function ago(ts) { if (!ts) return ""; const s = Math.round(Date.now() / 1000 - ts); return s < 60 ? `${s} sn önce` : s < 3600 ? `${Math.round(s / 60)} dk önce` : `${Math.round(s / 3600)} sa önce`; }
function secs(a, b) { if (!a) return ""; const s = Math.round((b || Date.now() / 1000) - a); return s < 60 ? `${s} sn` : `${Math.floor(s / 60)} dk ${s % 60} sn`; }

/* ------------------------------------------------------------ router */
const routes = [
  [/^#?\/?$/, viewHome],
  [/^#\/c\/([^/]+)(?:\/(\w+))?$/, viewChannel],
  [/^#\/p\/([^/]+)\/([^/]+)(?:\/(\w+))?$/, viewProject],
  [/^#\/settings$/, viewSettings],
  [/^#\/catalog$/, viewCatalog],
  [/^#\/library$/, () => viewLibrary()],
  [/^#\/jobs$/, viewJobs],
  [/^#\/new-channel$/, viewNewChannel],
];
function fireDone() { const f = state.onJobsDone; state.onJobsDone = null; if (f) f(); }
async function route() {
  closeDrawer();
  state.onJobsDone = null;
  const h = location.hash || "#/";
  $$("nav a").forEach((a) => a.classList.toggle("active", a.getAttribute("href") === h || (h.startsWith("#/c/") && a.getAttribute("href") === "#/c/" + h.split("/")[2])));
  for (const [re, fn] of routes) {
    const m = h.match(re);
    if (m) { try { await fn(...m.slice(1)); } catch (e) { app.innerHTML = `<div class="card"><h3>Hata</h3><div class="err">${esc(e.message)}</div></div>`; } return; }
  }
  app.innerHTML = "<p>Sayfa bulunamadı.</p>";
}
window.addEventListener("hashchange", route);

/* ------------------------------------------------------------ sidebar + polling */
async function refreshSidebar() {
  const ov = await api("/api/overview");
  state.overview = ov;
  $("#nav-channels").innerHTML = ov.channels.map((c) => `<a href="#/c/${c.id}">${esc(c.name)} <span class="small muted">${c.languages.join("·")}</span></a>`).join("");
  const running = ov.jobs.filter((j) => j.status === "running" || j.status === "queued").length;
  const b = $("#nav-jobs-badge"); b.textContent = running; b.classList.toggle("hidden", !running);
  const p = ov.providers, free = (x, f) => (f.includes(x) ? pill("ücretsiz", "ok") : pill("ücretli", "warn"));
  $("#provider-foot").innerHTML = `
    <div class="row"><span>Ses</span><span>${esc(p.tts)} ${free(p.tts, ["kokoro", "edge", "estimate"])}</span></div>
    <div class="row"><span>Görsel</span><span>${esc(p.images)} ${free(p.images, ["svg"])}</span></div>
    <div class="row"><span>Plan</span><span>${esc(p.planner)} ${free(p.planner, ["manual"])}</span></div>`;
  $$("nav a").forEach((a) => a.classList.toggle("active", a.getAttribute("href") === (location.hash || "#/")));
}
function startPolling() {
  clearInterval(state.polling);
  state.polling = setInterval(async () => {
    try {
      const jobs = await api("/api/jobs");
      const running = jobs.filter((j) => j.status === "running" || j.status === "queued").length;
      const b = $("#nav-jobs-badge"); b.textContent = running; b.classList.toggle("hidden", !running);
      if (state.lastRunning && !running) { toast("İşler tamamlandı"); fireDone(); }
      state.lastRunning = running;
      if (state.watchJob) await pumpLog();
    } catch { /* server restarting */ }
  }, 1500);
}
async function pumpLog() {
  const el = $("#live-log");
  if (!el || !state.watchJob) return;
  const j = await api(`/api/jobs/${state.watchJob.id}?since=${state.watchJob.seen}`);
  if (j.log.length) { el.textContent += j.log.join("\n") + "\n"; el.scrollTop = el.scrollHeight; }
  state.watchJob.seen = j.log_len;
  const st = $("#live-status"); if (st) st.innerHTML = `<span class="status-dot s-${j.status}"></span>${esc(j.label)} — ${esc(j.status)} ${j.started ? "· " + secs(j.started, j.finished) : ""}`;
  if (["done", "failed", "cancelled"].includes(j.status) && state.watchJob.final !== true) {
    state.watchJob.final = true;
    if (j.status === "failed") toast("İş başarısız oldu — günlüğe bak", true);
    setTimeout(fireDone, 300);
  }
}
function watch(jobId, label) {
  state.watchJob = { id: jobId, seen: 0, final: false };
  const el = $("#live-log"); if (el) el.textContent = `▶ ${label || "iş"} #${jobId}\n`;
  const box = $("#live-box"); if (box) box.classList.remove("hidden");
}

/* ------------------------------------------------------------ home */
async function viewHome() {
  const ov = await api("/api/overview");
  const totals = ov.channels.reduce((a, c) => ({ ideas: a.ideas + c.ideas, projects: a.projects + c.projects, videos: a.videos + c.videos }), { ideas: 0, projects: 0, videos: 0 });
  const keys = Object.entries(ov.secrets).map(([k, v]) => `${pill(k.replace("_API_KEY", ""), v ? "ok" : "")}`).join(" ");
  app.innerHTML = `
    <h1>Genel bakış</h1>
    <p class="sub">Fabrikanın durumu. Bir kanal seç, fikir havuzundan bir fikri projeye dönüştür, senaryoyu yaz, storyboard'u planla ve tek tuşla üret.</p>
    <div class="grid g4">
      <div class="card stat"><div class="n">${ov.channels.length}</div><div class="l">Kanal</div></div>
      <div class="card stat"><div class="n">${totals.ideas}</div><div class="l">Fikir</div></div>
      <div class="card stat"><div class="n">${totals.projects}</div><div class="l">Proje</div></div>
      <div class="card stat"><div class="n">${totals.videos}</div><div class="l">Üretilen video</div></div>
    </div>
    <h2>Kanallar</h2>
    <div class="grid g3">${ov.channels.map(channelCard).join("")}
      <a class="card link" href="#/new-channel" style="display:flex;align-items:center;justify-content:center;min-height:150px;color:var(--muted)">+ Yeni kanal ekle</a></div>
    <div class="grid g2" style="margin-top:22px">
      <div class="card"><h3>Son işler</h3>${ov.jobs.length ? ov.jobs.map(jobRow).join("") : '<p class="muted">Henüz iş yok.</p>'}</div>
      <div class="card"><h3>Servisler</h3>
        <p class="small muted" style="margin-top:0">Başlangıç ücretsiz: Kokoro ses, kodla çizim, Claude sohbetinde planlama. Ücretliye geçiş Ayarlar'dan tek satır.</p>
        <div class="row">${keys}</div>
        <p class="small" style="margin-bottom:0"><a href="#/settings">Ayarlar →</a></p></div>
    </div>`;
}
function channelCard(c) {
  const total = Object.values(c.ideas_by_status).reduce((a, b) => a + b, 0) || 1;
  const bar = Object.entries(c.ideas_by_status).filter(([, n]) => n).map(([s, n]) => `<span style="width:${(100 * n) / total}%;background:${STATUS_COLOR[s]}" title="${STATUS_TR[s]}: ${n}"></span>`).join("");
  return `<a class="card link" href="#/c/${c.id}">
    <div class="spread"><h3 style="margin:0">${esc(c.name)}</h3><span>${c.languages.map((l) => pill(l)).join(" ")}</span></div>
    <p class="small muted" style="min-height:34px">${esc(c.tagline).slice(0, 120)}</p>
    <div class="progress">${bar}</div>
    <div class="legend"><span>${c.ideas} fikir</span><span>${c.projects} proje</span><span>${c.videos} video</span></div></a>`;
}
function jobRow(j) {
  return `<div class="job-row" onclick="location.hash='#/jobs';setTimeout(()=>showJob(${j.id}),200)"><span><span class="status-dot s-${j.status}"></span>${esc(j.label)} ${j.project ? `<span class="muted small">· ${esc(j.project)}</span>` : ""}</span><span class="muted small">${ago(j.created)}</span></div>`;
}

/* ------------------------------------------------------------ new channel */
async function viewNewChannel() {
  app.innerHTML = `<h1>Yeni kanal</h1><p class="sub">Her kanalın kendi fikir havuzu, stili, sesi ve dilleri olur. Üretim hattı ortaktır.</p>
    <div class="card" style="max-width:620px">
      <label class="f">Kanal kimliği (klasör adı, küçük harf)</label><input id="nc-id" placeholder="history-of-medicine" style="width:100%">
      <label class="f">Kanal adı</label><input id="nc-name" placeholder="The Strange History of Medicine" style="width:100%">
      <label class="f">Tek cümlelik vaat</label><input id="nc-tag" placeholder="Weird, gross and brilliant moments in the history of healing" style="width:100%">
      <label class="f">Diller (ilk = ana dil)</label><input id="nc-langs" value="en, tr" style="width:100%">
      <div class="row" style="margin-top:16px"><button class="primary" id="nc-go">Kanalı oluştur</button></div></div>`;
  $("#nc-go").onclick = async () => {
    try {
      const r = await api("/api/channels", { method: "POST", body: { id: $("#nc-id").value.trim(), name: $("#nc-name").value.trim(), tagline: $("#nc-tag").value.trim(), languages: $("#nc-langs").value.split(",").map((s) => s.trim()).filter(Boolean) } });
      await refreshSidebar(); location.hash = `#/c/${r.id}`; toast("Kanal oluşturuldu");
    } catch (e) { toast(e.message, true); }
  };
}

/* ------------------------------------------------------------ channel */
async function viewChannel(cid, tab = "ideas") {
  const ch = await api(`/api/channels/${cid}`);
  const d = ch.data;
  app.innerHTML = `
    <div class="crumbs"><a href="#/">Genel bakış</a> / kanal</div>
    <div class="spread"><h1>${esc(d.name)}</h1><span>${(d.languages || []).map((l) => pill(LANG_TR[l] || l)).join(" ")} ${pill(d.category || "")}</span></div>
    <p class="sub">${esc(d.tagline || "")}</p>
    <div class="tabs">
      <a href="#/c/${cid}/ideas" class="${tab === "ideas" ? "active" : ""}">Fikir havuzu</a>
      <a href="#/c/${cid}/calendar" class="${tab === "calendar" ? "active" : ""}">Takvim</a>
      <a href="#/c/${cid}/projects" class="${tab === "projects" ? "active" : ""}">Projeler</a>
      <a href="#/c/${cid}/compile" class="${tab === "compile" ? "active" : ""}">Derleme</a>
      <a href="#/c/${cid}/settings" class="${tab === "settings" ? "active" : ""}">Kanal ayarları</a>
    </div><div id="tab"></div>`;
  const el = $("#tab");
  if (tab === "ideas") return channelIdeas(cid, el);
  if (tab === "projects") return channelProjects(cid, el);
  if (tab === "compile") return channelCompile(cid, el, d);
  if (tab === "calendar") return channelCalendar(cid, el, d);
  if (tab === "settings") return channelSettings(cid, el, ch);
}

async function channelIdeas(cid, el) {
  const data = await api(`/api/channels/${cid}/ideas`);
  const pillars = data.pillars || {};
  const f = { q: "", pillar: "", priority: "", status: "" };
  el.innerHTML = `
    <div class="spread" style="margin-bottom:12px">
      <div class="row">
        <input id="fi-q" placeholder="Ara…" style="width:220px">
        <select id="fi-pillar"><option value="">Tüm sütunlar</option>${Object.entries(pillars).map(([k, v]) => `<option value="${k}">${k} · ${esc(v.name)}</option>`).join("")}</select>
        <select id="fi-pri"><option value="">Tüm öncelikler</option><option>A</option><option>B</option><option>C</option></select>
        <select id="fi-status"><option value="">Tüm durumlar</option>${data.statuses.map((s) => `<option value="${s}">${STATUS_TR[s]}</option>`).join("")}</select>
        <select id="fi-sort"><option value="priority">Sıra: öncelik</option><option value="demand">Sıra: talep</option><option value="gap">Sıra: boşluk (küçük kanal kazanıyor)</option><option value="competition">Sıra: en az rekabet</option><option value="gut">Sıra: sezgi puanım</option></select>
      </div>
      <div class="row"><button id="fi-sig" title="YouTube Data API ile arama sonuçlarını ölçer (ücretsiz anahtar, günlük ~95 fikir)">Sinyalleri güncelle</button><button id="fi-add">+ Fikir ekle</button></div>
    </div>
    <div class="help small">Sinyaller YouTube'da o konuyu aratınca çıkan ilk 25 videodan hesaplanır. <b>Talep</b>: tipik izlenme. <b>Rekabet</b>: son 12 ayda çıkan video ve büyük kanal sayısı. <b>Boşluk</b>: küçük kanalların aboneden çok izlenme aldığı konu. Bunlar karar vermez, sana bilgi verir: son söz <b>sezgi</b> puanın (1–5).</div>
    <div id="live-box" class="hidden" style="margin-bottom:12px"><div id="live-status" class="small muted"></div><div class="log" id="live-log" style="height:140px"></div></div>
    <div id="fi-form" class="card hidden" style="margin-bottom:12px">
      <div class="grid g2"><div><label class="f">Başlık</label><input id="nf-title" style="width:100%"></div>
      <div class="row"><div><label class="f">Sütun</label><select id="nf-pillar">${Object.keys(pillars).map((k) => `<option>${k}</option>`).join("")}<option value="">—</option></select></div>
      <div><label class="f">Öncelik</label><select id="nf-pri"><option>A</option><option selected>B</option><option>C</option></select></div></div></div>
      <label class="f">Açı / kanca</label><input id="nf-angle" style="width:100%">
      <div class="row" style="margin-top:10px"><button class="primary" id="nf-save">Kaydet</button></div></div>
    <div id="fi-count" class="small muted" style="margin-bottom:6px"></div>
    <table><thead><tr><th style="width:44px"></th><th>Fikir</th><th style="width:130px">Sütun</th><th style="width:170px">Sinyal</th><th style="width:70px">Sezgi</th><th style="width:130px">Durum</th><th style="width:150px"></th></tr></thead><tbody id="fi-body"></tbody></table>`;
  const render = () => {
    const rank = { A: 0, B: 1, C: 2 };
    const sg = (i, k) => ((i.signals || {})[k] ?? -1);
    const sorters = {
      priority: (a, b) => (rank[a.priority] ?? 1) - (rank[b.priority] ?? 1),
      demand: (a, b) => sg(b, "median_views") - sg(a, "median_views"),
      gap: (a, b) => sg(b, "outlier") - sg(a, "outlier"),
      competition: (a, b) => (sg(a, "competition") < 0 ? 99 : sg(a, "competition")) - (sg(b, "competition") < 0 ? 99 : sg(b, "competition")),
      gut: (a, b) => (b.gut || 0) - (a.gut || 0),
    };
    const rows = data.ideas.slice().sort(sorters[f.sort || "priority"]).filter((i) => (!f.q || (i.title + " " + (i.angle || "")).toLowerCase().includes(f.q)) && (!f.pillar || i.pillar === f.pillar) && (!f.priority || i.priority === f.priority) && (!f.status || i.status === f.status));
    $("#fi-count").textContent = `${rows.length} / ${data.ideas.length} fikir`;
    $("#fi-body").innerHTML = rows.map((i) => `<tr>
      <td>${pill(i.priority || "B", i.priority || "B")}</td>
      <td><div class="t">${esc(i.title)}</div><div class="a">${esc(i.angle || "")}${i.demand ? ` <span class="pill info">talep: ${esc(i.demand)}</span>` : ""}</div></td>
      <td class="small">${esc(i.pillar)} ${pillars[i.pillar] ? `<div class="muted">${esc(pillars[i.pillar].name)}</div>` : ""}</td>
      <td class="small">${signalCell(i.signals)}</td>
      <td><select class="fi-gut" data-id="${i.id}"><option value="">–</option>${[1, 2, 3, 4, 5].map((n) => `<option ${i.gut == n ? "selected" : ""}>${n}</option>`).join("")}</select></td>
      <td><select data-id="${i.id}" class="fi-st">${data.statuses.map((s) => `<option value="${s}" ${i.status === s ? "selected" : ""}>${STATUS_TR[s]}</option>`).join("")}</select></td>
      <td>${i.project ? `<a class="btn sm" href="#/p/${cid}/${i.project}">Projeyi aç →</a>` : `<button class="sm fi-go" data-id="${i.id}">Projeye dönüştür</button>`}</td></tr>`).join("");
    $$(".fi-st").forEach((s) => (s.onchange = async () => { const r = await api(`/api/channels/${cid}/ideas/${s.dataset.id}`, { method: "PATCH", body: { status: s.value } }); Object.assign(data.ideas.find((x) => x.id === r.id), r); toast("Durum güncellendi"); }));
    $$(".fi-gut").forEach((s) => (s.onchange = async () => { const r = await api(`/api/channels/${cid}/ideas/${s.dataset.id}`, { method: "PATCH", body: { gut: s.value ? +s.value : null } }); Object.assign(data.ideas.find((x) => x.id === r.id), r); toast("Sezgi puanı kaydedildi"); }));
    $$(".fi-go").forEach((b) => (b.onclick = async () => { const r = await api(`/api/channels/${cid}/ideas/${b.dataset.id}/project`, { method: "POST" }); location.hash = `#/p/${cid}/${r.slug}`; toast("Proje oluşturuldu"); }));
  };
  $("#fi-q").oninput = (e) => { f.q = e.target.value.toLowerCase(); render(); };
  $("#fi-pillar").onchange = (e) => { f.pillar = e.target.value; render(); };
  $("#fi-pri").onchange = (e) => { f.priority = e.target.value; render(); };
  $("#fi-status").onchange = (e) => { f.status = e.target.value; render(); };
  $("#fi-sort").onchange = (e) => { f.sort = e.target.value; render(); };
  $("#fi-sig").onclick = async () => {
    const ids = f.pillar || f.priority || f.q ? $$(".fi-gut").map((s) => s.dataset.id).slice(0, 90) : null;
    try { const r = await api(`/api/channels/${cid}/signals`, { method: "POST", body: ids ? { ids } : { limit: 90 } }); watch(r.job, "Fikir sinyalleri"); state.onJobsDone = () => viewChannel(cid, "ideas"); toast("Sinyaller ölçülüyor…"); }
    catch (e) { toast(e.message, true); }
  };
  $("#fi-add").onclick = () => $("#fi-form").classList.toggle("hidden");
  $("#nf-save").onclick = async () => {
    try { const i = await api(`/api/channels/${cid}/ideas`, { method: "POST", body: { title: $("#nf-title").value, pillar: $("#nf-pillar").value, priority: $("#nf-pri").value, angle: $("#nf-angle").value } }); data.ideas.push(i); $("#fi-form").classList.add("hidden"); render(); toast("Fikir eklendi"); }
    catch (e) { toast(e.message, true); }
  };
  render();
}

async function channelProjects(cid, el) {
  el.innerHTML = `<div class="spread" style="margin-bottom:12px"><span class="muted">Projeler en yeniden eskiye.</span>
    <div class="row"><input id="np-title" placeholder="Yeni proje başlığı" style="width:320px"><button class="primary" id="np-go">+ Proje</button></div></div><div id="pl" class="grid g3"><div class="muted">Yükleniyor…</div></div>`;
  $("#np-go").onclick = async () => { try { const r = await api(`/api/channels/${cid}/projects`, { method: "POST", body: { title: $("#np-title").value } }); location.hash = `#/p/${cid}/${r.slug}`; } catch (e) { toast(e.message, true); } };
  const list = await api(`/api/channels/${cid}/projects`);
  $("#pl").innerHTML = list.length ? list.map((p) => `<a class="card link" href="#/p/${cid}/${p.slug}">
      <div class="thumb" style="${p.thumb ? `background-image:url('${p.thumb}')` : ""}"></div>
      <div class="spread"><h3 style="margin:0">${esc(p.title)}</h3></div>
      <div class="row" style="margin-top:8px">${p.ready ? pill("hazır", "ok") : pill("eksik", "bad")} ${pill(p.shots + " shot")} ${Object.entries(p.videos).map(([l, u]) => pill(l + (u ? " ✓" : " —"), u ? "ok" : "")).join(" ")}</div>
      ${p.blocks.length ? `<div class="small muted" style="margin-top:6px">${esc(p.blocks[0])}</div>` : ""}</a>`).join("") : '<p class="muted">Henüz proje yok. Fikir havuzundan bir fikri projeye dönüştür.</p>';
}

async function channelCompile(cid, el, d) {
  const list = await api(`/api/channels/${cid}/projects`);
  const langs = d.languages || ["en"];
  el.innerHTML = `<div class="help">Birden çok bitmiş videoyu tek uzun videoda birleştirir. Örneğin aynı sütundan 6–10 videoyla 1–2 saatlik "uyku için" derleme. Bu formatlar nişte milyonlarca izleniyor. Bölüm zaman damgaları kendiliğinden çıkar.</div>
    <div class="card"><div class="row"><label>Dil <select id="cp-lang">${langs.map((l) => `<option>${l}</option>`).join("")}</select></label>
    <input id="cp-title" placeholder="Başlık (örn. Ancient Bodies — 2 hours to fall asleep)" style="flex:1;min-width:280px"><button class="primary" id="cp-go">Derle</button></div>
    <div id="cp-list" style="margin-top:12px"></div></div>
    <div id="live-box" class="hidden" style="margin-top:14px"><div id="live-status" class="small muted"></div><div class="log" id="live-log"></div></div>`;
  const draw = () => {
    const lg = $("#cp-lang").value;
    const ok = list.filter((p) => p.videos[lg]);
    $("#cp-list").innerHTML = ok.length ? ok.map((p) => `<label class="check"><input type="checkbox" value="${p.slug}"> ${esc(p.title)}</label>`).join("") : `<p class="muted">Bu dilde bitmiş video yok.</p>`;
  };
  $("#cp-lang").onchange = draw; draw();
  $("#cp-go").onclick = async () => {
    const slugs = $$("#cp-list input:checked").map((i) => i.value);
    try { const r = await api("/api/compile", { method: "POST", body: { channel: cid, slugs, lang: $("#cp-lang").value, title: $("#cp-title").value } }); watch(r.job, "Derleme"); }
    catch (e) { toast(e.message, true); }
  };
}

async function channelSettings(cid, el, ch) {
  el.innerHTML = `<div class="grid g2"><div class="card"><h3>channel.yaml</h3>
    <p class="small muted">Kimlik, diller, maskot, renk paleti ve bu kanala özel ayarlar (<span class="kbd">overrides</span> altında config.yaml'ın her anahtarı ezilebilir).</p>
    <textarea id="cy" class="code" rows="24">${esc(ch.yaml)}</textarea><div class="row" style="margin-top:10px"><button class="primary" id="cy-save">Kaydet</button></div></div>
    <div class="card"><h3>Örnek ayarlar</h3><pre class="code small" style="white-space:pre-wrap">overrides:
  tts:
    provider: elevenlabs          # bu kanal ücretli sese geçti
    elevenlabs: {voice_id: "..."}
  images:
    default_engine: gemini        # bu kanal AI görselleri kullanıyor
style:
  palette: {sky_warm: "#e9e4d4", ochre: "#7aa0a8"}   # kanalın renk kimliği
prompt_style: "Muted blue-grey palette, clinical feel."</pre></div></div>
    <div class="grid g2" style="margin-top:16px"><div class="card"><h3>Marka görselleri</h3>
    <p class="small muted">YouTube Studio → Özelleştirme → Markalama: profil resmi (800×800), banner (2560×1440, yazı her cihazda görünen 1546×423 alanda) ve video filigranı (150×150). Maskotla, videolardaki çizim kitiyle çizilir. İsteğe bağlı <span class="kbd">branding:</span> ayarları için <span class="kbd">studio/branding.py</span>.</p>
    <div class="row"><button class="primary" id="br-make">Marka görsellerini üret</button></div>
    ${ch.branding && ch.branding.banner ? `<div style="margin-top:12px"><a href="${ch.branding.banner_guides}" target="_blank"><img src="${ch.branding.banner_guides}" style="width:100%;border-radius:8px" alt="banner"></a>
      <div class="row" style="margin-top:8px;align-items:center;gap:12px"><img src="${ch.branding.profile}" style="width:96px;height:96px;border-radius:50%" alt="profil"><img src="${ch.branding.watermark}" style="width:48px;height:48px" alt="filigran">
      <span class="small"><a href="${ch.branding.profile}" download>profile.png</a> · <a href="${ch.branding.banner}" download>banner.png</a> · <a href="${ch.branding.watermark}" download>watermark.png</a></span></div></div>` : ""}</div>
    <div class="card"><h3>Bilgi paketi (sohbet botu için)</h3>
    <p class="small muted">Kanalın tamamını tek dosyada toplar: kimlik, seriler, yazım kuralları, ses etiketleri, çizim kiti, fikir havuzu, yayın sonuçları, kaynak kütüphanesi ve örnek senaryo. Claude Project / ChatGPT / Gemini / DeepSeek'e "bilgi" olarak yükle; yayın ya da marka değişikliğinden sonra yeniden üretip değiştir.</p>
    <div class="row"><button class="primary" id="kn-make">Bilgi paketini üret</button>${ch.knowledge ? ` <a class="small" href="${ch.knowledge}" download="knowledge.md">knowledge.md indir</a>` : ""}</div></div></div>`;
  $("#br-make").onclick = async () => { const r = await api("/api/tools/branding", { method: "POST", body: { channel: cid } }); watch(r.job, "Marka görselleri"); state.onJobsDone = () => viewChannel(cid, "settings"); };
  $("#kn-make").onclick = async () => { const r = await api("/api/tools/knowledge", { method: "POST", body: { channel: cid } }); watch(r.job, "Bilgi paketi"); state.onJobsDone = () => viewChannel(cid, "settings"); };
  $("#cy-save").onclick = async () => { try { await api(`/api/channels/${cid}`, { method: "PUT", body: { yaml: $("#cy").value } }); toast("Kaydedildi"); refreshSidebar(); } catch (e) { toast(e.message, true); } };
}

/* ------------------------------------------------------------ project */
let P = null; // current project payload
async function loadProject(cid, slug) { P = await api(`/api/projects/${cid}/${slug}`); return P; }

async function viewProject(cid, slug, tab = "script") {
  await loadProject(cid, slug);
  const r = P.readiness;
  const blocks = r.checks.filter((c) => c.level === "block" && !c.ok).length;
  app.innerHTML = `
    <div class="crumbs"><a href="#/">Genel bakış</a> / <a href="#/c/${cid}/projects">${esc(cid)}</a> / proje</div>
    <div class="spread"><h1>${esc(P.meta.title || slug)}</h1><span>${r.ready ? pill("üretime hazır", "ok") : pill(blocks + " engel", "bad")}</span></div>
    <p class="sub small">${esc(slug)} ${P.meta.note ? "· " + esc(P.meta.note) : ""}</p>
    <div class="tabs">
      <a href="#/p/${cid}/${slug}/script" class="${tab === "script" ? "active" : ""}">1 · Senaryo & kaynaklar</a>
      <a href="#/p/${cid}/${slug}/board" class="${tab === "board" ? "active" : ""}">2 · Storyboard <span class="n">${P.shots.length}</span></a>
      <a href="#/p/${cid}/${slug}/make" class="${tab === "make" ? "active" : ""}">3 · Üretim</a>
      <a href="#/p/${cid}/${slug}/pack" class="${tab === "pack" ? "active" : ""}">4 · Kapak & başlık</a>
      <a href="#/p/${cid}/${slug}/out" class="${tab === "out" ? "active" : ""}">5 · Çıktılar</a>
      <a href="#/p/${cid}/${slug}/pub" class="${tab === "pub" ? "active" : ""}">6 · Yayın & performans</a>
      <a href="#/p/${cid}/${slug}/meta" class="${tab === "meta" ? "active" : ""}">Proje ayarları</a>
    </div><div id="tab"></div>`;
  const el = $("#tab");
  state.onJobsDone = null;
  if (tab === "script") return projScript(cid, slug, el);
  if (tab === "board") return projBoard(cid, slug, el);
  if (tab === "make") return projMake(cid, slug, el);
  if (tab === "out") return projOut(cid, slug, el);
  if (tab === "pack") return projPackage(cid, slug, el);
  if (tab === "pub") return projPublish(cid, slug, el);
  if (tab === "meta") return projMeta(cid, slug, el);
}

function checklist(r) {
  return r.checks.map((c) => `<div class="check"><span class="ic ${c.ok ? "ok" : c.level}">${c.ok ? "✓" : c.level === "block" ? "✕" : c.level === "warn" ? "!" : "·"}</span><span>${esc(c.message)}</span></div>`).join("");
}

function projScript(cid, slug, el) {
  const words = (t) => (t.replace(/^#.*$/gm, "").replace(/<!--[\s\S]*?-->/g, "").match(/\b\w+\b/g) || []).length;
  el.innerHTML = `<div class="grid g2">
    <div class="card"><div class="spread"><h3>Senaryo <span class="muted small" id="wc"></span></h3><div class="row"><button id="sc-save" class="primary sm">Kaydet</button><button id="sc-split" class="sm">Kaydet & böl →</button></div></div>
      <p class="small muted" style="margin:0 0 8px">Paragrafları boş satırla ayır. ~150 kelime ≈ 1 dakika. Kısa cümleler görsel temposunu artırır.</p>
      <textarea id="sc" rows="26">${esc(P.script)}</textarea></div>
    <div><div class="card"><div class="spread"><h3>Kaynaklar</h3><button id="so-save" class="primary sm">Kaydet</button></div>
      <p class="small muted" style="margin:0 0 8px">Serbest notlar: iddia + bağlantı. İddialar bölümü bunları ortak kütüphaneye ve cümlelere bağlar; açıklamaya sadece iddiaların kaynakları girer.</p>
      <textarea id="so" rows="8" class="code">${esc(P.sources)}</textarea></div>
      <div class="card" style="margin-top:14px" id="claims-card"></div>
      <div class="card" style="margin-top:14px"><h3>Kalite kapısı</h3>${checklist(P.readiness)}</div></div></div>`;
  const upd = () => ($("#wc").textContent = `· ${words($("#sc").value)} kelime ≈ ${(words($("#sc").value) / 150).toFixed(1)} dk`);
  $("#sc").oninput = upd; upd();
  // Every button saves BOTH boxes, so pasted sources are never lost, and the quality gate is refreshed afterwards.
  const saved = { sc: $("#sc").value, so: $("#so").value };
  const dirty = () => !!$("#sc") && ($("#sc").value !== saved.sc || $("#so").value !== saved.so);
  const mark = () => $$("#sc-save, #so-save").forEach((b) => (b.textContent = dirty() ? "Kaydet •" : "Kaydet"));
  $("#sc").addEventListener("input", mark); $("#so").addEventListener("input", mark);
  const saveAll = async () => {
    await api(`/api/projects/${cid}/${slug}/script`, { method: "PUT", body: { text: $("#sc").value } });
    await api(`/api/projects/${cid}/${slug}/sources`, { method: "PUT", body: { text: $("#so").value } });
    saved.sc = $("#sc").value; saved.so = $("#so").value; mark();
  };
  const saveAndRefresh = async () => { await saveAll(); toast("Senaryo ve kaynaklar kaydedildi"); await viewProject(cid, slug, "script"); };
  $("#sc-save").onclick = saveAndRefresh;
  $("#so-save").onclick = saveAndRefresh;
  $("#sc-split").onclick = async () => { await saveAll(); await api(`/api/projects/${cid}/${slug}/run`, { method: "POST", body: { step: "split" } }); toast("Kaydedildi, bölünüyor…"); state.onJobsDone = () => (location.hash = `#/p/${cid}/${slug}/board`); };
  window.onbeforeunload = () => (dirty() ? "Kaydedilmemiş değişiklik var" : undefined);
  renderClaims(cid, slug, $("#claims-card"));
}

function projBoard(cid, slug, el) {
  const unplanned = P.shots.filter((s) => !s.visual).length;
  const imgs = P.shots.filter((s) => s.image).length;
  el.innerHTML = `
    <div class="spread" style="margin-bottom:12px">
      <div class="row"><button id="b-split">Böl</button>
        <button id="b-prompt" class="${unplanned ? "accent" : ""}">Plan istemini kopyala ${unplanned ? `(${unplanned})` : ""}</button>
        <button id="b-apply">Planı uygula</button>
        <button id="b-images" class="primary">Görselleri üret</button>
        <button id="b-sheet">Kontak sayfası</button></div>
      <span class="small muted">${P.shots.length} shot · ${P.shots.length - unplanned} planlı · ${imgs} görsel</span></div>
    ${unplanned ? `<div class="help"><b>Planlama (ücretsiz yol):</b> "Plan istemini kopyala" → claude.ai'de yeni bir sohbete yapıştır → gelen YAML cevabı "Planı uygula" kutusuna yapıştır. Ücretli otomatik yol için Ayarlar'da <span class="kbd">planner.provider: anthropic</span>.</div>` : ""}
    <div id="apply-box" class="card hidden" style="margin-bottom:12px"><h3>Planı uygula</h3><textarea id="apply-text" class="code" rows="10" placeholder="Claude'un verdiği YAML cevabı buraya yapıştır"></textarea>
      <div class="row" style="margin-top:8px"><button class="primary" id="apply-go">Uygula</button><button class="ghost" id="apply-x">Vazgeç</button></div></div>
    <div id="live-box" class="hidden" style="margin-bottom:12px"><div id="live-status" class="small muted"></div><div class="log" id="live-log" style="height:140px"></div></div>
    ${P.sheet ? "" : ""}
    <div class="shots" id="shots"></div>`;
  let lastPara = -1;
  $("#shots").innerHTML = P.shots.map((s, i) => {
    const sep = s.para !== lastPara ? `<div class="para-sep">Paragraf ${s.para + 1}</div>` : "";
    lastPara = s.para;
    const badges = [s.engine === "gemini" || (s.visual && s.visual.prompt && !s.visual.bg) ? "AI" : "", s.camera ? "kamera: " + s.camera : ""].filter(Boolean);
    return `${sep}<div class="shot ${s.visual ? "" : "unplanned"}" data-i="${i}">
      <div class="img" style="${s.image ? `background-image:url('${s.image}')` : ""}">${s.image ? "" : s.visual ? "görsel üretilmedi" : "plan yok"}</div>
      <div class="meta"><div class="id"><span>${s.id}${s.start != null ? " · " + s.start.toFixed(1) + " sn" : ""}</span><span>${badges.map((b) => `<span class="pill small">${b}</span>`).join(" ")}</span></div>
      <div class="txt">${esc(s.text)}</div></div></div>`;
  }).join("");
  $$(".shot").forEach((d) => (d.onclick = () => shotEditor(cid, slug, +d.dataset.i)));
  const run = async (step, extra = {}) => { const r = await api(`/api/projects/${cid}/${slug}/run`, { method: "POST", body: { step, ...extra } }); watch(r.job, step); state.onJobsDone = () => viewProject(cid, slug, "board"); };
  $("#b-split").onclick = () => run("split");
  $("#b-images").onclick = () => run("images");
  $("#b-sheet").onclick = async () => { await run("sheet"); state.onJobsDone = async () => { await loadProject(cid, slug); if (P.sheet) window.open(P.sheet, "_blank"); }; };
  $("#b-prompt").onclick = async () => copyText(await api(`/api/projects/${cid}/${slug}/prompt/plan`));
  $("#b-apply").onclick = () => $("#apply-box").classList.remove("hidden");
  $("#apply-x").onclick = () => $("#apply-box").classList.add("hidden");
  $("#apply-go").onclick = async () => {
    try { const r = await api(`/api/projects/${cid}/${slug}/apply/plan`, { method: "POST", body: { text: $("#apply-text").value } }); toast(`${r.updated} shot planlandı`); viewProject(cid, slug, "board"); }
    catch (e) { toast(e.message, true); }
  };
}

function closeDrawer() { const d = $("#drawer"); d.classList.add("hidden"); d.innerHTML = ""; }
function shotEditor(cid, slug, idx) {
  const s = P.shots[idx];
  const others = P.languages.slice(1);
  const d = $("#drawer");
  d.classList.remove("hidden");
  d.innerHTML = `
    <div class="spread"><h2 style="margin:0">${s.id} <span class="muted small">paragraf ${s.para + 1}</span></h2>
      <div class="row"><button class="sm" id="se-prev" ${idx ? "" : "disabled"}>← Önceki</button><button class="sm" id="se-next" ${idx < P.shots.length - 1 ? "" : "disabled"}>Sonraki →</button><button class="sm ghost" id="se-x">✕</button></div></div>
    <p style="font-size:16px;margin:12px 0">“${esc(s.text)}”</p>
    <div class="grid g2" style="gap:10px"><div><div class="small muted">Canlı önizleme (kodla çizim)</div><div class="preview" id="se-prev-svg">…</div><div id="se-err" class="err"></div></div>
      <div><div class="small muted">Üretilmiş görsel</div><div class="preview">${s.image ? `<img src="${s.image}">` : "henüz yok"}</div></div></div>
    <label class="f">Sahne tarifi (YAML) — biçim: docs/STORYBOARD.md · katalog: <a href="#/catalog" target="_blank">çizim kataloğu</a></label>
    <textarea id="se-v" class="code" rows="12" spellcheck="false">${esc(s.visual_yaml)}</textarea>
    <div class="row" style="margin-top:8px">
      <label>Motor <select id="se-eng"><option value="">otomatik</option><option value="svg" ${s.engine === "svg" ? "selected" : ""}>svg (ücretsiz)</option><option value="gemini" ${s.engine === "gemini" ? "selected" : ""}>gemini (ücretli)</option></select></label>
      <label>Kamera <select id="se-cam"><option value="">otomatik</option>${["in", "out", "none"].map((c) => `<option ${s.camera === c ? "selected" : ""}>${c}</option>`).join("")}</select></label></div>
    <label class="f">Ekran yazısı (videonun üstüne, dile göre basılır; görsel yazısız kalır)</label>
    <div class="row"><select id="se-ovk"><option value="">yok</option>${["stat", "label", "cite"].map((k) => `<option value="${k}" ${(s.overlay || {}).kind === k ? "selected" : ""}>${{ stat: "büyük sayı", label: "etiket", cite: "kaynak satırı" }[k]}</option>`).join("")}</select>
      <input id="se-ovt" placeholder="+11–16%" style="flex:1" value="${esc((s.overlay || {}).text || "")}">${others.map((l) => `<input class="se-ovi" data-l="${l}" placeholder="${l}" style="width:140px" value="${esc(((s.overlay || {}).i18n || {})[l] || "")}">`).join("")}</div>
    ${others.map((l) => `<label class="f">${LANG_TR[l] || l} metni</label><input class="se-i18n" data-l="${l}" style="width:100%" value="${esc((s.i18n || {})[l] || "")}">`).join("")}
    <div class="row" style="margin-top:14px"><button class="primary" id="se-save">Kaydet</button><button class="accent" id="se-render">Kaydet ve görseli üret</button></div>
    <div class="help small" style="margin-top:16px">İpucu: AI görseli için tarifin yerine <span class="kbd">prompt: "..."</span> yaz ve motoru gemini seç. Görsellere asla yazı/rakam koyma: diller arasında aynı görseller kullanılıyor.</div>`;
  const prev = async () => {
    const v = $("#se-v").value;
    if (!v.trim()) { $("#se-prev-svg").innerHTML = "plan yok"; return; }
    try { $("#se-prev-svg").innerHTML = await api("/api/preview-svg", { method: "POST", body: { visual: v, channel: cid } }); $("#se-err").textContent = ""; }
    catch (e) { $("#se-err").textContent = e.message; }
  };
  let t; $("#se-v").oninput = () => { clearTimeout(t); t = setTimeout(prev, 350); };
  prev();
  $("#se-x").onclick = closeDrawer;
  $("#se-prev").onclick = () => shotEditor(cid, slug, idx - 1);
  $("#se-next").onclick = () => shotEditor(cid, slug, idx + 1);
  const save = async (render) => {
    const i18n = {}; $$(".se-i18n").forEach((i) => (i18n[i.dataset.l] = i.value));
    try {
      const ovi = {}; $$(".se-ovi").forEach((i) => i.value && (ovi[i.dataset.l] = i.value));
      const overlay = $("#se-ovk").value && $("#se-ovt").value ? { kind: $("#se-ovk").value, text: $("#se-ovt").value, ...(Object.keys(ovi).length ? { i18n: ovi } : {}) } : null;
      const r = await api(`/api/projects/${cid}/${slug}/shots/${s.id}`, { method: "PUT", body: { visual_yaml: $("#se-v").value, engine: $("#se-eng").value, camera: $("#se-cam").value, i18n, overlay, render } });
      toast(render ? "Kaydedildi, görsel üretiliyor…" : "Kaydedildi");
      await loadProject(cid, slug);
      if (render) state.onJobsDone = async () => { await loadProject(cid, slug); shotEditor(cid, slug, idx); projBoard(cid, slug, $("#tab")); };
    } catch (e) { toast(e.message, true); }
  };
  $("#se-save").onclick = () => save(false);
  $("#se-render").onclick = () => save(true);
}

function projMake(cid, slug, el) {
  const primary = P.languages[0];
  const row = (lg) => {
    const isPrimary = lg === primary;
    const tr = P.shots.filter((s) => isPrimary || (s.i18n || {})[lg]).length;
    const o = P.outputs[lg];
    return `<div class="lang-block"><div class="spread"><h3 style="margin:0">${LANG_TR[lg] || lg} ${isPrimary ? pill("ana dil") : pill(`çeviri ${tr}/${P.shots.length}`, tr === P.shots.length ? "ok" : "warn")}</h3>
      <span>${o.video ? pill("video hazır", "ok") : pill("video yok")}</span></div>
      <div class="steps" style="margin-top:10px">
        ${isPrimary ? "" : `<button class="sm" data-copy-tr="${lg}">Çeviri istemini kopyala</button><button class="sm" data-apply-tr="${lg}">Çeviriyi uygula</button><span class="arrow">→</span>`}
        <button data-step="voice" data-lang="${lg}">Seslendirme</button><span class="arrow">→</span>
        <button data-step="align" data-lang="${lg}">Zamanlama</button><span class="arrow">→</span>
        <button data-step="render" data-lang="${lg}">Video</button><span class="arrow">·</span>
        <button data-step="shorts" data-lang="${lg}">Shorts</button>
        ${isPrimary ? "" : `<button data-step="dub" data-lang="${lg}" title="Bu dilin sesini ana videonun zamanına oturtur: YouTube'a aynı videoya ek ses parçası olarak yüklenir">Ek ses izi</button>`}
        <button class="primary" data-step="all" data-lang="${lg}" style="margin-left:auto">Tümünü üret</button></div>
      <div class="tr-box hidden" data-trbox="${lg}" style="margin-top:10px"><textarea class="code" rows="8" placeholder="Claude'un verdiği çeviri YAML'ı"></textarea><button class="sm primary" data-trgo="${lg}" style="margin-top:6px">Uygula</button></div></div>`;
  };
  el.innerHTML = `<div class="grid" style="grid-template-columns: minmax(0,2fr) minmax(260px,1fr)">
    <div>${P.languages.map(row).join("")}
      <div class="help small"><b>İkinci dil nasıl yayınlanır?</b> Ayrı video değil: Türkçe satırında "Tümünü üret" sonra "Ek ses izi". Çıkan dosyayı YouTube Studio → videonun <i>Diller</i> bölümü → <i>Ses parçası ekle</i> ile İngilizce videoya yükle; izlenmeler tek videoda toplanır. Türkçe başlık ve kapağı da aynı yerden ekle.</div>
      <div class="help small">"Tümünü üret" sırasıyla: böl → seslendirme → zamanlama → görseller → video → (Proje ayarlarında shorts listesi varsa) Shorts. Değişmeyen ses ve görseller önbellekten gelir, yeniden ücret ödenmez. Shorts kesitleri Proje ayarları'ndaki <span class="kbd">shorts</span> listesinden üretilir.</div>
      <div id="live-box" class="${P.jobs.length ? "" : "hidden"}"><div id="live-status" class="small muted"></div><div class="log" id="live-log"></div></div></div>
    <div><div class="card"><h3>Kalite kapısı</h3>${checklist(P.readiness)}</div></div></div>`;
  $$("[data-step]").forEach((b) => (b.onclick = async () => {
    if (!P.readiness.ready && ["all", "render"].includes(b.dataset.step) && !confirm("Kalite kapısında engeller var (kaynak/senaryo/plan). Yine de üretilsin mi?")) return;
    const r = await api(`/api/projects/${cid}/${slug}/run`, { method: "POST", body: { step: b.dataset.step, lang: b.dataset.lang } });
    watch(r.job, b.textContent + " [" + b.dataset.lang + "]");
    state.onJobsDone = () => viewProject(cid, slug, "make");
  }));
  $$("[data-copy-tr]").forEach((b) => (b.onclick = async () => copyText(await api(`/api/projects/${cid}/${slug}/prompt/translate?lang=${b.dataset.copyTr}`))));
  $$("[data-apply-tr]").forEach((b) => (b.onclick = () => $(`[data-trbox="${b.dataset.applyTr}"]`).classList.toggle("hidden")));
  $$("[data-trgo]").forEach((b) => (b.onclick = async () => {
    const lg = b.dataset.trgo, text = $(`[data-trbox="${lg}"] textarea`).value;
    try { const r = await api(`/api/projects/${cid}/${slug}/apply/translation`, { method: "POST", body: { text, lang: lg } }); toast(`${r.updated} shot çevrildi`); viewProject(cid, slug, "make"); }
    catch (e) { toast(e.message, true); }
  }));
  if (P.jobs.length) watch(P.jobs[0].id, P.jobs[0].label);
}

function projOut(cid, slug, el) {
  el.innerHTML = P.languages.map((lg) => {
    const o = P.outputs[lg];
    return `<div class="card" style="margin-bottom:14px"><div class="spread"><h3 style="margin:0">${LANG_TR[lg] || lg}</h3>
      <div class="row">${o.video ? `<a class="btn sm" href="${o.video}" download>Videoyu indir</a>` : ""}${o.narration ? `<a class="btn sm" href="${o.narration}" download>Sesi indir</a>` : ""}${o.captions ? `<a class="btn sm" href="${o.captions}" download>Altyazı (.srt)</a>` : ""}${o.dub ? `<a class="btn sm" href="${o.dub}" download>Ek ses izi (.wav)</a>` : ""}</div></div>
      ${o.video ? `<div class="grid g2" style="margin-top:12px"><video controls preload="metadata" poster="${(P.shots.find((x) => x.image) || {}).image || ""}" src="${o.video}"></video>
        <div><div class="spread"><span class="small muted">YouTube açıklaması (bölümler + kaynaklar)</span><button class="sm" data-desc="${lg}">Kopyala</button></div>
        <textarea class="code" rows="14" readonly>${esc(o.description)}</textarea></div></div>` : `<p class="muted">Henüz video yok. Üretim sekmesinden üret.</p>`}
      ${o.shorts.length ? `<h3 style="margin-top:14px">Shorts</h3><div class="video-grid">${o.shorts.map((u) => `<div><video controls preload="metadata" src="${u}"></video><a class="small" href="${u}" download>indir</a></div>`).join("")}</div>` : ""}</div>`;
  }).join("");
  $$("[data-desc]").forEach((b) => (b.onclick = () => copyText(P.outputs[b.dataset.desc].description)));
}

function projMeta(cid, slug, el) {
  el.innerHTML = `<div class="grid g2"><div class="card"><h3>project.yaml</h3><textarea id="my" class="code" rows="20">${esc(P.meta_yaml)}</textarea>
    <div class="row" style="margin-top:10px"><button class="primary" id="my-save">Kaydet</button></div></div>
    <div class="card"><h3>Alanlar</h3><pre class="code small" style="white-space:pre-wrap">title: "Video başlığı"
description: "Açıklamanın ilk paragrafı"
status: scripting | production | published
chapters:            # paragraf numarası → bölüm adı
  0: Intro
  1: "The bone scans"
shorts:              # dikey kesitler (shot aralığı)
  - {title: "Kanca metni", from: s007, to: s019}
thumbnails: [...]    # Kapak & başlık sekmesinde düzenlenir
publish: {...}       # Yayın & performans sekmesinde düzenlenir</pre></div></div>`;
  $("#my-save").onclick = async () => { try { await api(`/api/projects/${cid}/${slug}/meta`, { method: "PUT", body: { yaml: $("#my").value } }); toast("Kaydedildi"); } catch (e) { toast(e.message, true); } };
}

/* ------------------------------------------------------------ settings / catalog / jobs */
async function viewSettings() {
  const s = await api("/api/settings");
  const keyRow = (k, label, what) => `<div class="spread" style="padding:8px 0;border-bottom:1px solid #f0e9da"><div><b>${label}</b> ${s.secrets[k] ? pill("kayıtlı", "ok") : pill("yok")}<div class="small muted">${what}</div></div>
    <div class="row"><input type="password" data-key="${k}" placeholder="yapıştır" style="width:240px"><button class="sm" data-save-key="${k}">Kaydet</button>${s.secrets[k] ? `<button class="sm ghost" data-del-key="${k}">Sil</button>` : ""}</div></div>`;
  app.innerHTML = `<h1>Ayarlar</h1><p class="sub">Tüm kanallar için varsayılan ayarlar. Kanala özel farklar kanalın ayarlarında (<span class="kbd">overrides</span>).</p>
    <div class="grid g3">
      <div class="card"><h3>Seslendirme</h3><p class="small muted">Şu an: <b>${esc(s.providers.tts)}</b> · dile özel: ${esc(JSON.stringify(s.providers.tts_by_lang))}</p><p class="small">kokoro = ücretsiz, yerel (İngilizce) · edge = ücretsiz, çevrimiçi (Türkçe dahil) · elevenlabs = ücretli, en doğal</p></div>
      <div class="card"><h3>Görseller</h3><p class="small muted">Şu an: <b>${esc(s.providers.images)}</b> · Gemini modeli: ${esc(s.providers.gemini_model)}</p><p class="small">svg = kodla çizim, ücretsiz · gemini = Nano Banana, görsel başına ücret (shot bazında da seçilebilir)</p></div>
      <div class="card"><h3>Planlama & çeviri</h3><p class="small muted">Şu an: <b>${esc(s.providers.planner)}</b></p><p class="small">manual = istemi Claude sohbetine yapıştır (ücretsiz) · anthropic = otomatik (API ücreti)</p></div></div>
    <div class="card" style="margin-top:14px"><h3>API anahtarları</h3><p class="small muted" style="margin-top:0">Sadece bu bilgisayardaki <span class="kbd">.env</span> dosyasına yazılır, GitHub'a gitmez. Sadece ücretli servisler için gerekir.</p>
      ${keyRow("GEMINI_API_KEY", "Google Gemini", "AI görseller (Nano Banana)")}${keyRow("ELEVENLABS_API_KEY", "ElevenLabs", "Ücretli, çok dilli ses")}${keyRow("ANTHROPIC_API_KEY", "Anthropic", "Otomatik storyboard planlama ve çeviri")}${keyRow("YOUTUBE_API_KEY", "YouTube Data API", "Fikir havuzu talep/rekabet sinyalleri (ücretsiz, Google Cloud Console → YouTube Data API v3)")}</div>
    <div class="card" style="margin-top:14px"><div class="spread"><h3>config.yaml</h3><button class="primary sm" id="cfg-save">Kaydet</button></div><textarea id="cfg" class="code" rows="28">${esc(s.config_yaml)}</textarea></div>`;
  $$("[data-save-key]").forEach((b) => (b.onclick = async () => { const k = b.dataset.saveKey; await api("/api/secrets", { method: "PUT", body: { name: k, value: $(`[data-key="${k}"]`).value } }); toast("Anahtar kaydedildi"); viewSettings(); refreshSidebar(); }));
  $$("[data-del-key]").forEach((b) => (b.onclick = async () => { if (!confirm("Anahtar silinsin mi?")) return; await api("/api/secrets", { method: "PUT", body: { name: b.dataset.delKey, value: "" } }); viewSettings(); }));
  $("#cfg-save").onclick = async () => { try { await api("/api/settings", { method: "PUT", body: { config_yaml: $("#cfg").value } }); toast("Kaydedildi"); refreshSidebar(); } catch (e) { toast(e.message, true); } };
}

async function viewCatalog() {
  const c = await api("/api/catalog");
  app.innerHTML = `<div class="spread"><h1>Çizim kataloğu</h1><button id="cat-re">Kataloğu yeniden çiz</button></div>
    <p class="sub">Kodla çizim motorunun bildiği her şey. Sahne tariflerinde bu adları kullan.</p>
    <div class="card"><h3>Arka planlar (bg)</h3><p class="code small">${c.backgrounds.join(" · ")}</p>${c.images.backgrounds ? `<img src="${c.images.backgrounds}" style="width:100%;border-radius:8px">` : ""}</div>
    <div class="card" style="margin-top:14px"><h3>Pozlar (figures.pose)</h3><p class="code small">${c.poses.join(" · ")}</p>${c.images.poses ? `<img src="${c.images.poses}" style="width:100%;border-radius:8px">` : ""}</div>
    <div class="card" style="margin-top:14px"><h3>Nesneler (props.type)</h3><p class="code small">${c.props.join(" · ")}</p>${c.images.props ? `<img src="${c.images.props}" style="width:100%;border-radius:8px">` : ""}</div>`;
  $("#cat-re").onclick = async () => { await api("/api/tools/catalog", { method: "POST", body: {} }); toast("Katalog çiziliyor…"); state.onJobsDone = viewCatalog; };
}

async function viewJobs() {
  const jobs = await api("/api/jobs");
  app.innerHTML = `<h1>İşler</h1><p class="sub">Arka planda çalışan üretim adımları. İşler sırayla çalışır.</p>
    <div class="grid" style="grid-template-columns:minmax(260px,1fr) minmax(0,2fr)">
      <div class="card" style="padding:6px">${jobs.length ? jobs.map((j) => `<div class="job-row" data-j="${j.id}"><span><span class="status-dot s-${j.status}"></span>#${j.id} ${esc(j.label)}<div class="small muted">${esc(j.channel || "")} ${esc(j.project || "")}</div></span><span class="small muted">${ago(j.created)}</span></div>`).join("") : '<p class="muted" style="padding:10px">Henüz iş yok.</p>'}</div>
      <div><div class="spread"><div id="live-status" class="small muted">Bir iş seç</div><button class="sm" id="job-cancel">Durdur</button></div><div id="live-box"><div class="log" id="live-log" style="height:520px"></div></div></div></div>`;
  $$("[data-j]").forEach((r) => (r.onclick = () => showJob(+r.dataset.j)));
  $("#job-cancel").onclick = async () => { if (state.watchJob) { await api(`/api/jobs/${state.watchJob.id}/cancel`, { method: "POST" }); toast("Durduruldu"); } };
  if (jobs.length) showJob(jobs[0].id);
}
function showJob(id) { watch(id, "iş"); pumpLog(); }

/* ------------------------------------------------------------ boot */
(async () => {
  await refreshSidebar();
  startPolling();
  route();
})();
