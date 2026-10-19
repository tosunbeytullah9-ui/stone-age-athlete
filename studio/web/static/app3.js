/* Video Fabrikası — panel part 3: preparation studio (research → script → claims → packaging → Shorts → slot in one
   package, docs/PREP.md), the owner's review before upload, and a short explanation under every button. */
"use strict";

/* ------------------------------------------------------------ who does what (shown on the preparation page) */
const ROLES = [
  ["Claude", "Araştırma, kaynak bulma, senaryo, iddialar, başlık ve kapak fikirleri, Shorts kesitleri, takvim, politika öz denetimi", "ücretsiz (claude.ai aboneliği)"],
  ["Gemini", "Sahne resimleri ve kapak resimleri; istersen sahne planı", "~0,05 $ / resim · plan ~0,01 $"],
  ["Ses (TTS)", "Senaryoyu kanalın sesiyle okur", "kanala göre: Gemini ucuz, Kokoro/Edge ücretsiz"],
  ["Remotion", "Dosya kartı, hüküm damgası, rakam sahneleri", "ücretsiz, bu bilgisayarda"],
  ["FFmpeg", "Kurgu, müzik, ses tasarımı, altyazı, Shorts", "ücretsiz, bu bilgisayarda"],
  ["Sen", "Paketi okursun, iddiaları ve resimleri kontrol edersin, bitmiş videoyu izleyip onaylarsın", "kontrol mekanizması"],
];

/* ------------------------------------------------------------ preparation studio (channel tab) */
async function channelPrep(cid, el) {
  const home = await api(`/api/channels/${cid}/prep`);
  const st = (state.prep && state.prep.cid === cid) ? state.prep : (state.prep = { cid, text: "", data: null, report: null, name: "", sec: "summary" });
  const pol = home.policy;
  state.prepAfter = (home.after_import || []).join(" → ");
  el.innerHTML = `
    <div class="help small"><b>Hazırlık stüdyosu.</b> Bir videonun üretimden önceki her şeyi burada tek pakette toplanır: araştırma, kaynaklar, senaryo, iddialar, başlıklar, 3 kapak, Shorts, yayın günü ve YouTube politika denetimi. Paketi Claude hazırlar, fabrika denetler, sen okuyup onaylarsın; "Projeyi kur" ile üretim kendiliğinden başlar.</div>
    <div class="flow">
      <div class="flow-step ${st.data ? "done" : "now"}"><b>1</b><div><div class="t">Konu seç, Claude'a hazırlat</div><div class="small muted">${home.ideas.length} bekleyen fikir · ilk boş gün ${home.slots[0] ? esc(home.slots[0].day + " " + home.slots[0].date) : "yok"}</div></div></div>
      <div class="flow-step ${st.data ? (st.report && st.report.ok ? "done" : "now") : ""}"><b>2</b><div><div class="t">Paketi incele, düzelt</div><div class="small muted">${st.report ? (st.report.ok ? "engel yok" : `${st.report.errors.length + st.report.checks.filter((c) => c.level === "block" && !c.ok).length} engel`) : "Claude'un cevabını yapıştır"}</div></div></div>
      <div class="flow-step ${st.report && st.report.ok ? "now" : ""}"><b>3</b><div><div class="t">Projeyi kur → üretim</div><div class="small muted">sonra: ${esc((home.after_import || []).join(" → "))}</div></div></div>
    </div>
    <div class="grid" style="grid-template-columns:minmax(0,1fr) minmax(300px,380px);align-items:start">
      <div id="pp-main"></div>
      <div>
        <div class="card"><h3>1 · Konu</h3>
          <label class="f">Fikir havuzundan</label>
          <select id="pp-idea" style="width:100%"><option value="">— serbest konu yaz —</option>${home.ideas.map((i) => `<option value="${esc(i.id)}">${esc(i.id)} · ${esc(i.title)}${i.priority ? " (" + esc(i.priority) + ")" : ""}</option>`).join("")}</select>
          <label class="f">ya da serbest konu</label><input id="pp-topic" style="width:100%" placeholder="örn. Do we really use only 10% of our brain?">
          <div class="row" style="margin-top:10px"><button class="primary" id="pp-prompt">Hazırlık istemini kopyala</button><button class="sm ghost" id="pp-show">İstemi göster</button></div>
          <pre id="pp-prompt-view" class="code small hidden" style="white-space:pre-wrap;max-height:300px;overflow:auto;margin-top:8px"></pre>
          <p class="small muted" style="margin-bottom:0">Claude masaüstünde <b>Video Fabrikası</b> projesinde yeni bir sohbet aç, istemi yapıştır (ya da sadece "<span class="kbd">${esc(cid)} için ${home.ideas[0] ? esc(home.ideas[0].id) : "yeni bir video"} hazırla</span>" yaz). Claude araştırır ve tek bir YAML paketi verir.</p></div>
        <div class="card" style="margin-top:14px"><h3>Gelen kutusu <span class="muted small">${home.inbox.length} paket</span></h3>
          <p class="small muted" style="margin-top:0">Claude bilgisayarına bağlıysa paketi doğrudan <span class="kbd">channels/${esc(cid)}/prep/</span> klasörüne yazar; buluttaki Claude yazarsa <span class="kbd">guncelle.bat</span> ile gelir. İçe aktarılanlar <span class="kbd">prep/done/</span> klasörüne taşınır.</p>
          ${home.inbox.map((f) => `<div class="job-row" data-open="${esc(f.name)}"><span><b>${esc(f.title || f.name)}</b><div class="small muted">${esc(f.idea || "")} ${f.planned_date ? "· " + esc(f.planned_date) : ""}</div></span><span class="small muted">${ago(f.mtime)}</span></div>`).join("") || '<p class="muted small">Boş.</p>'}</div>
        <div class="card" style="margin-top:14px"><h3>Kanalın politika ayarı</h3>
          <div class="small">Hassas konu: <b>${esc(pol.sensitive.join(", ") || "yok")}</b>${pol.series.length ? " (" + esc(pol.series.join(", ")) + ")" : ""}<br>Anlatıcı: <b>${esc(pol.narrator === "owner" ? "gerçek uzman (sahip)" : "kurgusal karakter")}</b><br>AI etiketi: <b>${pol.ai_label[0] ? "zorunlu" : "gerekmiyor"}</b> <span class="muted">— ${esc(pol.ai_label[1])}</span></div>
          ${pol.transparency ? `<div class="small quote" style="margin-top:6px">“${esc(pol.transparency)}”</div>` : '<div class="small err">Şeffaflık satırı yok: Kanal ayarları → channel.yaml → policy.transparency</div>'}
          <p class="small muted" style="margin-bottom:0">Kurallar: <a href="#" id="pp-rules">YouTube para kazanma politikaları özeti</a></p></div>
        <div class="card" style="margin-top:14px"><h3>Kim ne yapar</h3>
          <table class="mini"><tbody>${ROLES.map(([w, what, cost]) => `<tr><td><b>${w}</b></td><td>${what}<div class="muted">${cost}</div></td></tr>`).join("")}</tbody></table></div>
      </div></div>`;
  const ideaSel = $("#pp-idea");
  if (st.idea) ideaSel.value = st.idea;
  ideaSel.onchange = () => (st.idea = ideaSel.value);
  const promptUrl = () => `/api/channels/${cid}/prep/prompt?idea=${encodeURIComponent(ideaSel.value)}&topic=${encodeURIComponent($("#pp-topic").value)}`;
  $("#pp-prompt").onclick = async () => { copyText(await api(promptUrl())); toast("İstem kopyalandı: Claude'a yapıştır"); };
  $("#pp-show").onclick = async () => { const v = $("#pp-prompt-view"); if (v.classList.contains("hidden")) v.textContent = await api(promptUrl()); v.classList.toggle("hidden"); };
  $("#pp-rules").onclick = (e) => { e.preventDefault(); policyRulesDrawer(); };
  $$("[data-open]").forEach((r) => (r.onclick = async () => { st.text = await api(`/api/channels/${cid}/prep/inbox/${encodeURIComponent(r.dataset.open)}`); st.name = r.dataset.open; await prepCheck(cid, st); }));
  prepMain(cid, st);
}

