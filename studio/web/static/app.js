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
    <div class="row"><span>Resim</span><span>gemini ${pill("ücretli", "warn")}</span></div>
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
      <a href="#/c/${cid}/settings" class="${tab === "settings" ? "active" : ""}">Kanal ayarları</a>
    </div><div id="tab"></div>`;
  const el = $("#tab");
  if (tab === "ideas") return channelIdeas(cid, el);
  if (tab === "projects") return channelProjects(cid, el);
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
      <div class="row" style="margin-top:8px">${p.ready ? pill("hazır", "ok") : pill("eksik", "bad")} ${pill((p.scenes || 0) + " sahne")} ${Object.entries(p.videos).map(([l, u]) => pill(l + (u ? " ✓" : " —"), u ? "ok" : "")).join(" ")}</div>
      ${p.blocks.length ? `<div class="small muted" style="margin-top:6px">${esc(p.blocks[0])}</div>` : ""}</a>`).join("") : '<p class="muted">Henüz proje yok. Fikir havuzundan bir fikri projeye dönüştür.</p>';
}

async function channelSettings(cid, el, ch) {
  el.innerHTML = `<div class="grid g2"><div class="card"><h3>channel.yaml</h3>
    <p class="small muted">Kimlik, diller, görsel stil (<span class="kbd">visual_style</span>), tekrar eden karakterler (<span class="kbd">characters</span>) ve bu kanala özel ayarlar (<span class="kbd">overrides</span> altında config.yaml'ın her anahtarı ezilebilir).</p>
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
      <a href="#/p/${cid}/${slug}/board" class="${tab === "board" ? "active" : ""}">2 · Sahneler <span class="n">${P.shots.length ? sceneGroups().length : 0}</span></a>
      <a href="#/p/${cid}/${slug}/video" class="${["video", "make", "out"].includes(tab) ? "active" : ""}">3 · Video</a>
      <a href="#/p/${cid}/${slug}/pack" class="${tab === "pack" ? "active" : ""}">4 · Kapak & başlık</a>
      <a href="#/p/${cid}/${slug}/pub" class="${tab === "pub" ? "active" : ""}">5 · Yayın</a>
      <a href="#/p/${cid}/${slug}/meta" class="${tab === "meta" ? "active" : ""}">Proje ayarları</a>
    </div><div id="tab"></div>`;
  const el = $("#tab");
  state.onJobsDone = null;
  if (tab === "script") return projScript(cid, slug, el);
  if (tab === "board") return projScenes(cid, slug, el);
  if (["video", "make", "out"].includes(tab)) return projVideo(cid, slug, el);
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

/* scenes: consecutive shots that share one picture (visual {same: true} continues the previous one) */
function sceneGroups() {
  const groups = [];
  P.shots.forEach((s, i) => {
    if (groups.length && s.scene !== s.id && s.scene === groups[groups.length - 1].id) groups[groups.length - 1].shots.push({ ...s, i });
    else groups.push({ id: s.id, head: s, shots: [{ ...s, i }] });
  });
  return groups;
}
const sceneWords = (g) => g.shots.map((s) => s.text).join(" ");
const sceneSecs = (g) => {
  const a = g.shots[0].start, nx = P.shots[g.shots[g.shots.length - 1].i + 1];
  return a != null && nx && nx.start != null ? nx.start - a : null;
};

function projScenes(cid, slug, el) {
  const groups = sceneGroups();
  const unplanned = groups.filter((g) => g.head.kind === "none").length;
  const ai = groups.filter((g) => g.head.kind === "ai");
  const missing = ai.filter((g) => !g.head.image).length;
  const manual = (state.overview && state.overview.providers.planner) === "manual";
  const step = !P.shots.length ? 0 : unplanned ? 1 : missing ? 2 : 3;
  el.innerHTML = `
    <div class="flow">
      <div class="flow-step ${step === 1 ? "now" : step > 1 ? "done" : ""}"><b>1</b><div><div class="t">Sahneleri planla</div><div class="small muted">${P.shots.length ? `${groups.length} sahne · ${unplanned ? unplanned + " plansız" : "hepsi planlı"}` : "önce senaryoyu böl"}</div></div>
        <button id="b-plan" class="${step === 1 ? "primary" : ""}" ${P.shots.length ? "" : "disabled"}>${manual ? "Plan istemini kopyala" : unplanned ? "Planla" : "Plansızları planla"}</button></div>
      <div class="flow-step ${step === 2 ? "now" : step > 2 ? "done" : ""}"><b>2</b><div><div class="t">Resimleri çiz</div><div class="small muted">${ai.length} AI resmi · ${missing ? `${missing} çizilmedi (~${(missing * 0.05).toFixed(2)} $)` : "hepsi hazır"}</div></div>
        <button id="b-images" class="${step === 2 ? "primary" : ""}" ${unplanned === groups.length ? "disabled" : ""}>Resimleri çiz</button></div>
      <div class="flow-step ${step === 3 ? "now" : ""}"><b>3</b><div><div class="t">Kontrol et</div><div class="small muted">Beğenmediğin sahneye tıkla, istemi düzelt, yeniden çiz</div></div>
        <a class="btn ${step === 3 ? "primary" : ""}" href="#/p/${cid}/${slug}/video">Videoya geç →</a></div>
    </div>
    ${manual ? `<div id="apply-box" class="card" style="margin-bottom:12px"><div class="small muted">Elle planlama: kopyaladığın istemi claude.ai'ye yapıştır, gelen YAML'ı buraya yapıştır. (Ayarlar'da <span class="kbd">planner.provider: gemini</span> yaparsan tek tıkla planlanır.)</div>
      <textarea id="apply-text" class="code" rows="5" placeholder="YAML cevabı"></textarea><div class="row" style="margin-top:6px"><button class="primary sm" id="apply-go">Planı uygula</button></div></div>` : ""}
    <div id="live-box" class="hidden" style="margin-bottom:12px"><div id="live-status" class="small muted"></div><div class="log" id="live-log" style="height:140px"></div></div>
    <div class="spread" style="margin:6px 0 10px"><span class="small muted">${P.shots.length} cümle parçası → ${groups.length} sahne. Bir resim ekranda 5–9 sn kalır, kamera üzerinde yavaşça hareket eder.</span>
      <span class="row"><button class="sm ghost" id="b-split">Senaryoyu yeniden böl</button>${P.sheet ? `<a class="btn sm ghost" href="${P.sheet}" target="_blank">Kontak sayfası</a>` : ""}<button class="sm ghost" id="b-sheet">Kontak sayfasını yenile</button></span></div>
    <div class="scenes" id="scenes"></div>`;
  let lastPara = -1;
  $("#scenes").innerHTML = groups.map((g, k) => {
    const h = g.head, sec = sceneSecs(g);
    const sep = h.para !== lastPara ? `<div class="para-sep">Paragraf ${h.para + 1}</div>` : "";
    lastPara = h.para;
    const v = h.visual || {};
    const badges = [h.kind === "chart" ? "grafik" : "", (v.characters || []).includes("coach") ? "koç" : "", v.ref ? "devam" : "", h.camera ? "kamera: " + h.camera : "",
      g.shots.some((s) => s.overlay) ? "ekran yazısı" : ""].filter(Boolean);
    return `${sep}<div class="scene ${h.kind === "none" ? "unplanned" : ""}" data-k="${k}">
      <div class="img" style="${h.image ? `background-image:url('${h.image}?v=${Date.now() % 1e7}')` : ""}">${h.image ? "" : h.kind === "none" ? "plan yok" : "çizilmedi"}</div>
      <div class="meta"><div class="id"><span>${g.id}${g.shots.length > 1 ? "–" + g.shots[g.shots.length - 1].id.slice(1) : ""}${sec ? " · " + sec.toFixed(1) + " sn" : ""}</span><span>${badges.map((b) => `<span class="pill small">${b}</span>`).join(" ")}</span></div>
      <div class="txt">${esc(sceneWords(g))}</div></div></div>`;
  }).join("");
  $$(".scene").forEach((d) => (d.onclick = () => sceneEditor(cid, slug, +d.dataset.k)));
  const run = async (stepName, extra = {}) => { const r = await api(`/api/projects/${cid}/${slug}/run`, { method: "POST", body: { step: stepName, ...extra } }); watch(r.job, stepName); state.onJobsDone = () => viewProject(cid, slug, "board"); };
  $("#b-split").onclick = () => confirm("Senaryo yeniden bölünsün mü? Metni değişmeyen cümlelerin planı korunur.") && run("split");
  $("#b-images").onclick = () => run("images");
  $("#b-sheet").onclick = async () => { await run("sheet"); state.onJobsDone = async () => { await loadProject(cid, slug); if (P.sheet) window.open(P.sheet, "_blank"); viewProject(cid, slug, "board"); }; };
  $("#b-plan").onclick = async () => (manual ? copyText(await api(`/api/projects/${cid}/${slug}/prompt/plan`)) : run("plan"));
  if (manual) $("#apply-go").onclick = async () => {
    try { const r = await api(`/api/projects/${cid}/${slug}/apply/plan`, { method: "POST", body: { text: $("#apply-text").value } }); toast(`${r.updated} shot planlandı`); viewProject(cid, slug, "board"); }
    catch (e) { toast(e.message, true); }
  };
  if (P.jobs.length) watch(P.jobs[0].id, P.jobs[0].label);
}

function closeDrawer() { const d = $("#drawer"); d.classList.add("hidden"); d.innerHTML = ""; }
function sceneEditor(cid, slug, k) {
  const groups = sceneGroups();
  const g = groups[k], h = g.head, v = h.visual || {};
  const isChart = h.kind === "chart";
  const prevHead = k > 0 ? groups[k - 1].head : null;
  const others = P.languages.slice(1);
  const d = $("#drawer");
  d.classList.remove("hidden");
  d.innerHTML = `
    <div class="spread"><h2 style="margin:0">Sahne ${k + 1} <span class="muted small">${g.id} · ${g.shots.length} parça · paragraf ${h.para + 1}</span></h2>
      <div class="row"><button class="sm" id="se-prev" ${k ? "" : "disabled"}>←</button><button class="sm" id="se-next" ${k < groups.length - 1 ? "" : "disabled"}>→</button><button class="sm ghost" id="se-x">✕</button></div></div>
    <div class="preview" style="margin-top:12px" id="se-img">${h.image ? `<img src="${h.image}?v=${Date.now() % 1e7}">` : isChart ? "" : "henüz çizilmedi"}</div>
    <p style="font-size:16px;margin:12px 0">“${esc(sceneWords(g))}”</p>
    <div class="row" style="gap:6px;margin-bottom:6px"><button class="sm ${isChart ? "" : "on"}" id="se-mode-ai">Resim</button><button class="sm ${isChart ? "on" : ""}" id="se-mode-chart">Grafik</button></div>
    <div id="se-ai" class="${isChart ? "hidden" : ""}">
      <label class="f">Ne görünsün? (sahneyi İngilizce anlat: kim, ne yapıyor, nerede, ışık, çekim mesafesi — yazı/rakam isteme)</label>
      <textarea id="se-p" rows="5" spellcheck="false">${esc(v.prompt || "")}</textarea>
      <div class="row" style="margin-top:8px;gap:16px">
        <label class="check"><input type="checkbox" id="se-coach" ${(v.characters || []).includes("coach") ? "checked" : ""}> Koç bu sahnede</label>
        ${prevHead && prevHead.kind === "ai" ? `<label class="check"><input type="checkbox" id="se-ref" ${v.ref ? "checked" : ""}> Önceki sahnenin devamı (aynı yer, aynı kişiler)</label>` : ""}
        <label>Kamera <select id="se-cam"><option value="">otomatik</option>${[["in", "yakınlaş"], ["out", "uzaklaş"], ["left", "sola kay"], ["right", "sağa kay"], ["none", "sabit"]].map(([c, t]) => `<option value="${c}" ${h.camera === c ? "selected" : ""}>${t}</option>`).join("")}</select></label></div></div>
    <div id="se-chart" class="${isChart ? "" : "hidden"}">
      <label class="f">Grafik tarifi (YAML) — sayıları resim olarak gösterir; biçim: docs/STORYBOARD.md → Charts</label>
      <textarea id="se-c" class="code" rows="6" spellcheck="false">${esc(isChart ? h.visual_yaml : "bg: plain_warm\nprops:\n  - {type: bar_chart, x: 960, y: 860, values: [1.0, 0.4], colors: [ochre, water]}")}</textarea><div id="se-err" class="err"></div></div>
    <div class="row" style="margin-top:12px"><button class="accent" id="se-render">Kaydet ve yeniden çiz</button><button id="se-save">Sadece kaydet</button>
      ${k > 0 ? `<button class="ghost" id="se-merge" title="Bu sahnenin resmi silinir, önceki resim devam eder">Öncekiyle birleştir</button>` : ""}</div>
    <h3 style="margin-top:22px">Bu sahnedeki cümle parçaları</h3>
    <p class="small muted" style="margin-top:0">Ekran yazısı videonun üstüne dile göre basılır; resim yazısız kalır. "Buradan böl" bu parçadan itibaren yeni bir resim başlatır.</p>
    ${g.shots.map((s, j) => `<div class="shot-line" data-sid="${s.id}">
      <div class="spread"><span class="small muted">${s.id}${s.start != null ? " · " + s.start.toFixed(1) + " sn" : ""}</span>${j ? `<button class="sm ghost" data-split="${s.id}">Buradan böl</button>` : ""}</div>
      <div>${esc(s.text)}</div>
      <div class="row" style="margin-top:6px"><select class="ov-k"><option value="">ekran yazısı yok</option>${["stat", "label", "cite"].map((x) => `<option value="${x}" ${(s.overlay || {}).kind === x ? "selected" : ""}>${{ stat: "büyük sayı", label: "etiket", cite: "kaynak satırı" }[x]}</option>`).join("")}</select>
        <input class="ov-t" placeholder="+11–16%" style="flex:1" value="${esc((s.overlay || {}).text || "")}">${others.map((l) => `<input class="ov-i" data-l="${l}" placeholder="${l}" style="width:120px" value="${esc(((s.overlay || {}).i18n || {})[l] || "")}">`).join("")}</div>
      ${others.map((l) => `<input class="tr-i" data-l="${l}" style="width:100%;margin-top:6px" placeholder="${LANG_TR[l] || l} metni" value="${esc((s.i18n || {})[l] || "")}">`).join("")}
    </div>`).join("")}
    <div class="row" style="margin-top:10px"><button class="primary sm" id="se-lines">Parçaları kaydet</button></div>`;
  let mode = isChart ? "chart" : "ai";
  const setMode = (m) => { mode = m; $("#se-ai").classList.toggle("hidden", m !== "ai"); $("#se-chart").classList.toggle("hidden", m !== "chart"); $("#se-mode-ai").classList.toggle("on", m === "ai"); $("#se-mode-chart").classList.toggle("on", m === "chart"); if (m === "chart") prev(); };
  const prev = async () => {
    try { $("#se-img").innerHTML = await api("/api/preview-svg", { method: "POST", body: { visual: $("#se-c").value, channel: cid } }); $("#se-err").textContent = ""; }
    catch (e) { $("#se-err").textContent = e.message; }
  };
  let t; $("#se-c").oninput = () => { clearTimeout(t); t = setTimeout(prev, 350); };
  if (isChart) prev();
  $("#se-mode-ai").onclick = () => setMode("ai");
  $("#se-mode-chart").onclick = () => setMode("chart");
  $("#se-x").onclick = closeDrawer;
  $("#se-prev").onclick = () => sceneEditor(cid, slug, k - 1);
  $("#se-next").onclick = () => sceneEditor(cid, slug, k + 1);
  const reopen = async () => { await loadProject(cid, slug); projScenes(cid, slug, $("#tab")); sceneEditor(cid, slug, Math.min(k, sceneGroups().length - 1)); };
  const save = async (render) => {
    const body = mode === "chart" ? { chart_yaml: $("#se-c").value, render }
      : { prompt: $("#se-p").value, characters: $("#se-coach").checked ? ["coach"] : [], ref: $("#se-ref") && $("#se-ref").checked ? prevHead.id : null, camera: $("#se-cam").value, render };
    try {
      await api(`/api/projects/${cid}/${slug}/scenes/${g.id}`, { method: "PUT", body });
      toast(render ? "Kaydedildi, resim çiziliyor…" : "Kaydedildi");
      if (render) state.onJobsDone = reopen; else reopen();
    } catch (e) { toast(e.message, true); }
  };
  $("#se-save").onclick = () => save(false);
  $("#se-render").onclick = () => save(true);
  if ($("#se-merge")) $("#se-merge").onclick = async () => { await api(`/api/projects/${cid}/${slug}/scenes/${g.id}/merge`, { method: "POST" }); toast("Önceki sahneyle birleştirildi"); await loadProject(cid, slug); projScenes(cid, slug, $("#tab")); sceneEditor(cid, slug, k - 1); };
  $$("[data-split]").forEach((b) => (b.onclick = async () => { await api(`/api/projects/${cid}/${slug}/scenes/${b.dataset.split}/split`, { method: "POST" }); toast("Yeni sahne açıldı: istemini düzenle ve çiz"); await loadProject(cid, slug); projScenes(cid, slug, $("#tab")); sceneEditor(cid, slug, k + 1); }));
  $("#se-lines").onclick = async () => {
    try {
      for (const line of $$(".shot-line")) {
        const ovi = {}; $$(".ov-i", line).forEach((i) => i.value && (ovi[i.dataset.l] = i.value));
        const kind = $(".ov-k", line).value, text = $(".ov-t", line).value;
        const overlay = kind && text ? { kind, text, ...(Object.keys(ovi).length ? { i18n: ovi } : {}) } : null;
        const i18n = {}; $$(".tr-i", line).forEach((i) => (i18n[i.dataset.l] = i.value));
        await api(`/api/projects/${cid}/${slug}/shots/${line.dataset.sid}`, { method: "PUT", body: { overlay, i18n } });
      }
      toast("Kaydedildi"); await loadProject(cid, slug);
    } catch (e) { toast(e.message, true); }
  };
}

function projVideo(cid, slug, el) {
  const primary = P.languages[0];
  const block = (lg) => {
    const isPrimary = lg === primary;
    const tr = P.shots.filter((s) => isPrimary || (s.i18n || {})[lg]).length;
    const o = P.outputs[lg];
    const poster = (P.shots.find((x) => x.image) || {}).image || "";
    return `<div class="card" style="margin-bottom:14px"><div class="spread"><h3 style="margin:0">${LANG_TR[lg] || lg} ${isPrimary ? pill("ana dil") : pill(`çeviri ${tr}/${P.shots.length}`, tr === P.shots.length ? "ok" : "warn")}</h3>
        <div class="row">${isPrimary ? "" : `<button data-step="translate" data-lang="${lg}">Çevir</button><button data-step="dub" data-lang="${lg}" title="Bu dilin sesi, ana videonun zamanına oturtulur: YouTube'da aynı videoya ek ses parçası olarak yüklenir">Ek ses izi</button>`}
          <button class="primary" data-step="all" data-lang="${lg}">${o.video ? "Videoyu yeniden üret" : "Videoyu üret"}</button></div></div>
      <details class="small" style="margin-top:8px"><summary class="muted">Adım adım (ileri düzey)</summary><div class="steps" style="margin-top:8px">
        <button class="sm" data-step="voice" data-lang="${lg}">Seslendirme</button><span class="arrow">→</span><button class="sm" data-step="align" data-lang="${lg}">Zamanlama</button><span class="arrow">→</span>
        <button class="sm" data-step="render" data-lang="${lg}">Kurgu</button><span class="arrow">·</span><button class="sm" data-step="shorts" data-lang="${lg}">Shorts</button>
        ${isPrimary || !(state.overview && state.overview.providers.planner === "manual") ? "" : `<button class="sm" data-copy-tr="${lg}">Çeviri istemini kopyala</button><button class="sm" data-apply-tr="${lg}">Çeviriyi uygula</button>`}</div>
        <div class="tr-box hidden" data-trbox="${lg}" style="margin-top:10px"><textarea class="code" rows="6" placeholder="Çeviri YAML'ı"></textarea><button class="sm primary" data-trgo="${lg}" style="margin-top:6px">Uygula</button></div></details>
      ${o.video ? `<div class="grid g2" style="margin-top:12px"><div><video controls preload="metadata" poster="${poster}" src="${o.video}"></video>
          <div class="row" style="margin-top:8px"><a class="btn sm" href="${o.video}" download>Videoyu indir</a>${o.captions ? `<a class="btn sm" href="${o.captions}" download>Altyazı (.srt)</a>` : ""}${o.dub ? `<a class="btn sm" href="${o.dub}" download>Ek ses izi (.wav)</a>` : ""}</div></div>
        <div><div class="spread"><span class="small muted">YouTube açıklaması (bölümler + kaynaklar)</span><button class="sm" data-desc="${lg}">Kopyala</button></div>
        <textarea class="code" rows="12" readonly>${esc(o.description)}</textarea></div></div>` : `<p class="muted small" style="margin-bottom:0">Henüz video yok. "Videoyu üret" sırasıyla: seslendirme → zamanlama → eksik resimler → kurgu${isPrimary ? " → (Proje ayarlarında shorts listesi varsa) Shorts" : ""}. Değişmeyen ses ve resimler önbellekten gelir, tekrar ücret ödenmez.</p>`}
      ${o.shorts.length ? `<h3 style="margin-top:14px">Shorts</h3><div class="video-grid">${o.shorts.map((u) => `<div><video controls preload="metadata" src="${u}"></video><a class="small" href="${u}" download>indir</a></div>`).join("")}</div>` : ""}</div>`;
  };
  el.innerHTML = `<div class="grid" style="grid-template-columns: minmax(0,2fr) minmax(260px,1fr)">
    <div>${P.languages.map(block).join("")}
      ${P.languages.length > 1 ? `<div class="help small"><b>İkinci dil nasıl yayınlanır?</b> Ayrı video değil: "Çevir" → "Videoyu üret" → "Ek ses izi". Çıkan .wav dosyasını YouTube Studio → videonun <i>Diller</i> bölümü → <i>Ses parçası ekle</i> ile ana videoya yükle.</div>` : ""}
      <div id="live-box" class="${P.jobs.length ? "" : "hidden"}"><div id="live-status" class="small muted"></div><div class="log" id="live-log"></div></div></div>
    <div><div class="card"><h3>Kalite kapısı</h3>${checklist(P.readiness)}</div></div></div>`;
  $$("[data-step]").forEach((b) => (b.onclick = async () => {
    if (!P.readiness.ready && ["all", "render"].includes(b.dataset.step) && !confirm("Kalite kapısında engeller var (kaynak/senaryo/plan). Yine de üretilsin mi?")) return;
    const r = await api(`/api/projects/${cid}/${slug}/run`, { method: "POST", body: { step: b.dataset.step, lang: b.dataset.lang } });
    watch(r.job, b.textContent + " [" + b.dataset.lang + "]");
    state.onJobsDone = () => viewProject(cid, slug, "video");
  }));
  $$("[data-copy-tr]").forEach((b) => (b.onclick = async () => copyText(await api(`/api/projects/${cid}/${slug}/prompt/translate?lang=${b.dataset.copyTr}`))));
  $$("[data-apply-tr]").forEach((b) => (b.onclick = () => $(`[data-trbox="${b.dataset.applyTr}"]`).classList.toggle("hidden")));
  $$("[data-trgo]").forEach((b) => (b.onclick = async () => {
    const lg = b.dataset.trgo, text = $(`[data-trbox="${lg}"] textarea`).value;
    try { const r = await api(`/api/projects/${cid}/${slug}/apply/translation`, { method: "POST", body: { text, lang: lg } }); toast(`${r.updated} shot çevrildi`); viewProject(cid, slug, "video"); }
    catch (e) { toast(e.message, true); }
  }));
  $$("[data-desc]").forEach((b) => (b.onclick = () => copyText(P.outputs[b.dataset.desc].description)));
  if (P.jobs.length) watch(P.jobs[0].id, P.jobs[0].label);
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
shorts:              # dikey kesitler (cümle parçası aralığı)
  - {title: "Kanca metni", from: s007, to: s019}
thumbnails: [...]    # Kapak & başlık sekmesinde düzenlenir
publish: {...}       # Yayın & performans sekmesinde düzenlenir</pre></div></div>`;
  $("#my-save").onclick = async () => { try { await api(`/api/projects/${cid}/${slug}/meta`, { method: "PUT", body: { yaml: $("#my").value } }); toast("Kaydedildi"); } catch (e) { toast(e.message, true); } };
}

/* ------------------------------------------------------------ settings / jobs */
async function viewSettings() {
  const s = await api("/api/settings");
  const keyRow = (k, label, what) => `<div class="spread" style="padding:8px 0;border-bottom:1px solid #f0e9da"><div><b>${label}</b> ${s.secrets[k] ? pill("kayıtlı", "ok") : pill("yok")}<div class="small muted">${what}</div></div>
    <div class="row"><input type="password" data-key="${k}" placeholder="yapıştır" style="width:240px"><button class="sm" data-save-key="${k}">Kaydet</button>${s.secrets[k] ? `<button class="sm ghost" data-del-key="${k}">Sil</button>` : ""}</div></div>`;
  app.innerHTML = `<h1>Ayarlar</h1><p class="sub">Tüm kanallar için varsayılan ayarlar. Kanala özel farklar kanalın ayarlarında (<span class="kbd">overrides</span>).</p>
    <div class="grid g3">
      <div class="card"><h3>Seslendirme</h3><p class="small muted">Şu an: <b>${esc(s.providers.tts)}</b> · dile özel: ${esc(JSON.stringify(s.providers.tts_by_lang))}</p><p class="small">kokoro = ücretsiz, yerel (İngilizce) · edge = ücretsiz, çevrimiçi (Türkçe dahil) · elevenlabs = ücretli, en doğal</p></div>
      <div class="card"><h3>Resimler</h3><p class="small muted">Model: <b>${esc(s.providers.gemini_model)}</b></p><p class="small">Her sahne bir AI resmi (~0,05 $). Stil ve koç karakteri kanal ayarlarında. Grafikler kodla çizilir (ücretsiz). Değişmeyen sahne tekrar ödenmez.</p></div>
      <div class="card"><h3>Planlama & çeviri</h3><p class="small muted">Şu an: <b>${esc(s.providers.planner)}</b></p><p class="small">gemini = tek tık, görsellerle aynı anahtar (önerilen) · anthropic = otomatik (API ücreti) · manual = istemi Claude sohbetine yapıştır</p></div></div>
    <div class="card" style="margin-top:14px"><h3>API anahtarları</h3><p class="small muted" style="margin-top:0">Sadece bu bilgisayardaki <span class="kbd">.env</span> dosyasına yazılır, GitHub'a gitmez. Sadece ücretli servisler için gerekir.</p>
      ${keyRow("GEMINI_API_KEY", "Google Gemini", "Resimler, sahne planı, çeviri (ve istersen ses)")}${keyRow("ELEVENLABS_API_KEY", "ElevenLabs", "Ücretli, çok dilli ses")}${keyRow("ANTHROPIC_API_KEY", "Anthropic", "Otomatik storyboard planlama ve çeviri")}${keyRow("YOUTUBE_API_KEY", "YouTube Data API", "Fikir havuzu talep/rekabet sinyalleri (ücretsiz, Google Cloud Console → YouTube Data API v3)")}</div>
    <div class="card" style="margin-top:14px"><div class="spread"><h3>config.yaml</h3><button class="primary sm" id="cfg-save">Kaydet</button></div><textarea id="cfg" class="code" rows="28">${esc(s.config_yaml)}</textarea></div>`;
  $$("[data-save-key]").forEach((b) => (b.onclick = async () => { const k = b.dataset.saveKey; await api("/api/secrets", { method: "PUT", body: { name: k, value: $(`[data-key="${k}"]`).value } }); toast("Anahtar kaydedildi"); viewSettings(); refreshSidebar(); }));
  $$("[data-del-key]").forEach((b) => (b.onclick = async () => { if (!confirm("Anahtar silinsin mi?")) return; await api("/api/secrets", { method: "PUT", body: { name: b.dataset.delKey, value: "" } }); viewSettings(); }));
  $("#cfg-save").onclick = async () => { try { await api("/api/settings", { method: "PUT", body: { config_yaml: $("#cfg").value } }); toast("Kaydedildi"); refreshSidebar(); } catch (e) { toast(e.message, true); } };
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
