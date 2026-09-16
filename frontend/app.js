/**
 * Akilli Ticket Asistani v3.0 — Frontend Logic
 * Calisان Portali + IT Uzmani Paneli
 */

const API = "http://localhost:3000/api";

const CAT_ICON = {
  "Yazilim Sorunu":     "💻",
  "Donanim Arizasi":    "🖥️",
  "Ag / Baglanti":      "🌐",
  "Guvenlik / Erisim":  "🔒",
  "Veritabani":         "🗄️",
  "E-posta / Iletisim": "📧",
  "Yedekleme / Veri":   "💾",
  "Lisans / Abonelik":  "🔑",
};

function catIcon(k) {
  // fuzzy match (Turkce/ASCII)
  for (const [key, icon] of Object.entries(CAT_ICON)) {
    if (k && k.toLowerCase().replace(/[ığüşöç]/g, c =>
      ({ı:'i',ğ:'g',ü:'u',ş:'s',ö:'o',ç:'c'}[c]||c))
      .includes(key.toLowerCase().replace(/[ığüşöç]/g, c =>
      ({ı:'i',ğ:'g',ü:'u',ş:'s',ö:'o',ç:'c'}[c]||c)).split(' ')[0])) {
      return icon;
    }
  }
  return "🎫";
}

// ── STATE ──────────────────────────────────────────────────────────────────
let allTickets   = [];
let activeFilter = "all";
let activeDepartmentFilter = "all";
let activeTalep  = null;  // Modal icin
let autoRefreshInterval = null;

function getAuthHeaders(extra={}) {
  const token = localStorage.getItem('token');
  const headers = { ...extra };
  if (token) headers['Authorization'] = 'Bearer ' + token;
  return headers;
}

function formatSla(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const now = new Date();
  const diff = d - now;
  if (diff < 0) return "Süresi Doldu";
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const mins = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
  if (hours > 24) return Math.floor(hours/24) + " gün";
  return `${hours}s ${mins}d`;
}

// ── VIEW SWITCH ────────────────────────────────────────────────────────────
function switchView(view) {
  if (autoRefreshInterval) {
    clearInterval(autoRefreshInterval);
    autoRefreshInterval = null;
  }

  document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
  document.querySelectorAll(".view-btn").forEach(b => b.classList.remove("active"));
  
  const viewEl = document.getElementById(`view-${view}`);
  if (viewEl) viewEl.classList.add("active");
  
  const btn = document.getElementById(`btn-${view}`);
  if (btn) btn.classList.add("active");
  
  if (view === "expert") {
    // Restore toolbars for expert
    document.querySelector(".expert-sidebar").style.display = "flex";
    document.querySelector(".expert-content-header").style.display = "block";
    document.querySelector(".stats-bar").style.display = "flex";
    document.querySelector(".expert-toolbar").style.display = "flex";
    document.getElementById("employee-back-bar").style.display = "none";
    loadTickets();
    
    // Her 15 saniyede bir sessizce guncelle
    autoRefreshInterval = setInterval(() => {
      if (document.getElementById("thread-modal").style.display !== "flex" && 
          document.getElementById("complete-modal").style.display !== "flex") {
        loadTickets(true);
      }
    }, 15000);
  }
}

// ── TALEP TÜRÜ ─────────────────────────────────────────────────────────────
function selectTalepTuru(btn) {
  document.querySelectorAll(".ttur-btn").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
  document.getElementById("talep-turu-val").value = btn.dataset.value;
}

// ── CHAR COUNTER ───────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const ta = document.getElementById("mesaj");
  const cc = document.getElementById("char-count");
  if (ta && cc) {
    ta.addEventListener("input", () => {
      cc.textContent = `${ta.value.length} / 1000`;
    });
  }
});

// ── FILE HANDLING ──────────────────────────────────────────────────────────
function fileSelected(input) {
  const file = input.files[0];
  if (!file) return;
  const drop = document.getElementById("file-drop");
  const label = document.getElementById("file-label");
  drop.classList.add("has-file");
  label.textContent = `✅ ${file.name} (${(file.size/1024).toFixed(1)} KB)`;
}