async function prepCheck(cid, st) {
  try {
    const r = await api(`/api/channels/${cid}/prep/check`, { method: "POST", body: { text: st.text } });
    st.data = r.data; st.report = r.report;
  } catch (e) { toast(e.message, true); st.report = null; }
  prepMain(cid, st);
}

const PREP_SECTIONS = [["summary", "Özet & denetim"], ["research", "Araştırma"], ["script", "Senaryo"], ["claims", "İddialar & kaynaklar"], ["package", "Başlık & kapak"], ["shorts", "Shorts"], ["schedule", "Takvim"], ["policy", "Politika"], ["raw", "Ham YAML"]];

function prepMain(cid, st) {
  const el = $("#pp-main");
  if (!el) return;
  if (!st.data) {
    el.innerHTML = `<div class="card"><h3>2 · Claude'un paketini yapıştır</h3>
      <textarea id="pp-text" class="code" rows="18" spellcheck="false" placeholder="prep: 1\nchannel: ${esc(cid)}\ntitle: ...\nscript: |\n  ...">${esc(st.text)}</textarea>
      <div class="row" style="margin-top:8px"><button class="primary" id="pp-check">Paketi incele</button><button id="pp-save">Gelen kutusuna kaydet</button><button class="ghost" id="pp-example">Biçim örneği</button></div></div>`;
    $("#pp-check").onclick = async () => { st.text = $("#pp-text").value; st.name = st.name || ""; await prepCheck(cid, st); };
    $("#pp-save").onclick = async () => { try { const r = await api(`/api/channels/${cid}/prep/save`, { method: "POST", body: { text: $("#pp-text").value } }); st.name = r.name; toast("Kaydedildi: " + r.name); viewChannel(cid, "prep"); } catch (e) { toast(e.message, true); } };
    $("#pp-example").onclick = async () => { $("#pp-text").value = await api(`/api/channels/${cid}/prep/example`); toast("Biçim örneği yüklendi (gerçek bir video değil)"); };
    return;
  }
  const d = st.data, r = st.report, s = r.summary;
  const blocks = r.checks.filter((c) => c.level === "block" && !c.ok);
  const warns = r.checks.filter((c) => c.level === "warn" && !c.ok);
  const secCount = (sec) => r.checks.filter((c) => c.section === sec && !c.ok && c.level !== "info").length;
  el.innerHTML = `<div class="card">
      <div class="spread"><h3 style="margin:0">${esc(d.title || "(başlıksız)")}</h3>
        <span>${r.errors.length ? pill(r.errors.length + " hata", "bad") : blocks.length ? pill(blocks.length + " engel", "bad") : pill("engel yok", "ok")} ${warns.length ? pill(warns.length + " uyarı", "warn") : ""}</span></div>
      <div class="row small" style="margin:8px 0 4px">${pill(s.words + " kelime ≈ " + s.minutes + " dk")} ${pill(s.claims + " iddia")} ${pill(s.new_sources + " yeni kaynak")} ${pill(s.chapters + " bölüm")} ${pill(s.titles + " başlık")} ${pill(s.thumbnails + " kapak")} ${pill(s.shorts + " Short")} ${pill(s.planned_date || "tarih yok", s.planned_date ? "" : "warn")} ${s.sensitive ? pill("hassas konu (sağlık)", "info") : ""}</div>
      <div class="tabs" style="margin:10px 0 12px">${PREP_SECTIONS.map(([k, t]) => `<a href="#" data-sec="${k}" class="${st.sec === k ? "active" : ""}">${t}${secCount(k) ? ` <span class="n">${secCount(k)}</span>` : ""}</a>`).join("")}</div>
      <div id="pp-sec"></div>
      <div class="spread" style="margin-top:14px;border-top:1px solid var(--line);padding-top:12px">
        <div class="row"><button id="pp-recheck">Değişiklikleri denetle</button><button id="pp-save2">Gelen kutusuna kaydet</button><button class="ghost" id="pp-new">Yeni paket</button></div>
        <div class="row">${blocks.length && !r.errors.length ? `<label class="small"><input type="checkbox" id="pp-force"> engelleri bilerek geç</label>` : ""}<button class="accent" id="pp-import" ${r.errors.length ? "disabled" : ""}>Projeyi kur ve üretime gönder</button></div></div>
      <div id="live-box" class="hidden" style="margin-top:12px"><div id="live-status" class="small muted"></div><div class="log" id="live-log" style="height:160px"></div></div>
    </div>`;
  $$("[data-sec]").forEach((a) => (a.onclick = (e) => { e.preventDefault(); collect(st); st.sec = a.dataset.sec; prepMain(cid, st); }));
  prepSection(cid, st, $("#pp-sec"));
  const sync = async () => { collect(st); if (st.sec !== "raw") st.text = (await api(`/api/channels/${cid}/prep/dump`, { method: "POST", body: { data: st.data } })).text; };
  $("#pp-recheck").onclick = async () => { await sync(); await prepCheck(cid, st); toast("Yeniden denetlendi"); };
  $("#pp-save2").onclick = async () => { await sync(); try { const x = await api(`/api/channels/${cid}/prep/save`, { method: "POST", body: { text: st.text, name: st.name || null } }); st.name = x.name; toast("Gelen kutusuna kaydedildi: " + x.name); } catch (e) { toast(e.message, true); } };
  $("#pp-new").onclick = () => { if (confirm("Bu paket ekrandan kaldırılsın mı? (Gelen kutusundaki dosya kalır.)")) { state.prep = null; viewChannel(cid, "prep"); } };
  $("#pp-import").onclick = async () => {
    await sync();
    const force = $("#pp-force") && $("#pp-force").checked;
    if (!r.ok && !force) { toast("Önce engelleri düzelt ya da 'engelleri bilerek geç' kutusunu işaretle", true); return; }
    if (!confirm(`"${d.title}" projesi kurulacak, senaryo bölünecek ve şu adımlar çalışacak: ${(state.prepAfter || "bölme → plan → hareketli sahneler → kalite kapısı")}. Devam?`)) return;
    try {
      const x = await api(`/api/channels/${cid}/prep/import`, { method: "POST", body: { text: st.text, name: st.name || null, force } });
      watch(x.job, "Hazırlık → üretim adımları");
      toast("Proje kuruldu: " + x.slug);
      state.onJobsDone = () => { state.prep = null; location.hash = `#/p/${cid}/${x.slug}/board`; };
    } catch (e) { toast(e.message, true); }
  };
}

/* path helpers: "research.answer", "thumbnails.0.visual.prompt" */
function getPath(o, p) { return p.split(".").reduce((a, k) => (a == null ? a : a[k]), o); }
function setPath(o, p, v) { const ks = p.split("."); let a = o; ks.slice(0, -1).forEach((k, i) => { if (a[k] == null) a[k] = /^\d+$/.test(ks[i + 1]) ? [] : {}; a = a[k]; }); a[ks[ks.length - 1]] = v; }
function collect(st) {
  $$("[data-path]").forEach((i) => {
    let v = i.type === "checkbox" ? i.checked : i.value;
    if (i.dataset.kind === "lines") v = v.split("\n").map((x) => x.trim()).filter(Boolean);
    if (i.dataset.kind === "num") v = v === "" ? null : +v;
    setPath(st.data, i.dataset.path, v);
  });
  const raw = $("#pp-raw"); if (raw) st.text = raw.value;
}
const fld = (label, path, val, opt = {}) => `<label class="f">${label}</label>${opt.rows ? `<textarea data-path="${path}" ${opt.kind ? `data-kind="${opt.kind}"` : ""} rows="${opt.rows}" ${opt.code ? 'class="code"' : ""} spellcheck="${opt.code ? "false" : "true"}">${esc(Array.isArray(val) ? val.join("\n") : val ?? "")}</textarea>` : `<input data-path="${path}" ${opt.type ? `type="${opt.type}"` : ""} style="width:100%" value="${esc(val ?? "")}">`}${opt.help ? `<div class="small muted">${opt.help}</div>` : ""}`;
const checksOf = (r, sec) => r.checks.filter((c) => c.section === sec).map((c) => `<div class="check"><span class="ic ${c.ok ? "ok" : c.level}">${c.ok ? "✓" : c.level === "block" ? "✕" : c.level === "warn" ? "!" : "·"}</span><span>${esc(c.message)}</span></div>`).join("");