function fileDragOver(e) {
  e.preventDefault();
  document.getElementById("file-drop").classList.add("drag-over");
}

function fileDrop(e) {
  e.preventDefault();
  const drop = document.getElementById("file-drop");
  drop.classList.remove("drag-over");
  const file = e.dataTransfer.files[0];
  if (!file) return;
  const dt = new DataTransfer();
  dt.items.add(file);
  document.getElementById("file-input").files = dt.files;
  fileSelected(document.getElementById("file-input"));
}

// ── HEALTH CHECK ────────────────────────────────────────────────────────────
// removed as per user request

// ── SUBMIT TICKET ───────────────────────────────────────────────────────────
async function submitTicket(e) {
  e.preventDefault();
  const btn = document.getElementById("submit-btn");

  // Loading state
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner-sm"></div> Analiz ediliyor...';

  const form = new FormData();
  form.append("gonderen_kisi",  document.getElementById("ad-soyad").value);
  form.append("gonderen_birim", document.getElementById("birim").value);
  form.append("oncelik",        "Orta");  // AI belirleyecek
  form.append("mesaj",          document.getElementById("mesaj").value);
  form.append("talep_turu",     document.getElementById("talep-turu-val").value);
  if(currentUser) form.append("kullanici_adi", currentUser.kullanici_adi);
  const fileInput = document.getElementById("file-input");
  if (fileInput.files[0]) form.append("dosya", fileInput.files[0]);

  try {
    const res = await fetch(`${API}/analiz-et`, { 
        method: "POST", 
        body: form,
        headers: getAuthHeaders()
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    renderResult(data);
  } catch (err) {
    showResultError(err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg> Talebi Gönder`;
  }
}

// ── RENDER RESULT ───────────────────────────────────────────────────────────
function renderResult(d) {
  document.querySelector(".form-card").style.display = "none";
  const successPanel = document.getElementById("success-panel");
  successPanel.style.display = "flex";
  document.getElementById("success-talep-no").textContent = d.talep_no || "TKT-0000";
}

function showResultError(msg) {
  alert("Talep oluşturulurken bir hata oluştu: " + msg);
}

function resetForm() {
  document.getElementById("ticket-form").reset();
  document.getElementById("talep-turu-val").value = "Bug / Hata";
  document.querySelectorAll(".ttur-btn").forEach(b => b.classList.remove("active"));
  document.querySelector(".ttur-btn[data-value='Bug / Hata']").classList.add("active");
  document.getElementById("char-count").textContent = "0 / 1000";
  
  const drop = document.getElementById("file-drop");
  drop.classList.remove("has-file");
  document.getElementById("file-label").textContent = "Dosya seçin veya buraya sürükleyin";
  
  document.getElementById("success-panel").style.display = "none";
  document.querySelector(".form-card").style.display = "block";
}

// ── LOAD TICKETS ────────────────────────────────────────────────────────────
function showMyTickets() {
  document.getElementById("view-employee").classList.remove("active");
  document.getElementById("view-expert").classList.add("active");
  document.querySelector(".expert-sidebar").style.display = "none";
  document.querySelector(".expert-content-header").style.display = "none";
  document.querySelector(".stats-bar").style.display = "none";
  document.querySelector(".expert-toolbar").style.display = "none";
  document.getElementById("employee-back-bar").style.display = "block";
  loadTickets();
}

function showEmployeeForm() {
  document.getElementById("view-expert").classList.remove("active");
  document.getElementById("view-employee").classList.add("active");
}

async function loadTickets(silent = false) {
  const loading = document.getElementById("list-loading");
  const listEl  = document.getElementById("ticket-list");
  if (loading && !silent) loading.style.display = "flex";

  try {
    let url = `${API}/talepler`;
    if (currentUser && currentUser.rol === "calisan") {
      url += `?kullanici_adi=${currentUser.kullanici_adi}`;
    }
    const res = await fetch(url, { 
        cache: 'no-store',
        headers: getAuthHeaders()
    });
    if (!res.ok) {
        throw new Error("Sunucu " + res.status + " hatasi dondu");
    }

    const d   = await res.json();
    allTickets = d.talepler || [];

    // İstatistikler
    const oz = d.ozet || {};
    document.getElementById("stat-total").textContent = oz.toplam ?? 0;
    document.getElementById("stat-p1").textContent    = oz.P1 ?? 0;
    document.getElementById("stat-p2").textContent    = oz.P2 ?? 0;
    document.getElementById("stat-p3").textContent    = oz.P3 ?? 0;
    document.getElementById("stat-p4").textContent    = oz.P4 ?? 0;

    renderTickets();
    console.log("renderTickets basariyla calisti");
  } catch (err) {
    console.error("loadTickets hatasi:", err);
    loading.innerHTML = `<span style="color:#EF4444">Yüklenemedi: ${err.message}</span>`;
    return;
  }
  loading.style.display = "none";
}

// ── FILTER ──────────────────────────────────────────────────────────────────
function filterTickets(btn, filter) {
  document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
  activeFilter = filter;
  renderTickets();
}

function filterByDepartment(btn, dept) {
  document.querySelectorAll(".sidebar-item").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
  activeDepartmentFilter = dept;
  document.getElementById("current-department-title").textContent = btn.querySelector('.sidebar-text').textContent;
  renderTickets();
}

function updateSidebarBadges(tickets) {
  const counts = { "all": 0 };
  tickets.forEach(t => {
    if (t.durum !== "tamamlandi") {
      counts["all"]++;
      const dept = t.yonlendirilen_departman || "Genel IT Destek";
      counts[dept] = (counts[dept] || 0) + 1;
    }
  });

  document.querySelectorAll(".sidebar-badge").forEach(badge => badge.textContent = "0");
  
  for (const [dept, count] of Object.entries(counts)) {
    const badge = document.getElementById("badge-" + dept);
    if (badge) badge.textContent = count;
  }
}

// ── RENDER TICKET LIST ───────────────────────────────────────────────────────
function renderTickets() {
  const listEl = document.getElementById("ticket-list");
  const empty  = document.getElementById("list-empty");

  updateSidebarBadges(allTickets);

  const showDone = document.getElementById("show-done")?.checked;
  const filtered = allTickets.filter(t => {
    if (activeFilter !== "all" && (t.ai_oncelik || {}).kod !== activeFilter) return false;
    if (activeDepartmentFilter !== "all" && (t.yonlendirilen_departman || "Genel IT Destek") !== activeDepartmentFilter) return false;
    if (!showDone && t.durum === "tamamlandi") return false;
    return true;
  });

  // Loading satiri kaldir
  const loadingEl = document.getElementById("list-loading");
  if (loadingEl) loadingEl.style.display = "none";

  // Eski kartlari temizle
  listEl.querySelectorAll(".ticket-card").forEach(c => c.remove());

  if (filtered.length === 0) {
    empty.style.display = "flex";
    return;
  }
  empty.style.display = "none";

  filtered.forEach(t => {
    const op     = t.ai_oncelik || {};
    const pCls   = (op.kod || "p4").toLowerCase();
    const isDone = t.durum === "tamamlandi";
    const icon   = catIcon(t.kategori || "");

    const card = document.createElement("div");
    card.className = `ticket-card ${pCls} ${isDone ? "done" : ""}`;
    card.dataset.talep = t.talep_no;

    const mesajKisa = t.mesaj || "";

    card.innerHTML = `
      <div class="tc-priority">
        <span class="tc-prio-icon">${op.ikon || "⚪"}</span>
        <span class="tc-prio-label">${op.kod || "P4"}</span>
      </div>
      <div class="tc-body">
        <div class="tc-top">
          <span class="tc-no">${t.talep_no || "—"}</span>
          <span class="tc-turu">${t.talep_turu || "Diğer"}</span>
          <span class="tc-kategori">${icon} ${t.kategori || "—"}</span>
          ${isDone ? '<span class="tc-done-badge">✅ Tamamlandı</span>' : ""}
          ${(!isDone && t.sla_ihlal && currentUser.rol === 'uzman') ? '<span class="tc-done-badge" style="background:#fef2f2;color:#dc2626;border-color:#fecaca">⚠️ SLA İhlali</span>' : ""}
          ${(!isDone && !t.sla_ihlal && t.sla_deadline && currentUser.rol === 'uzman') ? '<span class="tc-done-badge" style="background:#f0fdf4;color:#166534;border-color:#bbf7d0">SLA: ' + formatSla(t.sla_deadline) + '</span>' : ""}
        </div>
        <div class="tc-mesaj">${mesajKisa}</div>
        <div class="tc-meta">
          <span class="tc-meta-item">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>
            ${t.gonderen_kisi || "—"}
          </span>
          <span class="tc-meta-item">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 00-4 0v2M8 7V5a2 2 0 00-4 0v2"/></svg>
            ${t.gonderen_birim || "—"}
          </span>
          <span class="tc-meta-item">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
            ~${t.cozum_suresi_gun || "?"} gün
          </span>
          <span class="tc-meta-item">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/></svg>
            ~${(t.tahmini_maliyet_tl || 0).toLocaleString("tr-TR")} TL
          </span>
          <span class="tc-meta-item">
            ${formatDate(t.created_at)}
          </span>
          ${t.yuklenen_dosya && t.yuklenen_dosya.dosya_adi ? (
            t.yuklenen_dosya.url ? `
            <a href="${API}${t.yuklenen_dosya.url}" target="_blank" class="tc-meta-item" style="color:#0ea5e9; text-decoration:none; cursor:pointer;" onclick="event.stopPropagation()">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/></svg>
              ${t.yuklenen_dosya.dosya_adi}
            </a>` : `
            <span class="tc-meta-item" style="color:#94a3b8; cursor:not-allowed;" title="Eski bilet olduğu için dosya sunucuda yok">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/></svg>
              ${t.yuklenen_dosya.dosya_adi} (Bulunamadı)
            </span>`
          ) : ''}
        </div>
        ${(() => {
          if (t.emsal_analizi) {
            let detay = "";
            if (t.emsal_analizi.benzer_vakalar && t.emsal_analizi.benzer_vakalar.length > 0) {
              detay = `
                <details style="margin-top: 10px; font-size: 0.8rem; background: rgba(0,0,0,0.03); border: 1px solid rgba(0,0,0,0.06); padding: 10px; border-radius: 6px;">
                  <summary style="cursor:pointer; font-weight:600; color:#0369a1;">Benzer Vakaları Gör (İlk 3)</summary>
                  <ul style="margin: 8px 0 0 0; padding-left: 0; list-style-type: none; border-top: 1px solid rgba(0,0,0,0.06); padding-top: 8px;">
                    ${t.emsal_analizi.benzer_vakalar.map(v => `
                      <li style="margin-bottom:10px; color:#334155;">
                        <strong style="color:#0f172a; font-weight:600;">[${v.talep_no}]</strong> 
                        <span style="color:#64748b;">(%${v.benzerlik} benzer)</span> - ${v.mesaj}<br/>
                        <div style="display:flex; align-items:center; gap:12px; margin-top:4px; font-size:0.75rem; color:#475569; font-weight:500;">
                          <span style="display:flex; align-items:center; gap:4px;">
                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                            ${v.sure} gün
                          </span>
                          <span style="display:flex; align-items:center; gap:4px;">
                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"></line><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>
                            ${v.maliyet.toLocaleString("tr-TR")} TL
                          </span>
                        </div>
                      </li>
                    `).join('')}
                  </ul>
                </details>
              `;
            }
            return `
              <div class="tc-insight" style="flex-direction:column; align-items:stretch;">
                <div style="display:flex; align-items:flex-start; gap:8px;">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink:0; margin-top:2px;"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
                  <span><strong>Anlamsal Emsal Analizi:</strong> En çok benzeyen (%${t.emsal_analizi.ortalama_benzerlik}) önceki ${t.emsal_analizi.adet} vaka ortalama <strong>${t.emsal_analizi.ortalama_sure_gun} gün</strong> ve <strong>${t.emsal_analizi.ortalama_maliyet_tl.toLocaleString("tr-TR")} TL</strong> ile sonuçlanmıştır.</span>
                </div>
                ${detay}
              </div>
            `;
          }
          return "";
        })()}
      </div>
      <div class="tc-actions">
        ${!isDone ? (
          (currentUser && currentUser.rol === 'uzman') ? `
          <button class="complete-btn" onclick="openCompleteModal('${t.talep_no}')" style="margin-bottom:5px;">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
            Tamamla
          </button>` : ''
        ) : `
          <div style="font-size:0.72rem;color:#6B7280;text-align:center;margin-bottom:5px;">
            <div>${t.gercek_sure_gun ?? "—"} gün</div>
            <div>${(t.gercek_maliyet_tl || 0).toLocaleString("tr-TR")} TL</div>
          </div>`
        }
        <button class="complete-btn" onclick="openThreadModal('${t.talep_no}')" style="background:#e2e8f0; color:#1e293b; position:relative;">
          💬 Yazışma / Log
          ${(() => {
            if (!t.son_yorum_tarihi || t.son_yorum_yapan_rol === (currentUser ? currentUser.rol : '')) return '';
            const rTime = localStorage.getItem('read_ticket_' + (currentUser ? currentUser.kullanici_adi : '') + '_' + t.talep_no);
            if (!rTime || rTime < t.son_yorum_tarihi) {
              return '<span style="position:absolute; top:-4px; right:-4px; width:10px; height:10px; background:#10B981; border-radius:50%; border:2px solid #fff;"></span>';
            }
            return '';
          })()}
        </button>
      </div>
    `;
    listEl.appendChild(card);
  });
}

function formatDate(iso) {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("tr-TR", { day:"2-digit", month:"short", hour:"2-digit", minute:"2-digit" });
  } catch { return ""; }
}

// ── COMPLETE MODAL ───────────────────────────────────────────────────────────
function openCompleteModal(talepNo) {
  activeTalep = talepNo;
  document.getElementById("modal-talep-no").textContent = talepNo;
  document.getElementById("modal-sure").value    = "";
  document.getElementById("modal-maliyet").value = "";

  document.getElementById("complete-modal").style.display = "flex";
}

function closeModal(e) {
  if (e.target.id === "complete-modal")
    document.getElementById("complete-modal").style.display = "none";
}

async function saveComplete() {
  const sure    = parseFloat(document.getElementById("modal-sure").value);
  const maliyet = parseFloat(document.getElementById("modal-maliyet").value);

  if (!sure || sure <= 0)    { alert("Lütfen geçerli bir süre girin."); return; }
  if (!maliyet || maliyet < 0) { alert("Lütfen geçerli bir maliyet girin."); return; }

  const saveBtn = document.getElementById("modal-save-btn");
  saveBtn.disabled = true;
  saveBtn.textContent = "Kaydediliyor...";

  try {
    const res = await fetch(`${API}/talep-tamamla`, {
      method: "POST",
      headers: getAuthHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ talep_no: activeTalep, gercek_sure_gun: sure, gercek_maliyet_tl: maliyet }),
    });
    if (!res.ok) throw new Error(await res.text());
    const d = await res.json();

    document.getElementById("complete-modal").style.display = "none";
    showToast(`✅ ${activeTalep} tamamlandı! Sistem ${d.ogrenme?.toplam_gercek_ticket || 0} gerçek veriden öğreniyor.`);
    loadTickets();
  } catch (err) {
    alert(`Hata: ${err.message}`);
  } finally {
    saveBtn.disabled = false;
    saveBtn.textContent = "Kaydet";
  }
}

// ── TOAST ────────────────────────────────────────────────────────────────────
function showToast(msg) {
  const t = document.createElement("div");
  t.style.cssText = `
    position:fixed;bottom:28px;left:50%;transform:translateX(-50%);
    background:#1A1A1A;color:#fff;padding:12px 24px;
    border-radius:10px;font-size:0.85rem;z-index:9999;
    box-shadow:0 4px 20px rgba(0,0,0,0.2);
    animation:slideUp 0.2s ease;
    max-width:90vw;text-align:center;
  `;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 4000);
}

// ── LOGIN ───────────────────────────────────────────────────────────────────
let currentUser = null;

async function handleLogin(e) {
  e.preventDefault();
  const u = document.getElementById("login-user").value;
  const p = document.getElementById("login-pass").value;
  try {
    console.log("Login basliyor:", u);
    const res = await fetch(`${API}/login`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({kullanici_adi: u, sifre: p})
    });
    if (!res.ok) throw new Error();
    const data = await res.json();
    currentUser = data.user;
    localStorage.setItem('token', data.token);
    
    document.getElementById("login-error").style.display = "none";
    document.getElementById("user-info").textContent = "Hoş geldin, " + currentUser.ad_soyad;
    document.getElementById("user-info").style.display = "inline-block";
    document.getElementById("btn-logout").style.display = "inline-flex";

    if (currentUser.rol === "uzman") {
      switchView("expert");
    } else {
      switchView("employee");
      document.getElementById("ad-soyad").value = currentUser.ad_soyad;
      document.getElementById("birim").value = currentUser.birim;
    }
  } catch(err) {
    console.error("Login hatasi:", err);
    const errEl = document.getElementById("login-error");
    errEl.style.display = "block";
    errEl.textContent = "Giriş başarısız: " + (err.message || "Bağlantı hatası");
  }
}

function handleLogout() {
  currentUser = null;
  localStorage.removeItem('token');
  document.getElementById("user-info").style.display = "none";
  document.getElementById("btn-logout").style.display = "none";
  
  // Clear login form fields
  document.getElementById("login-user").value = "";
  document.getElementById("login-pass").value = "";
  document.getElementById("login-error").style.display = "none";
  
  switchView("login");
}

// ── THREAD MODAL ────────────────────────────────────────────────────────────
async function openThreadModal(talepNo) {
  activeTalep = talepNo;
  document.getElementById("thread-talep-no").textContent = talepNo;
  document.getElementById("thread-modal").style.display = "flex";
  await loadThread(talepNo);
}

function closeThreadModal(e) {
  if (e.target.id === "thread-modal")
    document.getElementById("thread-modal").style.display = "none";
}

async function loadThread(talepNo) {
  const container = document.getElementById("thread-messages");
  container.innerHTML = '<div class="spinner-sm"></div>';
  try {
    const res = await fetch(`${API}/talep/${talepNo}/yorum`, { 
        cache: 'no-store',
        headers: getAuthHeaders()
    });
    const yorumlar = await res.json();
    container.innerHTML = "";
    if (yorumlar.length === 0) {
      container.innerHTML = '<p style="color:#64748b; text-align:center; margin-top:20px;">Henüz bir yazışma yok.</p>';
      return;
    }
    yorumlar.forEach(y => {
      const isMe = y.yazar_adi === currentUser.ad_soyad;
      const b = document.createElement("div");
      b.className = `msg-bubble ${isMe ? "msg-bubble-right" : "msg-bubble-left"}`;
      b.innerHTML = `
        <span class="msg-author">${y.yazar_adi} (${y.yazar_rol})</span>
        <div style="margin: 4px 0;">${y.mesaj}</div>
        <span class="msg-info">${formatDate(y.created_at)}</span>
      `;
      container.appendChild(b);
    });
    
    // Okundu isaretle
    const lastComment = yorumlar[yorumlar.length - 1];
    if (lastComment) {
      localStorage.setItem('read_ticket_' + (currentUser ? currentUser.kullanici_adi : '') + '_' + talepNo, lastComment.created_at);
      // Listeyi guncelle ki yesil nokta aninda gitsin (arka planda)
      renderTickets();
    }
    
    container.scrollTop = container.scrollHeight;
  } catch (err) {
    container.innerHTML = "Yüklenemedi.";
  }
}

async function submitComment(e) {
  e.preventDefault();
  const inp = document.getElementById("thread-input");
  const msg = inp.value;
  inp.value = "";
  try {
    await fetch(`${API}/talep/${activeTalep}/yorum`, {
      method: "POST",
      headers: getAuthHeaders({"Content-Type": "application/json"}),
      body: JSON.stringify({
        talep_no: activeTalep,
        yazar_adi: currentUser.ad_soyad,
        yazar_rol: currentUser.rol,
        mesaj: msg
      })
    });
    await loadThread(activeTalep);
  } catch(err) {
    console.error(err);
    alert("Hata: " + err.message);
  }
}