function prepSection(cid, st, el) {
  const d = st.data, r = st.report;
  const sec = st.sec;
  if (sec === "summary") {
    el.innerHTML = `${r.errors.length ? `<div class="help small" style="border-color:#efb6ae;background:#fff6f4;color:#8e231d"><b>İçe aktarılamaz:</b><br>${r.errors.map(esc).join("<br>")}</div>` : ""}
      <div class="grid g2">${["research", "sources", "script", "package", "shorts", "schedule", "policy"].map((k) => { const t = { research: "Araştırma", sources: "Kaynaklar & iddialar", script: "Senaryo", package: "Başlık & kapak", shorts: "Shorts", schedule: "Takvim", policy: "YouTube politikaları" }[k]; const h = checksOf(r, k); return h ? `<div><h3>${t}</h3>${h}</div>` : ""; }).join("")}</div>`;
    return;
  }
  if (sec === "research") {
    const rs = d.research || {};
    el.innerHTML = `${fld("Soru", "research.question", rs.question)}${fld("Kanıt ne diyor", "research.answer", rs.answer, { rows: 5 })}
      ${fld("Bu videonun farkı (özgünlük)", "research.angle", rs.angle, { rows: 3, help: "YouTube'un 'generic or repetitive content' kuralına karşı en önemli satır: bu video, mevcut videoların söylemediği neyi söylüyor?" })}
      ${fld("Rakip videolar ne diyor", "research.competition", rs.competition, { rows: 2 })}
      ${fld("Sahibin bakması gereken açık sorular (her satır bir soru)", "research.open_questions", rs.open_questions || [], { rows: 3, kind: "lines" })}`;
    return;
  }
  if (sec === "script") {
    const words = (t) => (t.replace(/^#.*$/gm, "").replace(/<!--[\s\S]*?-->/g, "").match(/\b\w+\b/g) || []).length;
    el.innerHTML = `${checksOf(r, "script")}<label class="f">Senaryo <span id="pp-wc"></span> — paragrafları boş satırla ayır; bölüm başlığı: <span class="kbd">&lt;!-- chapter: Başlık --&gt;</span></label>
      <textarea data-path="script" id="pp-script" rows="28">${esc(d.script || "")}</textarea>`;
    const up = () => ($("#pp-wc").textContent = `· ${words($("#pp-script").value)} kelime ≈ ${(words($("#pp-script").value) / 160).toFixed(1)} dk`);
    $("#pp-script").oninput = up; up();
    return;
  }
  if (sec === "claims") {
    const srcIds = [...new Set([...(d.sources || []).map((s) => s.id), ...(d.claims || []).map((c) => c.source).filter(Boolean)])];
    el.innerHTML = `${checksOf(r, "sources")}
      <h3 style="margin-top:12px">İddialar</h3><p class="small muted" style="margin-top:0"><b>Senaryodaki cümle</b>, iddiayı söyleyen kelimelerin aynısı olmalı: fabrika iddiayı bununla doğru shot'a bağlar.</p>
      <table class="mini"><thead><tr><th style="width:44px">id</th><th>İddia</th><th style="width:130px">Kaynak</th><th>Senaryodaki cümle</th></tr></thead><tbody>
      ${(d.claims || []).map((c, i) => `<tr><td>${esc(c.id || "")}</td><td><input data-path="claims.${i}.text" style="width:100%" value="${esc(c.text || "")}">${c.caveat ? `<div class="small muted">çekince: ${esc(c.caveat)}</div>` : ""}</td>
        <td><select data-path="claims.${i}.source" style="width:100%">${srcIds.map((x) => `<option ${x === c.source ? "selected" : ""}>${esc(x)}</option>`).join("")}<option value="" ${c.source ? "" : "selected"}>— kaynak yok</option></select></td>
        <td><input data-path="claims.${i}.says" style="width:100%" value="${esc(c.says || "")}"></td></tr>`).join("")}</tbody></table>
      <h3 style="margin-top:14px">Yeni kaynaklar</h3>
      ${(d.sources || []).map((s) => `<div class="claim" style="grid-template-columns:110px 1fr;margin-bottom:6px"><b>${esc(s.id)}</b><div>${esc(s.authors || "")} ${esc(s.year || "")}. ${esc(s.title || "")} ${s.venue ? "· " + esc(s.venue) : ""} · ${pill(s.type || "?", ["primary", "review", "meta-analysis", "guideline"].includes(s.type) ? "ok" : s.type === "news" ? "warn" : "")}
        ${s.url || s.doi ? ` · <a href="${esc(s.url || "https://doi.org/" + s.doi)}" target="_blank">aç</a>` : ""}${s.limits ? `<div class="small muted">sınır: ${esc(s.limits)}</div>` : ""}</div></div>`).join("") || '<p class="muted small">Pakette yeni kaynak yok (hepsi kütüphanede).</p>'}`;
    return;
  }
  if (sec === "package") {
    const th = d.thumbnails || [];
    el.innerHTML = `${checksOf(r, "package")}${fld("Seçilen başlık", "title", d.title, { help: "Videonun başlığı; en fazla 60 karakter, iddiaların izin verdiğinden büyük söz vermeden." })}
      ${fld("Başlık adayları (her satır bir başlık)", "titles", d.titles || [], { rows: 6, kind: "lines" })}
      ${fld("Açıklamanın ilk iki satırı", "description", d.description, { rows: 2 })}
      <h3 style="margin-top:14px">Kapaklar (Test & Compare için üç tür)</h3>
      <div class="grid g3">${th.map((t, i) => `<div class="card" style="padding:12px"><div class="spread"><b>${String.fromCharCode(65 + i)} · ${esc({ correction: "Düzeltme", stamp: "Damga", scene: "Sahne" }[t.kind] || t.kind || "?")}</b>${t.claim ? pill("iddia " + esc(t.claim), "info") : ""}</div>
        ${fld("Resim tarifi (yazısız)", `thumbnails.${i}.visual.prompt`, (t.visual || {}).prompt, { rows: 4 })}
        ${t.kind === "correction" ? fld("İnanış (üstü çizilir)", `thumbnails.${i}.myth.en`, (t.myth || {}).en) + fld("El yazısı not", `thumbnails.${i}.note.en`, (t.note || {}).en) : ""}
        ${t.kind === "scene" ? fld("Yazı (≤ 3 kelime)", `thumbnails.${i}.text.en`, (t.text || {}).en) : ""}
        ${fld("Yazının yeri", `thumbnails.${i}.pos`, t.pos)}</div>`).join("")}</div>
      <h3 style="margin-top:14px">Açılış önerileri</h3>${(d.hooks || []).map((h) => `<div class="hook">${pill(h.type || "")} ${esc(h.text || "")}</div>`).join("") || '<p class="muted small">yok</p>'}`;
    return;
  }
  if (sec === "shorts") {
    el.innerHTML = `${checksOf(r, "shorts")}<p class="small muted">Her Short, senaryodan bir kesittir: <b>başlangıç</b> ve <b>bitiş</b> kesitin ilk ve son kelimeleri. Fabrika bunları bölünmüş shot'larla eşleştirip dikey videoyu üretir (25–58 sn).</p>
      ${(d.shorts || []).map((s, i) => `<div class="card" style="padding:12px;margin-bottom:10px"><div class="grid g2">${fld("Başlık", `shorts.${i}.title`, s.title)}${fld("Ekranda ilk satır (kanca)", `shorts.${i}.hook`, s.hook)}</div>
        <div class="grid g2">${fld("Başlangıç (ilk kelimeler)", `shorts.${i}.from`, s.from)}${fld("Bitiş (son kelimeler)", `shorts.${i}.to`, s.to)}</div></div>`).join("") || '<p class="muted small">Pakette Short yok.</p>'}`;
    return;
  }
  if (sec === "schedule") {
    el.innerHTML = `${checksOf(r, "schedule")}<div class="form2" style="margin-top:8px"><label>Yayın günü<input type="date" data-path="planned_date" value="${esc(d.planned_date || "")}"></label>
      <label>Seri<input data-path="series" value="${esc(d.series || "")}"></label><label>Tür<input data-path="slot" value="${esc(d.slot || "long")}"></label><label>Açılış tipi<input data-path="hook_type" value="${esc(d.hook_type || "")}"></label></div>
      <p class="small muted">Takvimdeki boş günler kanal sekmesinde: <a href="#/c/${cid}/calendar">Takvim</a>. Yayın saati kanalın ayarından gelir.</p>`;
    return;
  }
  if (sec === "policy") {
    const p = d.policy || {};
    el.innerHTML = `${checksOf(r, "policy")}
      <h3 style="margin-top:12px">Claude'un öz denetimi</h3>
      ${fld("Özgünlük (neden kopya değil)", "policy.originality", p.originality, { rows: 2 })}
      ${fld("Tavsiyenin dayandığı kaynaklar (her satır bir id)", "policy.advice_from", p.advice_from || [], { rows: 2, kind: "lines" })}
      ${fld("Reklam riski ve nasıl ele alındığı (her satır bir madde)", "policy.risks", p.risks || [], { rows: 3, kind: "lines" })}
      <div class="row" style="margin-top:8px"><label class="check"><input type="checkbox" data-path="policy.narrator_claims_expertise" ${p.narrator_claims_expertise ? "checked" : ""}> Anlatıcı uzmanlık iddia ediyor</label>
      <label class="check"><input type="checkbox" data-path="policy.realistic_ai_visuals" ${p.realistic_ai_visuals ? "checked" : ""}> Gerçekçi (fotoğraf gibi) AI görüntü var</label></div>
      <p class="small"><a href="#" id="pp-rules2">YouTube kurallarının özeti →</a></p>`;
    $("#pp-rules2").onclick = (e) => { e.preventDefault(); policyRulesDrawer(); };
    return;
  }
  if (sec === "raw") {
    el.innerHTML = `<p class="small muted" style="margin-top:0">Paketin tamamı. Burada değiştirip "Değişiklikleri denetle" de.</p><textarea id="pp-raw" class="code" rows="30" spellcheck="false">${esc(st.text)}</textarea>`;
  }
}

/* ------------------------------------------------------------ YouTube rules (drawer) */
function policyRulesDrawer() {
  const d = $("#drawer");
  d.classList.remove("hidden");
  d.innerHTML = `<div class="spread"><h2 style="margin:0">YouTube para kazanma politikaları</h2><button class="sm ghost" id="pr-x">✕</button></div>
    <p class="small muted">Fabrikanın her adımda uyguladığı kurallar (Ekim 2026). Ayrıntı ve kaynaklar: <span class="kbd">docs/POLICY.md</span>.</p>
    ${[["Tekrar eden / kalıp içerik", "Her videonun kendi hikâyesi, araştırması ve bakış açısı olmalı. Tekrar eden giriş-çıkış, karakter ve seri formatı serbest; aynı hikâyeyi yeni rakamlarla tekrar etmek değil. Fabrika: senaryoları birbiriyle karşılaştırır (%12 uyarı, %25 engel), hep aynı hükümle biten seriyi uyarır."],
      ["Başkasının içeriği", "Başkasının metnini uzun uzun okumak ya da klip derlemek para kazanmaz. Fabrika: 40 kelimeden uzun alıntıyı uyarır; klip kullanmaz."],
      ["Tatmin etmeyen / itici içerik", "Açık bir hikâye yayı ve gerçek bir sonuç gerekir; yalnızca şok için şok, duygu sömürüsü, gerçekçi sahte felaket yok."],
      ["Hassas konuda yapay persona (Temmuz 2026)", "Sağlık, finans, hukuk konusunda insan uzman gibi davranan yapay karakterler para kazanamaz. Fabrika: sağlık videolarında anlatıcının \"as a coach / as a doctor / my patients\" gibi uzmanlık iddiasını engeller; tavsiye kaynağa ve sağlık otoritesine dayanır; açıklamada şeffaflık satırı zorunlu."],
      ["Tıbbi yanlış bilgi", "Sağlık iddiaları sağlık otoriteleriyle çelişemez. Efsane açıkça yanlış diye söylenir ve kanıtla düzeltilir. Fabrika: sağlık videosunda kılavuz/derleme kaynağı arar, kaynaktan fazlasını söyleyen cümleyi engeller."],
      ["Reklamveren dostu", "Başlıkta, kapakta ve ilk saniyelerde küfür, kan, şiddet, şok dili olmaz; tarihteki ölüm ve şiddet eğitsel bağlamda, sakin anlatılır. Fabrika: başlık/kapak ve açılışı tarar."],
      ["Yanıltıcı başlık ve kapak", "Başlık ve kapak videonun vermediği şeyi vaat edemez. Fabrika: başlık/kapaktaki her sayıyı iddialarda arar."],
      ["Yapay içerik etiketi", "Gerçekçi (fotoğraf gibi) yapay görüntü ya da gerçek bir kişinin sesi taklit edilirse yüklemede 'AI use' işaretlenir. Çizim üslubu ve gerçek kişiyi taklit etmeyen sentetik anlatıcı için gerekmez. Fabrika: kanal ayarına göre kendisi işaretler."],
      ["Dürüstlük ve tempo", "Kanal kim olduğu konusunda dürüst olur; aynı kalıpta toplu yükleme yapılmaz. Fabrika: haftada en fazla 3 uzun video önerir; yüklemeden önce senin onayını ister."]]
      .map(([t, x]) => `<div class="card" style="margin-bottom:10px"><h3>${t}</h3><div class="small">${x}</div></div>`).join("")}`;
  $("#pr-x").onclick = closeDrawer;
}

/* ------------------------------------------------------------ the owner's review (publish tab) */
function reviewCard(cid, slug) {
  const rv = P.review || { steps: {}, labels: {}, approved: false, message: "" };
  return `<div class="card" style="margin-bottom:14px;${rv.approved ? "" : "border-color:#e9c27a"}"><div class="spread"><h3 style="margin:0">Sahip onayı ${rv.approved ? pill("tamam", "ok") : pill("eksik", "warn")}</h3><span class="small muted">${esc(rv.date || "")}</span></div>
    <p class="small muted" style="margin-top:4px">Sen bu sistemin kontrol mekanizmasısın: dört adımı yapmadan video YouTube'a gönderilmez. Bu kayıt aynı zamanda her videoda insan emeği olduğunun kanıtıdır.</p>
    ${Object.entries(rv.labels).map(([k, t]) => `<label class="check"><input type="checkbox" data-rv="${k}" ${rv.steps[k] ? "checked" : ""}> ${esc(t)}</label>`).join("")}
    <div class="row" style="margin-top:8px"><button class="primary sm" id="rv-save">Onayı kaydet</button></div></div>`;
}
function bindReview(cid, slug) {
  const b = $("#rv-save");
  if (!b) return;
  b.onclick = async () => {
    const steps = {}; $$("[data-rv]").forEach((c) => (steps[c.dataset.rv] = c.checked));
    try { P.review = await api(`/api/projects/${cid}/${slug}/review`, { method: "PUT", body: { steps } }); toast(P.review.approved ? "Onay tamam: video gönderilebilir" : "Kaydedildi"); viewProject(cid, slug, "pub"); }
    catch (e) { toast(e.message, true); }
  };
}

/* ------------------------------------------------------------ a short explanation under every button */
const HELP = [
  // home / channel
  ["#nc-go", "Kanal klasörünü, fikir havuzunu ve ayar dosyasını oluşturur."],
  ["#fi-sig", "YouTube'da her fikri aratır: talep, rekabet ve boşluk puanı (ücretsiz anahtar)."],
  ["#fi-add", "Fikir havuzuna elle yeni bir konu ekler."],
  ["#nf-save", "Yeni fikri havuza kaydeder."],
  [".fi-go", "Boş bir proje açar. Önerilen: Hazırlık sekmesinden Claude'a hazırlatmak."],
  ["#np-go", "Boş bir proje açar (senaryoyu kendin yazarsın)."],
  ["#cy-save", "Kanal ayarlarını (channel.yaml) kaydeder; bütün videolar bunu kullanır."],
  ["#br-make", "Profil resmi, banner ve filigranı çizer (2 Gemini resmi, bir kez)."],
  ["#kn-make", "Kanalın tüm kurallarını tek dosyada toplar: Claude projesine yüklenir."],
  ["#yt-login", "Kanalı YouTube API'ye bağlar (tarayıcıda bir kez izin)."],
  ["#cal-prev", "Takvimde 4 hafta geri."], ["#cal-now", "Bu haftaya dön."], ["#cal-next", "Takvimde 4 hafta ileri."],
  // preparation studio
  ["#pp-prompt", "Kanalın kuralları, politikalar ve biçimle birlikte istemi kopyalar: Claude'a yapıştır."],
  ["#pp-show", "Claude'a gidecek istemi burada gösterir."],
  ["#pp-check", "Paketi okur: eksikleri, kaynakları ve YouTube politikalarını denetler. Hiçbir şey kurmaz."],
  ["#pp-save", "Paketi gelen kutusuna kaydeder; sonra açıp devam edebilirsin."],
  ["#pp-example", "Biçimi göstermek için küçük bir örnek paket yükler (yayınlanmaz)."],
  ["#pp-recheck", "Sekmelerde yaptığın değişiklikleri pakete işler ve yeniden denetler."],
  ["#pp-save2", "Düzenlenmiş paketi gelen kutusuna kaydeder."],
  ["#pp-new", "Bu paketi ekrandan kaldırır, yeni bir pakete başlar."],
  ["#pp-import", "Projeyi kurar: senaryo, kaynaklar, iddialar, başlıklar, kapak tarifleri, Shorts, yayın günü; sonra bölme, sahne planı, hareketli sahneler ve kalite kapısı çalışır."],
  // project: script
  ["#sc-save", "Senaryoyu ve kaynak notlarını kaydeder, kalite kapısını yeniler."],
  ["#sc-split", "Kaydeder ve senaryoyu cümle parçalarına (shot) böler; mevcut resimler korunur."],
  ["#so-save", "Kaynak notlarını ve senaryoyu kaydeder."],
  ["#cl-copy", "İddia istemini kopyalar: Claude her iddiaya kaynak bulur."],
  ["#cl-apply", "Claude'un iddia cevabını yapıştıracağın kutuyu açar."],
  ["#cl-go", "İddiaları kaydeder, yeni kaynakları ortak kütüphaneye ekler."],
  // project: scenes
  ["#b-plan", "Her sahnenin resmini tarif eder (Gemini ~0,01 $; manual modda istemi kopyalar)."],
  ["#b-images", "Eksik resimleri çizer (~0,05 $/sahne); değişmeyen sahne tekrar ödenmez."],
  ["#b-video", "Seslendirme ve kurgu sekmesine geçer."],
  ["#apply-go", "Claude'un sahne planını storyboard'a işler."],
  ["#b-motion", "Dosya kartı, hüküm damgası ve rakam sahnelerini kanal kuralına göre kurar (ücretsiz)."],
  ["#b-split", "Senaryoyu yeniden böler; metni değişmeyen cümlelerin planı korunur."],
  ["#b-sheet", "Bütün sahne resimlerini tek sayfada toplar: kontrol için."],
  ["#se-mode-ai", "Bu sahne Gemini resmi olsun."], ["#se-mode-chart", "Bu sahne kodla çizilen grafik olsun (ücretsiz)."],
  ["#se-mode-motion", "Bu sahne hareketli sahne olsun (Remotion, ücretsiz)."],
  ["#se-mprev", "Hareketli sahnenin klibini üretir ve burada oynatır."],
  ["#se-render", "Değişikliği kaydeder ve sahneyi yeniden çizer (AI resmiyse ~0,05 $)."],
  ["#se-save", "Sadece kaydeder; çizim yapmaz."],
  ["#se-merge", "Bu sahnenin resmini kaldırır, önceki resim devam eder."],
  ["[data-split]", "Bu parçadan itibaren yeni bir resim başlatır."],
  ["#se-lines", "Ekran yazılarını ve çevirileri kaydeder."],
  // project: video
  ['[data-step="all"]', "Seslendirme → zamanlama → eksik resimler → kurgu → açıklama; değişmeyen parçalar önbellekten."],
  ['[data-step="voice"]', "Sadece seslendirme."], ['[data-step="align"]', "Her shot'ın konuşmadaki zamanını bulur."],
  ['[data-step="render"]', "Sadece kurgu (ses ve resimler hazırsa)."], ['[data-step="shorts"]', "Proje ayarlarındaki kesitlerden dikey Shorts üretir."],
  ['[data-step="translate"]', "Bu dile shot shot çeviri yapar."], ['[data-step="dub"]', "Bu dilin sesini ana videonun zamanına oturtur (YouTube ek ses izi)."],
  ["[data-copy-tr]", "Çeviri istemini kopyalar (manual mod)."], ["[data-apply-tr]", "Claude'un çevirisini yapıştıracağın kutuyu açar."],
  ["[data-trgo]", "Çeviriyi shot'lara işler."], ["[data-desc]", "YouTube açıklamasını panoya kopyalar."],
  ["[data-yt]", "Başlık, açıklama, kapak, altyazı, liste ve yayın zamanını YouTube'a gönderir; senin onayın yoksa göndermez."],
  ["#my-save", "Proje ayarlarını (project.yaml) kaydeder."],
  // project: package / publish
  ["#pk-copy", "Başlık ve kapak istemini kopyalar (manual mod)."], ["#pk-apply", "Claude'un paket cevabını yapıştıracağın kutuyu açar."],
  ["#pk-make", "10 başlık, 3 kapak fikri, açılış ve Shorts önerisi üretir, kapakları çizer (~0,15 $)."],
  ["#pk-render", "Aşağıdaki tariflerden kapakları yeniden çizer; sadece yazı değiştiyse ücretsiz."],
  ["#pk-go", "Paket cevabını kaydeder."], ["#th-save", "Kapak tariflerini kaydeder (çizmez)."], ["#t-add", "Kendi başlığını adaylara ekler."],
  ["#pb-save", "Yayın kaydını (seri, tarih, tahmin, başlık) kaydeder."], ["#mt-add", "Analytics'ten bir ölçüm satırı ekler."],
  ["#rt-open", "İzlenme eğrisini yapıştıracağın kutuyu açar."], ["#rt-go", "Eğriyi shot'larla eşleştirir: izleyicinin nerede gittiğini gösterir."],
  ["#rv-save", "Onay kutularını kaydeder; dördü tamamsa video YouTube'a gönderilebilir."],
  // system
  ["#lb-check", "Kütüphanedeki her kaynak bağlantısının açıldığını kontrol eder."], ["#lb-edit", "Kütüphaneyi YAML olarak düzenler."],
  ["#lb-save", "Kütüphaneyi kaydeder."], ["#cfg-save", "Genel ayarları (config.yaml) kaydeder."],
  ["[data-save-key]", "Anahtarı sadece bu bilgisayardaki .env dosyasına yazar."], ["[data-del-key]", "Anahtarı siler."],
  ["#job-cancel", "Çalışan işi durdurur."],
];

function helpOn() { try { return localStorage.getItem("vf-help") !== "off"; } catch { return true; } }
function decorateHelp(root = document) {
  if (!helpOn()) return;
  for (const [sel, text] of HELP) {
    root.querySelectorAll(sel).forEach((b) => {
      if (b.closest(".hb") || b.dataset.noHelp != null) return;
      const w = document.createElement("span");
      w.className = "hb";
      b.parentNode.insertBefore(w, b);
      w.appendChild(b);
      const s = document.createElement("small");
      s.textContent = text;
      w.appendChild(s);
    });
  }
}
(function helpObserver() {
  let t = null;
  const mo = new MutationObserver(() => { clearTimeout(t); t = setTimeout(() => { decorateHelp($("#app")); decorateHelp($("#drawer")); }, 30); });
  mo.observe(document.body, { childList: true, subtree: true });
  const foot = $("#provider-foot");
  if (foot && foot.parentNode) {
    const tg = document.createElement("label");
    tg.className = "help-toggle small";
    tg.innerHTML = `<input type="checkbox" ${helpOn() ? "checked" : ""}> Düğme açıklamaları`;
    tg.querySelector("input").onchange = (e) => { try { localStorage.setItem("vf-help", e.target.checked ? "on" : "off"); } catch { /* private window */ } location.reload(); };
    foot.parentNode.insertBefore(tg, foot);
  }
})();
