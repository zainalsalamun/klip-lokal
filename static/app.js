const form = document.querySelector('#form');
const button = document.querySelector('#submit');
const statusEl = document.querySelector('#status');
const errorEl = document.querySelector('#error');
const historyList = document.querySelector('#history-list');
const historyMessage = document.querySelector('#history-message');
const sidebar = document.querySelector('#app-sidebar');
const historyPanel = document.querySelector('#history');
const studioContent = document.querySelector('#studio-content');
const newJobButton = document.querySelector('#new-job');
const historyNav = document.querySelector('.history-nav');
function syncView() {
  const showingHistory = location.hash === '#history';
  historyPanel.hidden = !showingHistory;
  studioContent.hidden = showingHistory;
  document.querySelector('#results').hidden = showingHistory || !document.querySelector('#clips').children.length;
  historyNav.classList.toggle('active', showingHistory);
  historyNav.toggleAttribute('aria-current', showingHistory);
  if (showingHistory) historyNav.setAttribute('aria-current', 'page');
  for (const nav of sidebar.querySelectorAll('.nav:not(.history-nav)')) {
    const isCurrent = (!showingHistory) && (
      new URL(nav.href, location.href).pathname === location.pathname ||
      (nav.getAttribute('href') === '/kids' && (document.body.classList.contains('kids-studio') || document.body.classList.contains('kids-source'))) ||
      (nav.getAttribute('href') === '/global' && document.body.classList.contains('global-studio')) ||
      (nav.getAttribute('href') === '/' && !(document.body.classList.contains('kids-studio') || document.body.classList.contains('kids-source')) && !document.body.classList.contains('global-studio'))
    );
    nav.classList.toggle('active', isCurrent);
  }
  document.querySelector('header>span').textContent = 'Workspace / ' + (showingHistory ? 'Riwayat klip' : (document.body.classList.contains('kids-studio') || document.body.classList.contains('kids-source')) ? 'Studio Anak' : document.body.classList.contains('global-studio') ? 'Studio Global' : 'Studio klip');
}
window.addEventListener('hashchange', () => { syncView(); setSidebar(false, false); window.scrollTo(0, 0); });
syncView();
const mobileHistory = document.createElement('button'); mobileHistory.type = 'button'; mobileHistory.className = 'mobile-history-toggle';
mobileHistory.textContent = '☰ Menu'; mobileHistory.setAttribute('aria-controls', sidebar.id); mobileHistory.setAttribute('aria-expanded', 'false');
document.querySelector('header').prepend(mobileHistory);
const sidebarClose = document.createElement('button'); sidebarClose.type = 'button'; sidebarClose.className = 'sidebar-close'; sidebarClose.textContent = '×'; sidebarClose.setAttribute('aria-label', 'Tutup sidebar');
sidebar.prepend(sidebarClose);
const backdrop = document.createElement('button'); backdrop.type = 'button'; backdrop.className = 'sidebar-backdrop'; backdrop.tabIndex = -1; backdrop.setAttribute('aria-label', 'Tutup sidebar'); document.body.append(backdrop);
const mobileWidth = window.matchMedia('(max-width: 820px)');
function setSidebar(open, restoreFocus = true) {
  document.body.classList.toggle('sidebar-open', open);
  mobileHistory.setAttribute('aria-expanded', String(open));
  sidebar.inert = mobileWidth.matches && !open;
  if (open && mobileWidth.matches) { sidebar.setAttribute('role', 'dialog'); sidebar.setAttribute('aria-modal', 'true'); sidebarClose.focus(); }
  else { sidebar.removeAttribute('role'); sidebar.removeAttribute('aria-modal'); if (restoreFocus && mobileWidth.matches) mobileHistory.focus(); }
}
mobileHistory.addEventListener('click', () => setSidebar(!document.body.classList.contains('sidebar-open')));
sidebarClose.addEventListener('click', () => setSidebar(false)); backdrop.addEventListener('click', () => setSidebar(false));
mobileWidth.addEventListener('change', () => setSidebar(false, false));
document.addEventListener('keydown', event => {
  if (!mobileWidth.matches || !document.body.classList.contains('sidebar-open')) return;
  if (event.key === 'Escape') { event.preventDefault(); setSidebar(false); }
  if (event.key === 'Tab') {
    const available = [...sidebar.querySelectorAll('a[href], button:not(:disabled), input, textarea, select, [tabindex="0"]')].filter(element => element.getClientRects().length);
    const first = available[0], last = available.at(-1);
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  }
});
setSidebar(false, false);
let timer, activeJobId = null, selectedJobId = null, selectionVersion = 0;
const historyState = {page:1, query:'', status:'all', total:0, filtered:0, pages:1, activeId:null};
let historyVersion = 0, searchTimer;
const historyTools = document.createElement('div'); historyTools.className = 'history-tools';
historyTools.innerHTML = '<label class="history-search">Cari riwayat<input type="search" id="history-search" placeholder="Cari judul video atau link…" maxlength="200" autocomplete="off"></label><div class="history-filters" role="group" aria-label="Filter status riwayat"><button type="button" data-status="all" aria-pressed="true">Semua</button><button type="button" data-status="processing" aria-pressed="false">Diproses</button><button type="button" data-status="done" aria-pressed="false">Selesai</button><button type="button" data-status="failed" aria-pressed="false">Gagal</button></div>';
historyMessage.before(historyTools);
const pagination = document.createElement('nav'); pagination.className = 'history-pagination'; pagination.setAttribute('aria-label', 'Halaman riwayat');
pagination.innerHTML = '<span id="history-range" role="status"></span><div><button type="button" id="history-prev" aria-label="Halaman sebelumnya">← Sebelumnya</button><span id="history-page"></span><button type="button" id="history-next" aria-label="Halaman berikutnya">Berikutnya →</button></div>';
historyList.after(pagination);
function historyError(error) { historyMessage.textContent = error instanceof ConnectionError ? connectionMessage : 'Riwayat tidak dapat dimuat: ' + error.message; }
document.querySelector('#history-search').addEventListener('input', event => {
  historyState.query = event.target.value.trim(); historyState.page = 1;
  ++historyVersion; clearTimeout(searchTimer); searchTimer = setTimeout(() => refreshHistory().catch(historyError), 250);
});
for (const filter of historyTools.querySelectorAll('[data-status]')) filter.addEventListener('click', () => {
  clearTimeout(searchTimer); historyState.status = filter.dataset.status; historyState.page = 1;
  refreshHistory().catch(historyError);
});
document.querySelector('#history-prev').addEventListener('click', () => { historyState.page = Math.max(1, historyState.page-1); refreshHistory().catch(historyError); });
document.querySelector('#history-next').addEventListener('click', () => { historyState.page = Math.min(historyState.pages, historyState.page+1); refreshHistory().catch(historyError); });
const outputSizes = {480: '480 × 854', 720: '720 × 1280', 1080: '1080 × 1920'};
function syncFormat() {
  if (!form) return;
  window.KlipSelect?.refresh();
  syncSubtitleStyle();
  const formatEl = document.querySelector('#format-details');
  if (formatEl && form.elements.resolution) formatEl.textContent = outputSizes[form.elements.resolution.value] + ' · MP4 · ' + 'crop mengikuti pembicara';
}
function syncSubtitleStyle() {
  if (!form) return;
  const select = form.elements.subtitle_style;
  const preview = document.querySelector('.subtitle-preview');
  if (preview && select && select.selectedOptions[0]) {
    preview.dataset.style = select.value;
    const descEl = document.querySelector('#subtitle-style-description');
    if (descEl) descEl.textContent = select.selectedOptions[0].dataset.description;
  }
}
if (form) {
  form.elements.subtitle_style.addEventListener('change', syncSubtitleStyle);
  syncSubtitleStyle();
  if (form.dataset.kidsDuration) form.elements.duration.value = form.dataset.kidsDuration;
  window.KlipSelect?.refresh();
  form.elements.resolution.addEventListener('change', syncFormat);
  syncFormat();
}
const connectionMessage = 'Server lokal tidak terhubung. Jalankan aplikasi, lalu muat ulang halaman.';

class ConnectionError extends Error {}
async function api(path, options) {
  let response;
  try {
    response = await fetch(path, options);
  } catch (error) {
    throw new ConnectionError('Server lokal tidak dapat dihubungi.', {cause:error});
  }
  let data;
  try { data = await response.json(); }
  catch (_) { throw Error('Respons server tidak valid (HTTP ' + response.status + '). Muat ulang halaman.'); }
  if (!response.ok) {
    const error = Error(data.error || 'Permintaan gagal (HTTP ' + response.status + ')');
    error.data = data;
    error.status = response.status;
    throw error;
  }
  return data;
}
function remember(id) {
  try { if (id) localStorage.setItem('klip-selected', id); else localStorage.removeItem('klip-selected'); } catch (_) {}
}
function showError(message) {
  if (errorEl) errorEl.textContent = message;
  if (button) button.disabled = Boolean(activeJobId);
  const prog = document.querySelector('#progress');
  if (prog) prog.hidden = false;
}
function formatTime(n) { return Math.floor(n/60) + ':' + String(Math.floor(n%60)).padStart(2, '0'); }
function makeCaption(text, audience = 'local') {
  text = String(text || '').replace(/\s+/g, ' ').trim();
  const sentences = text.split(/(?<=[.!?])\s+/);
  let caption = sentences.find(sentence => sentence.split(/\s+/).length >= 4) || text;
  const words = caption.split(/\s+/);
  const shortened = words.length > 16 || caption.length > 120;
  caption = words.slice(0,16).join(' ');
  if (caption.length > 120) caption = caption.slice(0,120).replace(/\s+\S*$/, '');
  if (shortened) caption = caption.replace(/[.,;:!?…]+$/, '') + '…';
  return caption || (audience === 'global_en' ? 'A moment worth sharing.' : 'Satu momen, banyak cerita.');
}
function formatSaveTime(isoString) {
  if (!isoString) return '';
  const d = new Date(isoString);
  if (Number.isNaN(d.getTime())) return '';
  return ' (' + d.toLocaleTimeString('id-ID', {hour:'2-digit', minute:'2-digit'}) + ')';
}
function hasUnsavedCaptionEdits() {
  return Boolean(document.querySelector('.caption-editor.has-unsaved, .watermark-editor.has-unsaved, #kids-brief-section.has-unsaved'));
}
window.addEventListener('beforeunload', event => {
  if (hasUnsavedCaptionEdits()) {
    event.preventDefault();
    event.returnValue = '';
  }
});
function captionEditor(clip, index, jobId, audience) {
  const box = document.createElement('section'); box.className = 'caption-editor';
  const clipId = clip.clip_id || String(index);
  let savedCaption = clip.caption ?? (clip.text ? makeCaption(clip.text, audience) : '');
  let currentRevision = clip.caption_revision || clip.metadata_revision || 1;
  let isBusy = false;

  const header = document.createElement('div'); header.className = 'caption-editor-header';
  const label = document.createElement('label'); label.textContent = 'Caption posting'; label.htmlFor = 'caption-' + clipId;
  const targetBadge = document.createElement('span'); targetBadge.className = 'caption-target-badge';
  targetBadge.textContent = audience === 'global_en' ? 'Target AI: English' : 'Target AI: Indonesia';
  header.append(label, targetBadge);

  const textarea = document.createElement('textarea'); textarea.id = label.htmlFor; textarea.rows = 4;
  textarea.maxLength = 2000; textarea.placeholder = 'Buat caption AI dari pembahasan klip, atau tulis sendiri…'; textarea.value = savedCaption;

  const saveBtn = document.createElement('button'); saveBtn.type = 'button'; saveBtn.className = 'btn-save-caption'; saveBtn.textContent = 'Simpan caption'; saveBtn.disabled = true;
  const generate = document.createElement('button'); generate.type = 'button'; generate.className = 'btn-ai-caption'; generate.textContent = 'Buat caption AI lokal';

  const statusBadge = document.createElement('div'); statusBadge.className = 'caption-status-badge';
  statusBadge.setAttribute('role', 'status'); statusBadge.setAttribute('aria-live', 'polite');

  function isDirty() {
    return textarea.value !== savedCaption;
  }
  function syncDirtyState() {
    const dirty = isDirty();
    box.classList.toggle('has-unsaved', dirty);
    saveBtn.disabled = isBusy || !dirty;
    generate.disabled = isBusy;
    textarea.disabled = isBusy;
  }

  function updateStatus(state, msg) {
    statusBadge.className = 'caption-status-badge state-' + state;
    syncDirtyState();
    if (msg) { statusBadge.textContent = msg; return; }
    if (state === 'saved') {
      if (clip.caption_source === 'manual') {
        statusBadge.textContent = '✓ Tersimpan · Edit manual' + formatSaveTime(clip.caption_updated_at);
      } else if (clip.caption_source === 'ai_local') {
        const lang = clip.caption_language === 'en' ? 'English' : 'Indonesia';
        statusBadge.textContent = '✓ Tersimpan · AI lokal (' + lang + ')' + formatSaveTime(clip.caption_updated_at);
      } else {
        statusBadge.textContent = 'Cuplikan transkrip otomatis';
      }
    } else if (state === 'modified') {
      statusBadge.textContent = '● Ada perubahan belum disimpan ke server';
    } else if (state === 'saving') {
      statusBadge.textContent = 'Menyimpan caption ke server…';
    } else if (state === 'conflict') {
      statusBadge.textContent = '⚠ Konflik: Versi server telah diperbarui';
    } else if (state === 'error') {
      statusBadge.textContent = '⚠ Gagal menyimpan caption';
    }
  }
  updateStatus('saved');

  const note = document.createElement('small'); note.className = 'caption-note';
  function updateNote() {
    if (clip.caption_source === 'manual') {
      note.textContent = 'Edit manual · pilihanmu, tidak divalidasi AI';
    } else if (clip.caption_source === 'ai_local') {
      note.textContent = clip.caption_note || 'Ringkasan AI lokal · tinjau sebelum posting';
    } else {
      note.textContent = clip.caption_note || 'Cuplikan transkrip · belum dirangkum AI';
    }
  }
  updateNote();

  const legacyKey = 'klip-caption:' + clip.url;
  let legacyDraft = null;
  try { legacyDraft = localStorage.getItem(legacyKey); } catch (_) {}

  const draftBanner = document.createElement('div'); draftBanner.className = 'caption-draft-banner'; draftBanner.hidden = true;
  const conflictBanner = document.createElement('div'); conflictBanner.className = 'caption-conflict-banner'; conflictBanner.hidden = true;

  const metaBar = document.createElement('div'); metaBar.className = 'caption-meta-bar';
  const charDisplay = document.createElement('span'); charDisplay.className = 'caption-char-count';
  function updateCharCount() {
    const len = textarea.value.length;
    charDisplay.textContent = len.toLocaleString('id-ID') + ' / 2.000 karakter';
    charDisplay.classList.toggle('is-limit', len >= 2000);
  }
  metaBar.append(note, charDisplay);
  updateCharCount();

  const actions = document.createElement('div'); actions.className = 'caption-actions';
  const copy = document.createElement('button'); copy.type = 'button'; copy.className = 'btn-copy-caption'; copy.textContent = 'Salin caption';
  const saveTxt = document.createElement('button'); saveTxt.type = 'button'; saveTxt.className = 'btn-download-txt'; saveTxt.textContent = 'Unduh TXT';
  const cancel = document.createElement('button'); cancel.type = 'button'; cancel.className = 'btn-cancel-caption'; cancel.textContent = 'Batal'; cancel.hidden = true;
  const feedback = document.createElement('span'); feedback.className = 'caption-feedback'; feedback.setAttribute('role', 'status');

  textarea.addEventListener('input', () => {
    updateCharCount();
    if (isDirty()) {
      updateStatus('modified');
      conflictBanner.hidden = true;
    } else {
      updateStatus('saved');
    }
  });

  if (legacyDraft != null) {
    if (legacyDraft.trim() !== (savedCaption || '').trim()) {
      draftBanner.hidden = false;
      const draftMsg = document.createElement('p');
      draftMsg.textContent = 'Ditemukan draft browser lama yang belum tersimpan ke server.';
      const draftActions = document.createElement('div'); draftActions.className = 'draft-banner-actions';
      const restoreBtn = document.createElement('button'); restoreBtn.type = 'button'; restoreBtn.textContent = 'Pulihkan draft browser';
      restoreBtn.addEventListener('click', () => {
        textarea.value = legacyDraft;
        updateCharCount();
        updateStatus('modified', '● Draft browser dipulihkan (belum disimpan ke server)');
        draftBanner.hidden = true;
        feedback.textContent = 'Draft browser dimuat. Klik "Simpan caption" untuk menyimpannya ke server.';
      });
      const discardBtn = document.createElement('button'); discardBtn.type = 'button'; discardBtn.textContent = 'Pakai versi tersimpan';
      discardBtn.addEventListener('click', () => {
        try { localStorage.removeItem(legacyKey); } catch (_) {}
        legacyDraft = null;
        draftBanner.hidden = true;
        feedback.textContent = 'Draft browser lama dibuang; memakai versi tersimpan server.';
      });
      draftActions.append(restoreBtn, discardBtn);
      draftBanner.append(draftMsg, draftActions);
    } else {
      try { localStorage.removeItem(legacyKey); } catch (_) {}
    }
  }

  saveBtn.addEventListener('click', async () => {
    if (isBusy || !isDirty()) return;
    isBusy = true;
    syncDirtyState();
    updateStatus('saving'); feedback.textContent = ''; feedback.classList.remove('is-error');
    try {
      const res = await api('/api/jobs/' + encodeURIComponent(jobId) + '/clips/' + encodeURIComponent(clipId) + '/caption', {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({caption: textarea.value, expected_revision: currentRevision})
      });
      clip.caption = res.caption; clip.caption_source = res.caption_source; clip.caption_language = res.caption_language;
      clip.caption_updated_at = res.caption_updated_at;
      currentRevision = res.caption_revision || res.metadata_revision || (currentRevision + 1);
      clip.caption_revision = currentRevision;
      clip.metadata_revision = res.metadata_revision || currentRevision;
      savedCaption = res.caption;
      try { localStorage.removeItem(legacyKey); } catch (_) {}
      legacyDraft = null; draftBanner.hidden = true; conflictBanner.hidden = true;
      updateNote(); updateStatus('saved');
      feedback.textContent = 'Caption manual berhasil disimpan ke server.';
    } catch (err) {
      if (err.data && err.data.conflict) {
        updateStatus('conflict');
        showConflictUI(err.data);
      } else {
        updateStatus('error');
        feedback.textContent = err instanceof ConnectionError ? connectionMessage : (err.message || 'Gagal menyimpan caption.');
        feedback.classList.add('is-error');
      }
    } finally {
      isBusy = false;
      syncDirtyState();
    }
  });

  function showConflictUI(data) {
    conflictBanner.replaceChildren(); conflictBanner.hidden = false;
    const msg = document.createElement('p');
    msg.textContent = 'Konflik revisi: Caption di server telah diubah oleh sesi lain. Ketikanmu tetap aman di bawah.';
    const actionsDiv = document.createElement('div'); actionsDiv.className = 'conflict-banner-actions';
    const loadServerBtn = document.createElement('button'); loadServerBtn.type = 'button';
    loadServerBtn.textContent = 'Pakai versi server (' + (data.server_caption ? data.server_caption.slice(0, 30) + '…' : 'kosong') + ')';
    loadServerBtn.addEventListener('click', () => {
      textarea.value = data.server_caption || ''; savedCaption = data.server_caption || '';
      currentRevision = data.current_revision; clip.caption = data.server_caption;
      clip.metadata_revision = data.current_revision; clip.caption_source = data.server_source || 'manual';
      updateCharCount(); updateNote(); updateStatus('saved'); conflictBanner.hidden = true;
      feedback.textContent = 'Versi server dimuat.';
    });
    const overwriteBtn = document.createElement('button'); overwriteBtn.type = 'button';
    overwriteBtn.textContent = 'Timpa dengan teks ini';
    overwriteBtn.addEventListener('click', () => {
      currentRevision = data.current_revision; conflictBanner.hidden = true; saveBtn.click();
    });
    actionsDiv.append(loadServerBtn, overwriteBtn);
    conflictBanner.append(msg, actionsDiv);
  }

  copy.addEventListener('click', async () => {
    const isModified = textarea.value !== savedCaption;
    try {
      await navigator.clipboard.writeText(textarea.value);
      feedback.textContent = isModified ? 'Tersalin (ada perubahan belum disimpan ke server)' : 'Tersalin';
    } catch (_) {
      textarea.focus(); textarea.select();
      feedback.textContent = 'Tekan ⌘C / Ctrl+C untuk menyalin';
    }
  });

  saveTxt.addEventListener('click', () => {
    const isModified = textarea.value !== savedCaption;
    const blob = new Blob([textarea.value], {type:'text/plain;charset=utf-8'});
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a'); link.href = url; link.download = 'caption-klip-' + (index + 1) + '.txt';
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    feedback.textContent = isModified ? 'Unduhan TXT dimulai (ada perubahan belum disimpan ke server)' : 'Unduhan TXT dimulai';
  });

  let replaceConfirmed = false;
  cancel.addEventListener('click', () => {
    replaceConfirmed = false; cancel.hidden = true; generate.textContent = 'Buat caption AI lokal'; feedback.textContent = '';
  });

  generate.addEventListener('click', async () => {
    const isModified = isDirty();
    const hasCustomText = textarea.value.trim().length > 0;
    if (!replaceConfirmed && (isModified || hasCustomText)) {
      replaceConfirmed = true; cancel.hidden = false; generate.textContent = 'Ganti teks & buat AI';
      feedback.textContent = 'Teks caption saat ini akan diganti oleh AI. Klik sekali lagi untuk melanjutkan, atau pilih Batal.';
      return;
    }
    if (isBusy) return;
    isBusy = true;
    replaceConfirmed = false; cancel.hidden = true; feedback.classList.remove('is-error');
    syncDirtyState();
    generate.textContent = 'Merangkum pembahasan…'; feedback.textContent = 'AI berjalan di laptop; proses pertama bisa lebih lama.';

    try {
      const result = await api('/api/jobs/' + encodeURIComponent(jobId) + '/clips/' + encodeURIComponent(clipId) + '/caption', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({expected_revision: currentRevision})
      });
      Object.assign(clip, result); textarea.value = result.caption; savedCaption = result.caption;
      currentRevision = result.caption_revision || result.metadata_revision || (currentRevision + 1);
      clip.caption_revision = currentRevision;
      clip.metadata_revision = result.metadata_revision || currentRevision;
      updateCharCount(); updateNote(); updateStatus('saved');
      try { localStorage.removeItem(legacyKey); } catch (_) {}
      legacyDraft = null; draftBanner.hidden = true; conflictBanner.hidden = true;
      feedback.textContent = 'Caption dibuat dari pembahasan klip oleh AI lokal. Tinjau sebelum posting.';
    } catch (error) {
      if (error.data && error.data.conflict) {
        feedback.textContent = error.message;
      } else {
        feedback.textContent = error instanceof ConnectionError ? connectionMessage : error.message;
      }
      feedback.classList.add('is-error');
    } finally {
      isBusy = false;
      generate.textContent = 'Buat caption AI lokal';
      syncDirtyState();
    }
  });

  actions.append(saveBtn, copy, saveTxt, generate, cancel);
  box.append(header, statusBadge, draftBanner, conflictBanner, textarea, metaBar, actions, feedback);
  return box;
}
function watermarkEditor(clip, index, jobId) {
  const box = document.createElement('section');
  box.className = 'watermark-editor';
  const clipId = clip.clip_id || String(index);

  const defaultWm = {
    enabled: false,
    type: 'text',
    text: '',
    asset_id: null,
    asset_width: null,
    asset_height: null,
    position: 'top_right',
    width_ratio: 0.15,
    opacity: 0.70,
    margin_ratio: 0.03,
    text_color: 'white',
    text_treatment: 'outline'
  };

  let savedWm = clip.watermark ? JSON.parse(JSON.stringify(clip.watermark)) : JSON.parse(JSON.stringify(defaultWm));
  let currentWm = JSON.parse(JSON.stringify(savedWm));
  let currentRevision = clip.watermark_revision || 1;
  let isBusy = false;
  let currentLogoLoadId = 0;

  const header = document.createElement('div'); header.className = 'watermark-editor-header';
  const titleLabel = document.createElement('label'); titleLabel.textContent = 'Watermark video';
  const toggleWrap = document.createElement('label'); toggleWrap.className = 'watermark-toggle-wrap';
  const toggleCheckbox = document.createElement('input'); toggleCheckbox.type = 'checkbox';
  toggleCheckbox.checked = Boolean(currentWm.enabled);
  const toggleText = document.createElement('span'); toggleText.textContent = 'Aktifkan watermark';
  toggleWrap.append(toggleCheckbox, toggleText);
  header.append(titleLabel, toggleWrap);

  const statusBadge = document.createElement('div'); statusBadge.className = 'caption-status-badge';
  statusBadge.setAttribute('role', 'status'); statusBadge.setAttribute('aria-live', 'polite');

  const saveBtn = document.createElement('button'); saveBtn.type = 'button'; saveBtn.className = 'btn-save-watermark';
  saveBtn.textContent = 'Simpan watermark'; saveBtn.disabled = true;

  function isDirty() {
    return JSON.stringify(currentWm) !== JSON.stringify(savedWm);
  }

  function syncDirtyState() {
    const dirty = isDirty();
    box.classList.toggle('has-unsaved', dirty);
    saveBtn.disabled = isBusy || !dirty;
  }

  function updateStatus(state, msg) {
    statusBadge.className = 'caption-status-badge state-' + state;
    syncDirtyState();
    if (msg) { statusBadge.textContent = msg; return; }
    if (state === 'saved') {
      if (currentWm.enabled) {
        const typeLabel = currentWm.type === 'logo' ? 'Logo' : 'Teks ("' + (currentWm.text || 'kosong') + '")';
        statusBadge.textContent = '✓ Tersimpan di draft · ' + typeLabel;
      } else {
        statusBadge.textContent = 'Watermark nonaktif';
      }
    } else if (state === 'modified') {
      statusBadge.textContent = '● Perubahan watermark belum disimpan';
    } else if (state === 'saving') {
      statusBadge.textContent = 'Menyimpan watermark ke server…';
    } else if (state === 'conflict') {
      statusBadge.textContent = '⚠ Konflik: Watermark di server telah diperbarui';
    } else if (state === 'error') {
      statusBadge.textContent = '⚠ Gagal menyimpan watermark';
    }
  }

  const conflictBanner = document.createElement('div'); conflictBanner.className = 'caption-conflict-banner'; conflictBanner.hidden = true;

  const body = document.createElement('div'); body.className = 'watermark-body';
  body.hidden = !currentWm.enabled;

  const typeField = document.createElement('div'); typeField.className = 'watermark-field';
  const typeLabel = document.createElement('label'); typeLabel.textContent = 'Tipe watermark';
  const typeSegmented = document.createElement('div'); typeSegmented.className = 'watermark-segmented';
  const btnTypeText = document.createElement('button'); btnTypeText.type = 'button'; btnTypeText.textContent = 'Teks';
  const btnTypeLogo = document.createElement('button'); btnTypeLogo.type = 'button'; btnTypeLogo.textContent = 'Logo (gambar)';
  typeSegmented.append(btnTypeText, btnTypeLogo);
  typeField.append(typeLabel, typeSegmented);

  const textPanel = document.createElement('div'); textPanel.className = 'watermark-field';
  const textInputLabel = document.createElement('label'); textInputLabel.textContent = 'Teks watermark (maks. 60 karakter)';
  const textInput = document.createElement('input'); textInput.type = 'text'; textInput.maxLength = 60;
  textInput.placeholder = 'Tulis nama brand atau @handle…'; textInput.value = currentWm.text || '';

  const textMetaRow = document.createElement('div'); textMetaRow.className = 'watermark-field-row';
  const colorWrap = document.createElement('div');
  const colorLabel = document.createElement('label'); colorLabel.textContent = 'Warna teks';
  const colorSelect = document.createElement('select');
  colorSelect.innerHTML = '<option value="white">Putih</option><option value="black">Hitam</option>';
  colorSelect.value = currentWm.text_color || 'white';
  colorWrap.append(colorLabel, colorSelect);

  const treatWrap = document.createElement('div');
  const treatLabel = document.createElement('label'); treatLabel.textContent = 'Gaya teks';
  const treatSelect = document.createElement('select');
  treatSelect.innerHTML = '<option value="outline">Outline (garis tepi)</option><option value="panel">Panel latar</option><option value="none">Polos</option>';
  treatSelect.value = currentWm.text_treatment || 'outline';
  treatWrap.append(treatLabel, treatSelect);
  textMetaRow.append(colorWrap, treatWrap);
  textPanel.append(textInputLabel, textInput, textMetaRow);

  const logoPanel = document.createElement('div'); logoPanel.className = 'watermark-field'; logoPanel.hidden = true;
  const logoInputLabel = document.createElement('label'); logoInputLabel.textContent = 'Unggah logo (PNG transparan / JPG, maks. 5 MiB)';
  const fileInput = document.createElement('input'); fileInput.type = 'file'; fileInput.accept = '.png,.jpg,.jpeg';
  const uploadFeedback = document.createElement('small'); uploadFeedback.className = 'watermark-note';
  const logoThumbWrap = document.createElement('div'); logoThumbWrap.className = 'watermark-logo-preview'; logoThumbWrap.hidden = !currentWm.asset_id;
  const logoThumb = document.createElement('img'); logoThumb.className = 'watermark-logo-thumb';
  if (currentWm.asset_id) logoThumb.src = '/api/watermark-assets/' + encodeURIComponent(currentWm.asset_id) + '/preview';
  const logoInfo = document.createElement('span'); logoInfo.style.fontSize = '12px'; logoInfo.textContent = currentWm.asset_id ? 'Logo tersimpan' : '';
  logoThumbWrap.append(logoThumb, logoInfo);
  logoPanel.append(logoInputLabel, fileInput, uploadFeedback, logoThumbWrap);

  const posField = document.createElement('div'); posField.className = 'watermark-field';
  const posLabel = document.createElement('label'); posLabel.textContent = 'Posisi overlay (9 anchor)';
  const posGrid = document.createElement('div'); posGrid.className = 'watermark-grid-9';
  const positions = [
    ['top_left', '↖ Kiri'], ['top_center', '↑ Tengah'], ['top_right', '↗ Kanan'],
    ['center_left', '← Kiri'], ['center', '• Tengah'], ['center_right', '→ Kanan'],
    ['bottom_left', '↙ Kiri'], ['bottom_center', '↓ Tengah'], ['bottom_right', '↘ Kanan']
  ];
  const posButtons = {};
  positions.forEach(([pKey, pLabel]) => {
    const btn = document.createElement('button'); btn.type = 'button'; btn.textContent = pLabel;
    btn.dataset.pos = pKey;
    posGrid.append(btn);
    posButtons[pKey] = btn;
    btn.addEventListener('click', () => {
      currentWm.position = pKey;
      syncPositionUI();
      updatePreview();
      updateStatus('modified');
    });
  });
  posField.append(posLabel, posGrid);

  const slidersField = document.createElement('div'); slidersField.className = 'watermark-field';
  const wWrap = document.createElement('div'); wWrap.className = 'watermark-slider-wrap';
  const wLabel = document.createElement('label'); wLabel.textContent = 'Lebar'; wLabel.style.minWidth = '50px';
  const wSlider = document.createElement('input'); wSlider.type = 'range'; wSlider.min = '5'; wSlider.max = '30'; wSlider.step = '1';
  wSlider.value = String(Math.round((currentWm.width_ratio || 0.15) * 100));
  const wVal = document.createElement('span'); wVal.textContent = wSlider.value + '%';
  wWrap.append(wLabel, wSlider, wVal);

  const oWrap = document.createElement('div'); oWrap.className = 'watermark-slider-wrap';
  const oLabel = document.createElement('label'); oLabel.textContent = 'Opasitas'; oLabel.style.minWidth = '50px';
  const oSlider = document.createElement('input'); oSlider.type = 'range'; oSlider.min = '10'; oSlider.max = '100'; oSlider.step = '5';
  oSlider.value = String(Math.round((currentWm.opacity || 0.70) * 100));
  const oVal = document.createElement('span'); oVal.textContent = oSlider.value + '%';
  oWrap.append(oLabel, oSlider, oVal);

  const mWrap = document.createElement('div'); mWrap.className = 'watermark-slider-wrap';
  const mLabel = document.createElement('label'); mLabel.textContent = 'Margin'; mLabel.style.minWidth = '50px';
  const mSlider = document.createElement('input'); mSlider.type = 'range'; mSlider.min = '0'; mSlider.max = '10'; mSlider.step = '1';
  mSlider.value = String(Math.round((currentWm.margin_ratio || 0.03) * 100));
  const mVal = document.createElement('span'); mVal.textContent = mSlider.value + '%';
  mWrap.append(mLabel, mSlider, mVal);
  slidersField.append(wWrap, oWrap, mWrap);

  const previewArea = document.createElement('div'); previewArea.className = 'watermark-preview-area';
  const previewCanvas = document.createElement('div'); previewCanvas.className = 'watermark-preview-canvas';
  const previewOverlay = document.createElement('div'); previewOverlay.className = 'watermark-preview-overlay';
  const previewSubtitleZone = document.createElement('div'); previewSubtitleZone.className = 'watermark-preview-subtitle-zone';
  previewSubtitleZone.textContent = 'Area Subtitle (bawah)';
  previewCanvas.append(previewOverlay, previewSubtitleZone);

  const previewSide = document.createElement('div'); previewSide.style.flex = '1';
  const clashWarning = document.createElement('div'); clashWarning.className = 'watermark-clash-warning'; clashWarning.hidden = true;
  clashWarning.textContent = '⚠ Perhatian: Posisi bawah berpotensi menutupi teks subtitle video.';
  const previewNote = document.createElement('p'); previewNote.className = 'watermark-note';
  previewNote.textContent = 'Ilustrasi preview 9:16. Posisi dan skala dinormalisasi otomatis pada kanvas ekspor (480p / 720p / 1080p).';
  previewSide.append(clashWarning, previewNote);
  previewArea.append(previewCanvas, previewSide);

  const presetField = document.createElement('div'); presetField.className = 'watermark-field';
  const presetLabel = document.createElement('label'); presetLabel.textContent = 'Preset watermark lokal';
  const presetRow = document.createElement('div'); presetRow.className = 'watermark-actions';
  const presetSelect = document.createElement('select'); presetSelect.style.flex = '1';
  presetSelect.innerHTML = '<option value="">-- Pilih preset tersimpan --</option>';
  const btnApplyPreset = document.createElement('button'); btnApplyPreset.type = 'button'; btnApplyPreset.textContent = 'Pakai preset';
  const btnSavePreset = document.createElement('button'); btnSavePreset.type = 'button'; btnSavePreset.textContent = 'Simpan preset baru';
  presetRow.append(presetSelect, btnApplyPreset, btnSavePreset);
  presetField.append(presetLabel, presetRow);

  const actions = document.createElement('div'); actions.className = 'watermark-actions';
  const feedback = document.createElement('span'); feedback.className = 'caption-feedback'; feedback.setAttribute('role', 'status');
  actions.append(saveBtn, feedback);

  const exportNote = document.createElement('p'); exportNote.className = 'watermark-note';
  exportNote.textContent = 'Simpan draft lalu gunakan Ekspor MP4 watermark di bawah. Hasil baru terpisah dari MP4 awal; audio dan subtitle yang sudah ada dipertahankan.';

  function syncTypeUI() {
    const isLogo = currentWm.type === 'logo';
    btnTypeText.classList.toggle('active', !isLogo);
    btnTypeLogo.classList.toggle('active', isLogo);
    textPanel.hidden = isLogo;
    logoPanel.hidden = !isLogo;
  }

  function syncPositionUI() {
    const pos = currentWm.position || 'top_right';
    for (const [k, btn] of Object.entries(posButtons)) {
      btn.classList.toggle('active', k === pos);
    }
  }

  function syncAllControlsFromConfig(cfg) {
    if (!cfg) return;
    currentWm = JSON.parse(JSON.stringify(cfg));
    toggleCheckbox.checked = Boolean(currentWm.enabled);
    body.hidden = !currentWm.enabled;
    textInput.value = currentWm.text ?? '';
    colorSelect.value = currentWm.text_color ?? 'white';
    treatSelect.value = currentWm.text_treatment ?? 'outline';

    const wValNum = Math.round(((currentWm.width_ratio ?? 0.15)) * 100);
    wSlider.value = String(wValNum);
    wVal.textContent = wValNum + '%';

    const oValNum = Math.round(((currentWm.opacity ?? 0.70)) * 100);
    oSlider.value = String(oValNum);
    oVal.textContent = oValNum + '%';

    const mValNum = Math.round(((currentWm.margin_ratio ?? 0.03)) * 100);
    mSlider.value = String(mValNum);
    mVal.textContent = mValNum + '%';

    syncTypeUI();
    syncPositionUI();

    if (currentWm.type === 'logo' && currentWm.asset_id) {
      logoThumb.src = '/api/watermark-assets/' + encodeURIComponent(currentWm.asset_id) + '/preview';
      logoThumbWrap.hidden = false;
      if (currentWm.asset_width && currentWm.asset_height) {
        logoInfo.textContent = 'Logo (' + currentWm.asset_width + '×' + currentWm.asset_height + 'px)';
      } else {
        logoInfo.textContent = 'Logo tersimpan';
      }
    } else {
      logoThumbWrap.hidden = true;
      logoThumb.src = '';
      logoInfo.textContent = '';
    }
    uploadFeedback.textContent = '';
    updatePreview();
  }

  function checkClashForGeometry(pos, marginPx, targetW, targetH) {
    let ox = 0;
    if (pos.endsWith('left')) ox = marginPx;
    else if (pos.endsWith('right')) ox = 140 - targetW - marginPx;
    else ox = Math.round((140 - targetW) / 2);

    let oy = 0;
    if (pos.startsWith('top')) oy = marginPx;
    else if (pos.startsWith('bottom')) oy = 248 - targetH - marginPx;
    else oy = Math.round((248 - targetH) / 2);

    const subX1 = 7, subX2 = 133, subY1 = 178, subY2 = 248;
    const overlapW = Math.max(0, Math.min(ox + targetW, subX2) - Math.max(ox, subX1));
    const overlapH = Math.max(0, Math.min(oy + targetH, subY2) - Math.max(oy, subY1));
    clashWarning.hidden = !(overlapW > 0 && overlapH > 0);
  }

  function updatePreview() {
    if (!currentWm.enabled) {
      previewCanvas.hidden = true;
      clashWarning.hidden = true;
      return;
    }
    previewCanvas.hidden = false;

    const marginRatio = currentWm.margin_ratio ?? 0.03;
    const widthRatio = currentWm.width_ratio ?? 0.15;
    const opacityVal = currentWm.opacity ?? 0.70;
    const pos = currentWm.position || 'top_right';

    // Canvas preview: 140px width x 248px height (dimensi terpendek = 140px)
    const shortestDim = 140;
    const marginPx = Math.round(marginRatio * shortestDim);
    const targetW = Math.max(8, Math.round(widthRatio * 140));

    previewOverlay.style.opacity = opacityVal;
    previewOverlay.style.width = targetW + 'px';
    previewOverlay.style.maxWidth = '';

    // Vertikal
    if (pos.startsWith('top')) {
      previewOverlay.style.top = marginPx + 'px';
      previewOverlay.style.bottom = '';
    } else if (pos.startsWith('bottom')) {
      previewOverlay.style.top = '';
      previewOverlay.style.bottom = marginPx + 'px';
    } else {
      // center_left, center, center_right
      previewOverlay.style.top = '50%';
      previewOverlay.style.bottom = '';
    }

    // Horizontal
    if (pos.endsWith('left')) {
      previewOverlay.style.left = marginPx + 'px';
      previewOverlay.style.right = '';
    } else if (pos.endsWith('right')) {
      previewOverlay.style.left = '';
      previewOverlay.style.right = marginPx + 'px';
    } else {
      // top_center, center, bottom_center
      previewOverlay.style.left = '50%';
      previewOverlay.style.right = '';
    }

    // Transform offset
    if (pos === 'center') {
      previewOverlay.style.transform = 'translate(-50%, -50%)';
    } else if (pos === 'top_center' || pos === 'bottom_center') {
      previewOverlay.style.transform = 'translateX(-50%)';
    } else if (pos === 'center_left' || pos === 'center_right') {
      previewOverlay.style.transform = 'translateY(-50%)';
    } else {
      previewOverlay.style.transform = 'none';
    }

    let targetH = 14;
    if (currentWm.type === 'logo' && currentWm.asset_id) {
      const activeAssetId = currentWm.asset_id;
      const loadId = ++currentLogoLoadId;
      previewOverlay.replaceChildren();
      const img = document.createElement('img');
      img.src = '/api/watermark-assets/' + encodeURIComponent(activeAssetId) + '/preview';
      img.style.width = '100%';
      img.style.display = 'block';

      if (currentWm.asset_width && currentWm.asset_height) {
        const aspect = currentWm.asset_height / currentWm.asset_width;
        targetH = Math.max(8, Math.round(targetW * aspect));
      }

      img.onload = () => {
        if (loadId !== currentLogoLoadId || currentWm.type !== 'logo' || currentWm.asset_id !== activeAssetId) return;
        if (img.naturalWidth && img.naturalHeight) {
          currentWm.asset_width = img.naturalWidth;
          currentWm.asset_height = img.naturalHeight;
          if (logoInfo && (!logoInfo.textContent || logoInfo.textContent === 'Logo tersimpan')) {
            logoInfo.textContent = 'Logo (' + img.naturalWidth + '×' + img.naturalHeight + 'px)';
          }
          const naturalAspect = img.naturalHeight / img.naturalWidth;
          const realH = Math.max(8, Math.round(targetW * naturalAspect));
          checkClashForGeometry(pos, marginPx, targetW, realH);
        }
      };
      img.onerror = () => {
        if (loadId !== currentLogoLoadId || currentWm.asset_id !== activeAssetId) return;
        uploadFeedback.textContent = '⚠ Gagal memuat pratinjau gambar logo.';
        uploadFeedback.style.color = '#c0392b';
      };

      previewOverlay.appendChild(img);
    } else {
      previewOverlay.replaceChildren();
      const span = document.createElement('span');
      span.textContent = currentWm.text || 'Watermark';
      span.style.fontFamily = 'Arial, sans-serif';
      span.style.fontWeight = 'bold';
      const textLen = Math.max(1, (currentWm.text || 'Watermark').length);
      const fontSize = Math.max(7, Math.min(13, Math.floor((targetW / Math.max(4, textLen)) * 1.5)));
      span.style.fontSize = fontSize + 'px';
      span.style.color = currentWm.text_color === 'black' ? '#000' : '#fff';
      if (currentWm.text_treatment === 'outline') {
        const outCol = currentWm.text_color === 'black' ? '#fff' : '#000';
        span.style.textShadow = '1px 1px 0 ' + outCol + ', -1px -1px 0 ' + outCol + ', 1px -1px 0 ' + outCol + ', -1px 1px 0 ' + outCol;
      } else if (currentWm.text_treatment === 'panel') {
        span.style.background = currentWm.text_color === 'black' ? 'rgba(255,255,255,0.7)' : 'rgba(0,0,0,0.6)';
        span.style.padding = '2px 4px';
        span.style.borderRadius = '3px';
      }
      previewOverlay.appendChild(span);
      targetH = Math.max(10, Math.round(fontSize * 1.4));
    }

    checkClashForGeometry(pos, marginPx, targetW, targetH);
  }

  toggleCheckbox.addEventListener('change', () => {
    currentWm.enabled = toggleCheckbox.checked;
    body.hidden = !currentWm.enabled;
    updatePreview();
    updateStatus('modified');
  });

  btnTypeText.addEventListener('click', () => {
    currentWm.type = 'text';
    syncTypeUI();
    updatePreview();
    updateStatus('modified');
  });

  btnTypeLogo.addEventListener('click', () => {
    currentWm.type = 'logo';
    syncTypeUI();
    updatePreview();
    updateStatus('modified');
  });

  textInput.addEventListener('input', () => {
    currentWm.text = textInput.value;
    updatePreview();
    updateStatus('modified');
  });

  colorSelect.addEventListener('change', () => {
    currentWm.text_color = colorSelect.value;
    updatePreview();
    updateStatus('modified');
  });

  treatSelect.addEventListener('change', () => {
    currentWm.text_treatment = treatSelect.value;
    updatePreview();
    updateStatus('modified');
  });

  wSlider.addEventListener('input', () => {
    wVal.textContent = wSlider.value + '%';
    currentWm.width_ratio = Number(wSlider.value) / 100;
    updatePreview();
    updateStatus('modified');
  });

  oSlider.addEventListener('input', () => {
    oVal.textContent = oSlider.value + '%';
    currentWm.opacity = Number(oSlider.value) / 100;
    updatePreview();
    updateStatus('modified');
  });

  mSlider.addEventListener('input', () => {
    mVal.textContent = mSlider.value + '%';
    currentWm.margin_ratio = Number(mSlider.value) / 100;
    updatePreview();
    updateStatus('modified');
  });

  fileInput.addEventListener('change', async () => {
    if (!fileInput.files || !fileInput.files[0]) return;
    const file = fileInput.files[0];
    if (file.size > 5 * 1024 * 1024) {
      uploadFeedback.textContent = '⚠ Ukuran file melebihi batas 5 MiB.';
      uploadFeedback.style.color = '#c0392b';
      return;
    }
    uploadFeedback.textContent = 'Mengunggah dan menormalisasi logo…';
    uploadFeedback.style.color = '#556247';
    const fd = new FormData();
    fd.append('file', file);
    try {
      const res = await api('/api/watermark-assets', { method: 'POST', body: fd });
      currentWm.asset_id = res.asset_id;
      currentWm.asset_width = res.width;
      currentWm.asset_height = res.height;
      logoThumb.src = '/api/watermark-assets/' + encodeURIComponent(res.asset_id) + '/preview';
      logoThumbWrap.hidden = false;
      logoInfo.textContent = res.image_format.toUpperCase() + ' (' + res.width + '×' + res.height + 'px)';
      uploadFeedback.textContent = res.image_format === 'jpg' ? '✓ Logo JPG diunggah (tanpa transparansi bawaan).' : '✓ Logo PNG transparan diunggah.';
      uploadFeedback.style.color = '#27ae60';
      updatePreview();
      updateStatus('modified');
    } catch (err) {
      uploadFeedback.textContent = '⚠ ' + (err.message || 'Gagal mengunggah logo.');
      uploadFeedback.style.color = '#c0392b';
    }
  });

  async function loadPresetList() {
    try {
      const data = await api('/api/watermark-presets');
      presetSelect.innerHTML = '<option value="">-- Pilih preset tersimpan --</option>';
      (data.presets || []).forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.preset_id;
        opt.textContent = p.name;
        opt.dataset.config = JSON.stringify(p.configuration);
        presetSelect.appendChild(opt);
      });
    } catch (_) {}
  }
  loadPresetList();

  btnApplyPreset.addEventListener('click', () => {
    const sel = presetSelect.selectedOptions[0];
    if (!sel || !sel.dataset.config) return;
    try {
      const cfg = JSON.parse(sel.dataset.config);
      syncAllControlsFromConfig(cfg);
      updateStatus('modified');
      feedback.textContent = 'Preset "' + sel.textContent + '" diterapkan ke draft.';
    } catch (_) {}
  });

  btnSavePreset.addEventListener('click', async () => {
    const name = window.prompt('Masukkan nama preset watermark baru:', 'Preset ' + (currentWm.type === 'logo' ? 'Logo' : currentWm.text || 'Klip'));
    if (!name || !name.trim()) return;
    try {
      await api('/api/watermark-presets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim(), configuration: currentWm })
      });
      await loadPresetList();
      feedback.textContent = 'Preset baru berhasil disimpan.';
    } catch (err) {
      feedback.textContent = 'Gagal menyimpan preset: ' + err.message;
    }
  });

  saveBtn.addEventListener('click', async () => {
    if (isBusy || !isDirty()) return;
    isBusy = true;
    syncDirtyState();
    updateStatus('saving');
    feedback.textContent = ''; feedback.classList.remove('is-error');

    try {
      const res = await api('/api/jobs/' + encodeURIComponent(jobId) + '/clips/' + encodeURIComponent(clipId) + '/watermark', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ watermark: currentWm, expected_revision: currentRevision })
      });
      clip.watermark = res.watermark;
      currentRevision = res.watermark_revision || (currentRevision + 1);
      clip.watermark_revision = currentRevision;
      savedWm = JSON.parse(JSON.stringify(res.watermark));
      conflictBanner.hidden = true;
      syncAllControlsFromConfig(res.watermark);
      updateStatus('saved');
      if (res.clash_detected) {
        clashWarning.hidden = false;
        if (res.clash_message) clashWarning.textContent = '⚠ ' + res.clash_message;
      }
      feedback.textContent = 'Pengaturan watermark tersimpan di draft klip.';
    } catch (err) {
      if (err.data && err.data.conflict) {
        updateStatus('conflict');
        showConflictUI(err.data);
      } else {
        updateStatus('error');
        feedback.textContent = err.message || 'Gagal menyimpan watermark.';
        feedback.classList.add('is-error');
      }
    } finally {
      isBusy = false;
      syncDirtyState();
    }
  });

  function showConflictUI(data) {
    conflictBanner.replaceChildren(); conflictBanner.hidden = false;
    const msg = document.createElement('p');
    msg.textContent = 'Konflik revisi: Watermark di server telah diperbarui oleh sesi lain. Perubahanmu tetap tersimpan di form.';
    const actionsDiv = document.createElement('div'); actionsDiv.className = 'conflict-banner-actions';
    const loadServerBtn = document.createElement('button'); loadServerBtn.type = 'button';
    loadServerBtn.textContent = 'Pakai versi server';
    loadServerBtn.addEventListener('click', () => {
      if (data.server_watermark) {
        savedWm = JSON.parse(JSON.stringify(data.server_watermark));
        syncAllControlsFromConfig(data.server_watermark);
      }
      currentRevision = data.current_revision;
      clip.watermark_revision = currentRevision;
      conflictBanner.hidden = true;
      updateStatus('saved');
      feedback.textContent = 'Versi server dimuat ke form.';
    });
    const overwriteBtn = document.createElement('button'); overwriteBtn.type = 'button';
    overwriteBtn.textContent = 'Timpa dengan konfigurasi ini';
    overwriteBtn.addEventListener('click', () => {
      currentRevision = data.current_revision;
      conflictBanner.hidden = true;
      saveBtn.click();
    });
    actionsDiv.append(loadServerBtn, overwriteBtn);
    conflictBanner.append(msg, actionsDiv);
  }

  syncAllControlsFromConfig(currentWm);
  updateStatus('saved');

  body.append(typeField, textPanel, logoPanel, posField, slidersField, previewArea, presetField);
  box.append(header, statusBadge, conflictBanner, body, actions, exportNote);
  return box;
}
function clipOutputTools(clip, job) {
  const box = document.createElement('section'); box.className = 'clip-output-tools';
  const title = document.createElement('h3'); title.textContent = 'Tinjau & ekspor versi baru';
  const note = document.createElement('p'); note.textContent = 'Tinjau video, edit caption dan simpan watermark di atas. Trim/subtitle manual belum tersedia. Thumbnail dibuat dari frame klip ini; tanpa ilustrasi atau judul buatan.';
  const frameLabel = document.createElement('label'); frameLabel.textContent = 'Waktu frame thumbnail (detik dalam klip)';
  const frame = document.createElement('input'); frame.type = 'number'; frame.min = '0'; frame.step = '0.1'; frame.value = '0';
  frameLabel.append(frame);
  const ratioLabel = document.createElement('label'); ratioLabel.textContent = 'Rasio thumbnail';
  const ratio = document.createElement('select');
  for (const [value, text] of [['vertical', 'Cover 9:16 · 1080 × 1920'], ['landscape', 'Thumbnail 16:9 · 1280 × 720']]) {
    const option = document.createElement('option'); option.value = value; option.textContent = text; ratio.append(option);
  }
  ratioLabel.append(ratio);
  const actions = document.createElement('div'); actions.className = 'watermark-actions';
  const video = document.createElement('button'); video.type = 'button'; video.textContent = 'Ekspor MP4 watermark';
  const image = document.createElement('button'); image.type = 'button'; image.textContent = 'Buat thumbnail PNG';
  const status = document.createElement('p'); status.setAttribute('role', 'status');
  const list = document.createElement('div'); list.className = 'clip-export-list';
  let busy = false;
  const base = '/api/jobs/' + encodeURIComponent(job.id) + '/clips/' + encodeURIComponent(clip.clip_id);
  function showRecord(record) {
    let row = [...list.children].find(el => el.dataset.exportId === record.export_id);
    if (!row) { row = document.createElement('div'); row.dataset.exportId = record.export_id; list.prepend(row); }
    row.replaceChildren();
    const label = document.createElement('span'); label.textContent = (record.kind === 'video' ? 'MP4 watermark' : 'Thumbnail PNG') + ' · ' + new Date(record.created_at).toLocaleString('id-ID') + ' · ';
    row.append(label);
    if (record.status === 'done') {
      const link = document.createElement('a'); link.href = base + '/exports/' + record.export_id + '/file?download=1'; link.textContent = 'Unduh hasil'; row.append(link);
      if (record.kind === 'thumbnail') {
        const preview = document.createElement('img'); preview.src = base + '/exports/' + record.export_id + '/file'; preview.alt = 'Thumbnail dari frame klip'; row.append(preview);
      }
    } else row.append(document.createTextNode(record.status === 'failed' ? 'Gagal: ' + record.error : 'Sedang mengekspor…'));
  }
  async function follow(record) {
    showRecord(record);
    while (record.status === 'running') {
      await new Promise(resolve => setTimeout(resolve, 1200));
      if (!box.isConnected) return;
      record = (await api(base + '/exports/' + record.export_id)).export;
      showRecord(record);
    }
  }
  async function start(kind) {
    if (busy) return;
    if (box.closest('.clip')?.querySelector('.watermark-editor.has-unsaved')) { status.textContent = 'Simpan draft watermark terlebih dahulu.'; return; }
    const time = Number(frame.value);
    if (!Number.isFinite(time) || time < 0) { status.textContent = 'Isi waktu frame yang valid.'; return; }
    busy = true; video.disabled = image.disabled = true; status.textContent = 'Menyiapkan ekspor lokal…';
    try {
      const result = await api(base + '/exports', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({
        request_id:crypto.randomUUID().replaceAll('-', ''), kind, frame_time:kind === 'thumbnail' ? time : 0,
        ratio:ratio.value, expected_watermark_revision:clip.watermark_revision || 1
      })});
      await follow(result.export);
      status.textContent = 'Status ekspor diperbarui. Hasil awal tetap tersedia.';
    } catch (error) { status.textContent = error.message; }
    finally { busy = false; video.disabled = image.disabled = false; }
  }
  video.addEventListener('click', () => start('video')); image.addEventListener('click', () => start('thumbnail'));
  actions.append(video, image); box.append(title, note, frameLabel, ratioLabel, actions, status, list);
  for (const record of Object.values(clip.exports || {})) {
    if (record.status === 'running') follow(record).catch(error => { status.textContent = error.message; });
    else showRecord(record);
  }
  if (job.content_profile === 'kids') {
    const publishing = document.createElement('p'); publishing.textContent = 'Sebelum publikasi, tinjau kesesuaian usia, hak aset dan pengaturan audience YouTube. Aplikasi tidak mengunggah atau mengubah akun.';
    const help = document.createElement('a'); help.href = 'https://support.google.com/youtube/answer/9527654?hl=id'; help.target = '_blank'; help.rel = 'noopener noreferrer'; help.textContent = 'Panduan audience Made for Kids';
    box.append(publishing, help);
  }
  return box;
}

function render(job) {
  const resultsNote = document.querySelector('#results-note') || document.querySelector('#results .results-head p');
  if (resultsNote) resultsNote.textContent = job.content_profile === 'kids' ? 'Kandidat untuk ditinjau · Anak 3–5 · Indonesia. Tujuan brief: ' + (job.kids_metadata?.brief_snapshot?.learning_goal || 'Tinjau konsep pembelajaran') + '. Label ini bukan sertifikasi kesesuaian usia.' : job.audience === 'global_en' ? 'Subtitle dan caption: English · suara asli dipertahankan. Tinjau terjemahan dan konteks sebelum posting.' : 'Pilihan berdasarkan transkrip, bukan jaminan viral. Tinjau framing dan batas ucapan sebelum posting.';
  document.querySelector('#results').hidden = location.hash === '#history' || !job.clips?.length;
  document.querySelector('#result-title').textContent = job.title || 'Klip siap ditinjau';
  const grid = document.querySelector('#clips');
  grid.replaceChildren();
  (job.clips || []).forEach((c, i) => {
    const card = document.createElement('article'); card.className = 'clip';
    const video = document.createElement('video'); video.controls = true; video.preload = 'metadata'; video.src = c.url;
    const heading = document.createElement('h3'); heading.textContent = 'Klip ' + String(i+1).padStart(2, '0');
    const time = document.createElement('span'); time.className = 'time'; time.textContent = formatTime(c.start) + ' — ' + formatTime(c.end) + ' di video asli';
    const text = document.createElement('p'); text.textContent = c.text;
    const download = document.createElement('a'); download.className = 'download'; download.href = c.url + '?download=1'; download.textContent = 'Unduh MP4 ↓';
    const framing = document.createElement('small'); framing.className = 'framing-note'; framing.textContent = c.framing?.note || 'Hasil lama · crop tengah';
    card.append(video, heading, time, framing, text, download, captionEditor(c, i, job.id, job.audience), watermarkEditor(c, i, job.id), clipOutputTools(c, job)); grid.append(card);
  });
}
function display(job) {
  const progEl = document.querySelector('#progress');
  if (progEl) progEl.hidden = false;
  if (statusEl) statusEl.textContent = job.status;
  const percEl = document.querySelector('#percent');
  if (percEl) percEl.textContent = (job.progress || 0) + '%';
  const barEl = document.querySelector('#bar');
  if (barEl) barEl.style.width = (job.progress || 0) + '%';
  if (errorEl) errorEl.textContent = job.error || '';
  render(job);
}
function selectHistoryRow() {
  for (const row of historyList.querySelectorAll('.history-row')) {
    const selected = row.dataset.id === selectedJobId;
    row.classList.toggle('selected', selected);
    row.setAttribute('aria-pressed', String(selected));
  }
}
function renderHistory(jobs) {
  historyList.replaceChildren();
  document.querySelector('#history-count').textContent = historyState.total;
  const start = historyState.filtered ? (historyState.page-1)*10+1 : 0;
  document.querySelector('#history-range').textContent = start + '–' + Math.min(historyState.page*10, historyState.filtered) + ' dari ' + historyState.filtered + ' video';
  document.querySelector('#history-page').textContent = historyState.page + ' / ' + historyState.pages;
  document.querySelector('#history-prev').disabled = historyState.page <= 1;
  document.querySelector('#history-next').disabled = historyState.page >= historyState.pages;
  for (const filter of historyTools.querySelectorAll('[data-status]')) filter.setAttribute('aria-pressed', String(filter.dataset.status === historyState.status));
  historyMessage.textContent = jobs.length ? 'Pilih video untuk membuka kembali hasilnya. Hasil lama tetap tersimpan saat kamu membuat klip baru.' : (historyState.total ? 'Tidak ada video yang cocok dengan pencarian atau filter ini.' : 'Belum ada riwayat. Video yang kamu proses akan tersimpan di sini.');
  for (const job of jobs) {
    const row = document.createElement('button'); row.type = 'button'; row.className = 'history-row'; row.dataset.id = job.id;
    const icon = document.createElement('span'); icon.className = 'history-icon'; icon.textContent = job.source_url ? '↗' : '▯';
    const content = document.createElement('span'); content.className = 'history-content';
    const title = document.createElement('strong'); title.textContent = job.title || job.source_name || 'Video sebelumnya';
    const meta = document.createElement('small');
    const date = new Date(job.created_at);
    meta.textContent = (Number.isNaN(date.getTime()) ? '' : date.toLocaleString('id-ID', {dateStyle:'medium', timeStyle:'short'})) + ' · ' + job.clip_count + ' klip · ' + (job.resolution || '720') + 'p';
    if (job.source_url) meta.textContent += ' · ' + job.source_url;
    if (job.content_profile === 'kids') meta.textContent = 'Anak · 3–5 · ' + meta.textContent;
    content.append(title, meta);
    const state = document.createElement('span'); state.className = 'history-state';
    state.textContent = !job.done ? 'Diproses' : job.error ? 'Gagal' : 'Selesai';
    if (!job.done) state.classList.add('processing');
    if (job.error) state.classList.add('failed');
    row.append(icon, content, state); row.addEventListener('click', () => openJob(job.id));
    const item = document.createElement('div'); item.className = 'history-item';
    const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'history-delete'; remove.textContent = 'Hapus';
    remove.setAttribute('aria-label', 'Hapus riwayat ' + (job.title || 'video'));
    remove.disabled = !job.done;
    remove.title = job.done ? 'Hapus riwayat dan semua berkas video ini dari disk' : 'Tunggu pemrosesan selesai sebelum menghapus';
    remove.addEventListener('click', () => deleteJob(job, remove));
    item.append(row, remove); historyList.append(item);
  }
  selectHistoryRow();
}
// One app-themed confirmation; opening/cancelling never sends a DELETE.
let deleteDialog, finishDeleteConfirmation;
function confirmHistoryDelete(job) {
  if (!deleteDialog) {
    deleteDialog = document.createElement('dialog');
    deleteDialog.className = 'delete-dialog';
    deleteDialog.setAttribute('role', 'alertdialog');
    deleteDialog.setAttribute('aria-labelledby', 'delete-dialog-title');
    deleteDialog.setAttribute('aria-describedby', 'delete-dialog-description delete-dialog-video delete-dialog-warning');
    deleteDialog.innerHTML = `<button type="button" class="delete-dialog-close" aria-label="Tutup konfirmasi hapus">×</button>
      <div class="delete-dialog-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M9 6V4h6v2M5 6l1 14h12l1-14M10 10v6M14 10v6"/></svg></div>
      <div class="eyebrow">KELOLA PENYIMPANAN</div><h2 id="delete-dialog-title">Hapus riwayat klip?</h2>
      <p id="delete-dialog-description">Video sumber, audio, transkrip, subtitle, dan semua hasil klip dari pekerjaan ini akan dihapus dari laptop.</p>
      <div class="delete-dialog-target"><span>VIDEO YANG AKAN DIHAPUS</span><strong id="delete-dialog-video"></strong><small id="delete-dialog-count"></small></div>
      <p id="delete-dialog-warning" class="delete-dialog-warning">Penghapusan ini permanen dan tidak bisa dibatalkan.</p>
      <p class="delete-dialog-note">Cache model tetap tersimpan. Salinan yang sudah kamu unduh ke folder lain tidak ikut dihapus.</p>
      <div class="delete-dialog-actions"><button type="button" class="delete-dialog-cancel" autofocus>Batal</button><button type="button" class="delete-dialog-confirm">Hapus permanen</button></div>`;
    document.body.append(deleteDialog);
    const settle = confirmed => {
      if (!deleteDialog.open) return;
      const resolve = finishDeleteConfirmation; finishDeleteConfirmation = null;
      deleteDialog.close(); document.body.classList.remove('delete-dialog-open');
      resolve?.(confirmed);
    };
    deleteDialog.querySelector('.delete-dialog-cancel').addEventListener('click', () => settle(false));
    deleteDialog.querySelector('.delete-dialog-close').addEventListener('click', () => settle(false));
    deleteDialog.querySelector('.delete-dialog-confirm').addEventListener('click', () => settle(true));
    deleteDialog.addEventListener('cancel', event => { event.preventDefault(); settle(false); });
    deleteDialog.addEventListener('click', event => {
      const box = deleteDialog.getBoundingClientRect();
      if (event.target === deleteDialog && (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom)) settle(false);
    });
    deleteDialog.addEventListener('close', () => {
      if (deleteDialog.open) return;
      document.body.classList.remove('delete-dialog-open');
      if (finishDeleteConfirmation) { const resolve = finishDeleteConfirmation; finishDeleteConfirmation = null; resolve(false); }
    });
  }
  if (deleteDialog.open) return Promise.resolve(false);
  deleteDialog.querySelector('#delete-dialog-video').textContent = job.title || 'Video tanpa judul';
  const count = job.clip_count ?? job.clips?.length ?? 0;
  deleteDialog.querySelector('#delete-dialog-count').textContent = count + ' hasil klip · seluruh berkas pekerjaan';
  return new Promise(resolve => {
    finishDeleteConfirmation = resolve;
    document.body.classList.add('delete-dialog-open');
    deleteDialog.showModal();
    deleteDialog.querySelector('.delete-dialog-cancel').focus();
  });
}
async function deleteJob(job, remove) {
  if (!job.done || !await confirmHistoryDelete(job)) return;
  remove.disabled = true; remove.textContent = '…'; remove.setAttribute('aria-busy','true');
  historyMessage.textContent = 'Menghapus riwayat dan berkas pekerjaan…';
  try {
    await api('/api/jobs/' + encodeURIComponent(job.id), {method:'DELETE'});
    try {
      for (const key of Object.keys(localStorage)) if (key.startsWith('klip-caption:/files/' + job.id + '/')) localStorage.removeItem(key);
    } catch (_) {}
    if (selectedJobId === job.id) {
      ++selectionVersion; selectedJobId = null; remember(null);
      document.querySelector('#results').hidden = true;
      document.querySelector('#clips').replaceChildren();
      document.querySelector('#progress').hidden = true;
      errorEl.textContent = '';
    }
    const remaining = await refreshHistory();
    if (location.hash !== '#history' && !selectedJobId && remaining.length) await openJob(activeJobId || remaining[0].id);
    historyMessage.textContent = 'Riwayat dan semua berkas pekerjaan berhasil dihapus dari disk.';
  } catch (error) {
    remove.disabled = false;
    historyMessage.textContent = error instanceof ConnectionError ? connectionMessage : error.message;
  } finally {
    if (remove.isConnected) { remove.textContent = 'Hapus'; remove.removeAttribute('aria-busy'); }
  }
}
async function refreshHistory() {
  const version = ++historyVersion;
  const params = new URLSearchParams({page:historyState.page, page_size:10, q:historyState.query, status:historyState.status});
  let data = await api('/api/jobs?' + params);
  if (version !== historyVersion) return [];
  // Compatibility while an older server is completing an existing video.
  if (!Number.isInteger(data.total)) {
    const all = data.jobs;
    const filtered = all.filter(job => {
      const category = !job.done ? 'processing' : job.error ? 'failed' : 'done';
      return (historyState.status === 'all' || historyState.status === category) &&
        [job.title, job.source_url, job.source_name].join(' ').toLocaleLowerCase().includes(historyState.query.toLocaleLowerCase());
    });
    const pages = Math.max(1, Math.ceil(filtered.length/10));
    const page = Math.min(historyState.page, pages);
    data = {jobs:filtered.slice((page-1)*10, page*10), total:all.length, filtered_total:filtered.length, total_pages:pages, page, active_job_id:all.find(job => !job.done)?.id};
  }
  Object.assign(historyState, {total:data.total, filtered:data.filtered_total, pages:data.total_pages, page:data.page, activeId:data.active_job_id});
  renderHistory(data.jobs); return data.jobs;
}
async function openJob(id) {
  if (selectedJobId && selectedJobId !== id && hasUnsavedCaptionEdits()) {
    if (!window.confirm('Ada perubahan caption yang belum disimpan ke server. Tetap pindah video tanpa menyimpan?')) return;
  }
  if (location.hash === '#history') { history.replaceState(null, '', location.pathname + location.search); syncView(); window.scrollTo(0, 0); }
  const version = ++selectionVersion;
  selectedJobId = id; remember(id); selectHistoryRow();
  if (mobileWidth.matches && document.body.classList.contains('sidebar-open')) setSidebar(false);
  try {
    const job = await api('/api/jobs/' + encodeURIComponent(id));
    if (version !== selectionVersion) return;
    const kidsSourceForm = form?.elements.content_profile?.value === 'kids';
    const matchesBrief = !kidsSourceForm || (job.content_profile === 'kids' &&
      job.kids_metadata?.brief_id === form.elements.brief_id.value);
    const matchesForm = form && matchesBrief;
    const urlInput = document.querySelector('#url');
    if (urlInput && matchesForm) urlInput.value = job.source_url || '';
    const vidInput = document.querySelector('#video');
    if (vidInput && matchesForm) vidInput.value = '';
    const uplLabel = document.querySelector('#upload-label');
    if (uplLabel && matchesForm) uplLabel.textContent = '＋ Pilih file video';
    if (matchesForm) {
      for (const key of ['duration', 'count', 'language']) {
        if (key === 'language' && kidsSourceForm) form.elements.language.value = 'id';
        else if (job[key] != null) form.elements[key].value = job[key];
      }
      form.elements.resolution.value = job.resolution || '720';
      form.elements.subtitle_style.value = job.subtitle_style || 'classic';
      if (form.elements.topic) form.elements.topic.value = job.topic || 'general';
      syncFormat();
    }
    display(job);
    if (!job.done && !activeJobId) { activeJobId = id; if (button) button.disabled = true; poll(id); }
  } catch (error) { if (version === selectionVersion) showError(error instanceof ConnectionError ? connectionMessage : 'Hasil belum dapat ditampilkan: ' + error.message); }
}
async function poll(id) {
  let job;
  try { job = await api('/api/jobs/' + encodeURIComponent(id)); }
  catch (error) {
    if (selectedJobId === id) showError(error instanceof ConnectionError ? connectionMessage : 'Status belum dapat dimuat: ' + error.message);
    timer = setTimeout(() => poll(id), 4000); return;
  }
  if (job.done) {
    activeJobId = null; if (button) button.disabled = false;
    try { localStorage.removeItem('klip-job'); } catch (_) {}
  }
  try { if (selectedJobId === id) display(job); }
  catch (error) {
    showError('Hasil belum dapat ditampilkan di antarmuka. Muat ulang halaman. (' + error.message + ')');
  }
  if (job.done) { refreshHistory().catch(historyError); return; }
  timer = setTimeout(() => poll(id), 1800);
}
const vidEl = document.querySelector('#video');
if (vidEl) {
  vidEl.addEventListener('change', event => {
    const upl = document.querySelector('#upload-label');
    if (upl) upl.textContent = event.target.files[0]?.name || '＋ Pilih file video';
    if (event.target.files.length) {
      const u = document.querySelector('#url');
      if (u) u.value = '';
    }
  });
}
const urlEl = document.querySelector('#url');
if (urlEl) {
  urlEl.addEventListener('input', event => {
    if (event.target.value) {
      const v = document.querySelector('#video');
      if (v) v.value = '';
      const upl = document.querySelector('#upload-label');
      if (upl) upl.textContent = '＋ Pilih file video';
    }
  });
}
const newJobBtn = document.querySelector('#new-job');
if (newJobBtn) {
  newJobBtn.addEventListener('click', () => {
    if (hasUnsavedCaptionEdits()) {
      if (!window.confirm('Ada perubahan caption yang belum disimpan ke server. Tetap buat klip baru tanpa menyimpan?')) return;
    }
    history.replaceState(null, '', location.pathname + location.search); syncView(); window.scrollTo(0, 0);
    ++selectionVersion; selectedJobId = null; remember(null);
    if (form) { form.reset(); syncFormat(); }
    const upl = document.querySelector('#upload-label');
    if (upl) upl.textContent = '＋ Pilih file video';
    const resEl = document.querySelector('#results');
    if (resEl) resEl.hidden = true;
    const progEl = document.querySelector('#progress');
    if (progEl) progEl.hidden = !activeJobId;
    if (errorEl) errorEl.textContent = '';
    if (activeJobId && statusEl) {
      statusEl.textContent = 'Ada video sedang diproses. Kamu bisa membuka hasil lama dari riwayat.';
      const perc = document.querySelector('#percent');
      if (perc) perc.textContent = '';
    }
    if (button) button.disabled = Boolean(activeJobId); selectHistoryRow();
    if (mobileWidth.matches) setSidebar(false, false);
    const u = document.querySelector('#url');
    if (u) u.focus();
  });
}
if (form) {
  form.addEventListener('submit', async event => {
    event.preventDefault(); if (activeJobId) return;
    if (button) button.disabled = true;
    if (errorEl) errorEl.textContent = '';
    const progEl = document.querySelector('#progress');
    if (progEl) progEl.hidden = false;
    if (statusEl) statusEl.textContent = 'Mengirim video…';
    try {
      if (form.elements.audience?.value === 'global_en') {
        const health = await api('/api/health');
        if (!health.capabilities?.includes('global_en')) throw Error('Studio Global memerlukan server versi baru. Setelah video aktif selesai, restart server lalu coba lagi.');
      }
      const result = await api('/api/jobs', {method:'POST', body:new FormData(form)});
      clearTimeout(timer); ++selectionVersion;
      activeJobId = selectedJobId = result.id; remember(result.id);
      try { localStorage.setItem('klip-job', result.id); } catch (_) {}
      const resEl = document.querySelector('#results');
      if (resEl) resEl.hidden = true;
      const perc = document.querySelector('#percent');
      if (perc) perc.textContent = '0%';
      const bar = document.querySelector('#bar');
      if (bar) bar.style.width = '0%';
      poll(result.id);
      historyState.page = 1; historyState.query = ''; historyState.status = 'all';
      const sInput = document.querySelector('#history-search');
      if (sInput) sInput.value = '';
      refreshHistory().catch(() => { historyMessage.textContent = 'Riwayat belum dapat dimuat. Proses video tetap berjalan.'; });
    } catch (error) { showError(error instanceof ConnectionError ? connectionMessage : error.message); }
  });
}
for (const idea of document.querySelectorAll('.use-idea')) {
  idea.addEventListener('click', () => {
    if (!form) return;
    form.elements.topic.value = idea.dataset.topic; form.elements.duration.value = idea.dataset.duration;
    window.KlipSelect?.refresh();
    const isel = document.querySelector('#idea-selected');
    if (isel) isel.textContent = 'Fokus dipilih: ' + idea.closest('.idea-card').querySelector('h3').textContent + '. Pilih video yang sesuai dengan fokus ini.';
    form.scrollIntoView({behavior:'smooth', block:'center'});
    const u = document.querySelector('#url');
    if (u) u.focus({preventScroll:true});
  });
}

function initKidsStudio() {
  const briefPanel = document.querySelector('#kids-brief-section');
  if (!briefPanel) return;

  const titleInput = document.querySelector('#brief-title');
  const catSelect = document.querySelector('#brief-category');
  const durSelect = document.querySelector('#brief-duration');
  const goalInput = document.querySelector('#brief-goal');
  const outlineInput = document.querySelector('#brief-outline');
  const assetsInput = document.querySelector('#brief-assets');
  const briefIdInput = document.querySelector('#brief-id');
  const revisionInput = document.querySelector('#brief-revision');
  const ideaIdInput = document.querySelector('#brief-idea-id');
  const statusTag = document.querySelector('#brief-status-tag');
  const feedback = document.querySelector('#brief-feedback');
  const conflictBanner = document.querySelector('#brief-conflict-banner');
  const useServerBtn = document.querySelector('#brief-use-server-btn');
  const keepLocalBtn = document.querySelector('#brief-keep-local-btn');
  const saveBtn = document.querySelector('#save-brief-btn');
  const copyBtn = document.querySelector('#copy-brief-btn');
  const exportTxtBtn = document.querySelector('#export-txt-btn');
  const exportJsonBtn = document.querySelector('#export-json-btn');
  const deleteBtn = document.querySelector('#delete-brief-btn');
  const newBriefBtn = document.querySelector('#new-brief-btn');
  const useVideoBtn = document.createElement('button'); useVideoBtn.type = 'button';
  useVideoBtn.className = 'btn-primary'; useVideoBtn.id = 'use-kids-video';
  useVideoBtn.textContent = 'Gunakan video sendiri ↗'; useVideoBtn.disabled = true;
  newBriefBtn?.parentElement.append(useVideoBtn);
  useVideoBtn.addEventListener('click', () => {
    if (isSaving || isDirty || !currentBriefId) { setFeedback('Simpan brief sebelum memilih video.', 'warning'); return; }
    location.href = '/kids/source?brief=' + encodeURIComponent(currentBriefId);
  });
  const savedBriefsList = document.querySelector('#saved-briefs-list');
  const savedBriefsStatus = document.querySelector('#saved-briefs-status');
  const savedBriefsCount = document.querySelector('#saved-briefs-count');
  const pagination = document.querySelector('#briefs-pagination');
  const prevBtn = document.querySelector('#briefs-prev-btn');
  const nextBtn = document.querySelector('#briefs-next-btn');
  const pageInfo = document.querySelector('#briefs-page-info');

  const titleCount = document.querySelector('#title-count');
  const goalCount = document.querySelector('#goal-count');
  const outlineCount = document.querySelector('#outline-count');
  const assetsCount = document.querySelector('#assets-count');

  let currentBriefId = null;
  let serverRevision = 1;
  let savedBrief = null;
  let conflictBrief = null;
  let isSaving = false;
  let isDirty = false;
  let briefsPage = 1;
  let briefsTotalPages = 1;

  function setBriefBusy(busy) {
    isSaving = busy;
    // Lock form and context switches until the response belongs to this editor again.
    document.querySelectorAll('#kids-brief-section input, #kids-brief-section select, #kids-brief-section textarea, #kids-brief-section button, .use-kids-idea, .btn-load-brief, #new-brief-btn').forEach(el => {
      el.disabled = busy;
    });
    useVideoBtn.disabled = busy || isDirty || !currentBriefId;
    if (window.KlipSelect) window.KlipSelect.refresh();
  }
  document.addEventListener('click', event => {
    const link = event.target.closest('a[href]');
    if (!link || (!isDirty && !isSaving) || link.target === '_blank') return;
    const target = new URL(link.href, location.href);
    if (target.origin !== location.origin) return;
    if (isSaving || !window.confirm('Ada perubahan brief yang belum disimpan. Tetap tinggalkan editor?')) {
      event.preventDefault();
      event.stopImmediatePropagation();
    }
  }, true);

  function updateCounts() {
    if (titleCount && titleInput) titleCount.textContent = `(${titleInput.value.length}/120)`;
    if (goalCount && goalInput) goalCount.textContent = `(${goalInput.value.length}/300)`;
    if (outlineCount && outlineInput) outlineCount.textContent = `(${outlineInput.value.length}/2000)`;
    if (assetsCount && assetsInput) assetsCount.textContent = `(${assetsInput.value.length}/2000)`;
  }

  function markDirty() {
    isDirty = true;
    useVideoBtn.disabled = true;
    briefPanel.classList.add('has-unsaved');
    if (statusTag) {
      statusTag.textContent = currentBriefId ? 'Ada perubahan belum disimpan' : 'Draft baru (belum disimpan)';
      statusTag.className = 'status-dirty';
    }
  }

  function markSaved() {
    isDirty = false;
    useVideoBtn.disabled = isSaving || !currentBriefId;
    briefPanel.classList.remove('has-unsaved');
    if (statusTag) {
      statusTag.textContent = `Tersimpan (Revisi ${serverRevision})`;
      statusTag.className = 'status-saved';
    }
  }

  function setFeedback(msg, type = 'info') {
    if (!feedback) return;
    feedback.textContent = msg;
    feedback.className = `brief-feedback brief-feedback-${type}`;
    if (!msg) feedback.style.display = 'none';
    else feedback.style.display = 'block';
  }

  for (const input of [titleInput, goalInput, outlineInput, assetsInput]) {
    if (input) {
      input.addEventListener('input', () => {
        updateCounts();
        markDirty();
      });
    }
  }
  for (const sel of [catSelect, durSelect]) {
    if (sel) {
      sel.addEventListener('change', () => {
        markDirty();
      });
    }
  }

  const filterBtns = document.querySelectorAll('.kids-filter-btn');
  const ideaCards = document.querySelectorAll('.kids-idea-card');
  const emptyEl = document.querySelector('#kids-ideas-empty');

  for (const btn of filterBtns) {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => {
        b.classList.remove('active');
        b.setAttribute('aria-pressed', 'false');
      });
      btn.classList.add('active');
      btn.setAttribute('aria-pressed', 'true');
      const cat = btn.dataset.category;
      let visibleCount = 0;
      ideaCards.forEach(card => {
        const matches = cat === 'all' || card.dataset.category === cat;
        card.hidden = !matches;
        if (matches) visibleCount++;
      });
      if (emptyEl) emptyEl.hidden = visibleCount > 0;
    });
  }

  document.querySelectorAll('.use-kids-idea').forEach(btn => {
    btn.addEventListener('click', () => {
      if (isSaving) return;
      if (isDirty && !window.confirm('Ada perubahan brief yang belum disimpan. Tetap ganti dengan ide baru?')) {
        return;
      }
      currentBriefId = null;
      serverRevision = 1;
      savedBrief = null;
      conflictBrief = null;
      if (conflictBanner) conflictBanner.hidden = true;
      if (deleteBtn) deleteBtn.style.display = 'none';

      if (titleInput) titleInput.value = btn.dataset.title || '';
      if (goalInput) goalInput.value = btn.dataset.goal || '';
      if (catSelect) catSelect.value = btn.dataset.category || 'warna';
      if (durSelect) durSelect.value = btn.dataset.duration || '30';
      if (outlineInput) outlineInput.value = btn.dataset.outline || '';
      if (assetsInput) assetsInput.value = btn.dataset.assets || '';
      if (briefIdInput) briefIdInput.value = '';
      if (revisionInput) revisionInput.value = '1';
      if (ideaIdInput) ideaIdInput.value = btn.dataset.ideaId || '';

      if (window.KlipSelect) window.KlipSelect.refresh();
      updateCounts();
      markDirty();
      setFeedback('Ide berhasil dimuat ke editor. Lengkapi rencana lalu klik Simpan brief.', 'info');
      briefPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
      if (titleInput) titleInput.focus();
    });
  });

  async function saveBrief() {
    if (isSaving) return;
    const title = titleInput?.value.trim() || '';
    if (!title) {
      setFeedback('Judul brief wajib diisi.', 'error');
      if (titleInput) titleInput.focus();
      return;
    }
    if (title.length > 120) {
      setFeedback('Judul brief maksimal 120 karakter.', 'error');
      if (titleInput) titleInput.focus();
      return;
    }

    setBriefBusy(true);
    setFeedback('Menyimpan brief…', 'loading');

    const payload = {
      title,
      learning_goal: goalInput?.value.trim() || '',
      category: catSelect?.value || 'warna',
      target_duration: parseInt(durSelect?.value || '30', 10),
      outline: outlineInput?.value.trim() || '',
      asset_notes: assetsInput?.value.trim() || '',
      idea_id: ideaIdInput?.value.trim() || null,
    };

    try {
      let res;
      if (currentBriefId) {
        payload.expected_revision = serverRevision;
        res = await api(`/api/kids/briefs/${encodeURIComponent(currentBriefId)}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      } else {
        res = await api('/api/kids/briefs', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      }

      currentBriefId = res.brief.brief_id;
      serverRevision = res.brief.revision;
      savedBrief = res.brief;
      if (briefIdInput) briefIdInput.value = currentBriefId;
      if (revisionInput) revisionInput.value = serverRevision;
      if (deleteBtn) deleteBtn.style.display = 'inline-block';
      if (conflictBanner) conflictBanner.hidden = true;

      markSaved();
      setFeedback(`Brief tersimpan (Revisi ${serverRevision}).`, 'success');
      loadSavedBriefs(briefsPage);
    } catch (err) {
      if (err.cause?.status === 409 || err.message?.includes('409') || err.message?.includes('Konflik')) {
        try {
          const sres = await api(`/api/kids/briefs/${encodeURIComponent(currentBriefId)}`);
          conflictBrief = sres.brief;
        } catch (_) {}
        if (conflictBanner) conflictBanner.hidden = false;
        setFeedback('Konflik revisi: Versi server telah diperbarui oleh sesi lain.', 'warning');
      } else {
        setFeedback('Gagal menyimpan brief: ' + err.message, 'error');
      }
    } finally {
      setBriefBusy(false);
    }
  }

  if (saveBtn) saveBtn.addEventListener('click', saveBrief);

  if (useServerBtn) {
    useServerBtn.addEventListener('click', () => {
      if (!conflictBrief) return;
      loadBriefToForm(conflictBrief);
      if (conflictBanner) conflictBanner.hidden = true;
      setFeedback('Versi server dimuat ke editor.', 'info');
    });
  }
  if (keepLocalBtn) {
    keepLocalBtn.addEventListener('click', () => {
      if (conflictBrief) {
        serverRevision = conflictBrief.revision;
        if (revisionInput) revisionInput.value = serverRevision;
      }
      if (conflictBanner) conflictBanner.hidden = true;
      setFeedback('Tetap di edit lokal. Klik Simpan brief untuk menyimpan kembali.', 'info');
    });
  }

  function loadBriefToForm(b) {
    currentBriefId = b.brief_id;
    serverRevision = b.revision;
    savedBrief = b;
    conflictBrief = null;

    if (briefIdInput) briefIdInput.value = b.brief_id;
    if (revisionInput) revisionInput.value = b.revision;
    if (ideaIdInput) ideaIdInput.value = b.idea_id || '';
    if (titleInput) titleInput.value = b.title || '';
    if (goalInput) goalInput.value = b.learning_goal || '';
    if (catSelect) catSelect.value = b.category || 'warna';
    if (durSelect) durSelect.value = String(b.target_duration || 30);
    if (outlineInput) outlineInput.value = b.outline || '';
    if (assetsInput) assetsInput.value = b.asset_notes || '';

    if (window.KlipSelect) window.KlipSelect.refresh();
    updateCounts();
    markSaved();
    if (deleteBtn) deleteBtn.style.display = 'inline-block';
    if (conflictBanner) conflictBanner.hidden = true;
  }

  if (newBriefBtn) {
    newBriefBtn.addEventListener('click', () => {
      if (isSaving) return;
      if (isDirty && !window.confirm('Ada perubahan brief yang belum disimpan. Tetap buat brief baru?')) {
        return;
      }
      currentBriefId = null;
      serverRevision = 1;
      savedBrief = null;
      conflictBrief = null;
      isDirty = false;
      useVideoBtn.disabled = true;
      briefPanel.classList.remove('has-unsaved');
      if (briefIdInput) briefIdInput.value = '';
      if (revisionInput) revisionInput.value = '1';
      if (ideaIdInput) ideaIdInput.value = '';
      if (titleInput) titleInput.value = '';
      if (goalInput) goalInput.value = '';
      if (catSelect) catSelect.value = 'warna';
      if (durSelect) durSelect.value = '30';
      if (outlineInput) outlineInput.value = '';
      if (assetsInput) assetsInput.value = '';
      updateCounts();
      if (statusTag) {
        statusTag.textContent = 'Draft baru (belum disimpan)';
        statusTag.className = '';
      }
      if (deleteBtn) deleteBtn.style.display = 'none';
      if (conflictBanner) conflictBanner.hidden = true;
      setFeedback('', 'info');
      if (window.KlipSelect) window.KlipSelect.refresh();
      if (titleInput) titleInput.focus();
    });
  }

  if (deleteBtn) {
    deleteBtn.addEventListener('click', async () => {
      if (!currentBriefId) return;
      if (!window.confirm('Hapus brief ini secara permanen?')) return;
      deleteBtn.disabled = true;
      try {
        await api(`/api/kids/briefs/${encodeURIComponent(currentBriefId)}`, { method: 'DELETE' });
        setFeedback('Brief berhasil dihapus.', 'info');
        if (newBriefBtn) newBriefBtn.click();
        loadSavedBriefs(1);
      } catch (err) {
        setFeedback('Gagal menghapus brief: ' + err.message, 'error');
      } finally {
        deleteBtn.disabled = false;
      }
    });
  }

  function getBriefTxtString() {
    const title = titleInput?.value.trim() || 'Brief Tanpa Judul';
    const catLabel = catSelect?.selectedOptions[0]?.textContent || catSelect?.value || 'Warna';
    const dur = durSelect?.value || '30';
    const goal = goalInput?.value.trim() || '-';
    const outline = outlineInput?.value.trim() || '-';
    const assets = assetsInput?.value.trim() || '-';
    const ideaRef = ideaIdInput?.value.trim() || 'Kustom (orisinal)';
    const rev = serverRevision || 1;
    const now = new Date().toISOString();

    return [
      '='.repeat(80),
      'BRIEF PRODUKSI KONTEN ANAK (3–5 TAHUN · BAHASA INDONESIA)',
      'Klip Lokal — Studio Anak',
      '='.repeat(80),
      `Judul Kerja      : ${title}`,
      `Target Usia      : 3–5 tahun`,
      `Bahasa           : Bahasa Indonesia`,
      `Target Durasi    : ${dur} detik`,
      `Kategori         : ${catLabel}`,
      `Tujuan Belajar   : ${goal}`,
      `Referensi Ide    : ${ideaRef}`,
      `Revisi Brief     : ${rev}`,
      `Terakhir Diubah  : ${now}`,
      '',
      '-'.repeat(80),
      'OUTLINE PRODUKSI (Pembukaan – Kegiatan – Penutup)',
      '-'.repeat(80),
      outline,
      '',
      '-'.repeat(80),
      'CATATAN ASET & SUMBER REKAMAN',
      '-'.repeat(80),
      assets,
      '',
      '-'.repeat(80),
      'PANDUAN KUALITAS & KEBIJAKAN PLATFORM',
      '-'.repeat(80),
      '• Satu konsep dan jawaban yang jelas per klip; beri konteks sebelum pertanyaan.',
      '• Narasi bahasa Indonesia sederhana dan sesuai dengan objek yang benar-benar ditampilkan.',
      '• Tempo visual tenang, tanpa efek cepat, suara mengejutkan, atau loop tanpa akhir.',
      '• Tidak meminta data diri anak atau ajakan komentar publik (sesuai prinsip Made for Kids).',
      '• Menggunakan aset rekaman orisinal atau berizin resmi.',
      '='.repeat(80),
    ].join('\n');
  }

  function downloadFile(content, mimeType, filename) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, 100);
  }

  function slugify(text) {
    return text.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'brief';
  }

  if (copyBtn) {
    copyBtn.addEventListener('click', async () => {
      const text = getBriefTxtString();
      try {
        if (navigator.clipboard?.writeText) {
          await navigator.clipboard.writeText(text);
        } else {
          const ta = document.createElement('textarea');
          ta.value = text;
          document.body.appendChild(ta);
          ta.select();
          document.execCommand('copy');
          document.body.removeChild(ta);
        }
        setFeedback('Teks brief disalin ke clipboard.', 'success');
      } catch (err) {
        setFeedback('Gagal menyalin: ' + err.message, 'error');
      }
    });
  }

  if (exportTxtBtn) {
    exportTxtBtn.addEventListener('click', () => {
      const text = getBriefTxtString();
      const filename = `brief-${slugify(titleInput?.value.trim() || '')}.txt`;
      downloadFile(text, 'text/plain;charset=utf-8', filename);
      setFeedback('File TXT berhasil diunduh.', 'success');
    });
  }

  if (exportJsonBtn) {
    exportJsonBtn.addEventListener('click', () => {
      const dataObj = {
        brief_id: currentBriefId,
        revision: serverRevision,
        idea_id: ideaIdInput?.value.trim() || null,
        title: titleInput?.value.trim() || 'Brief Tanpa Judul',
        category: catSelect?.value || 'warna',
        age_band: '3_5',
        language: 'id',
        target_duration: parseInt(durSelect?.value || '30', 10),
        learning_goal: goalInput?.value.trim() || '',
        outline: outlineInput?.value.trim() || '',
        asset_notes: assetsInput?.value.trim() || '',
        exported_at: new Date().toISOString(),
      };
      const jsonStr = JSON.stringify(dataObj, null, 2);
      const filename = `brief-${slugify(titleInput?.value.trim() || '')}.json`;
      downloadFile(jsonStr, 'application/json;charset=utf-8', filename);
      setFeedback('File JSON berhasil diunduh.', 'success');
    });
  }

  async function loadSavedBriefs(page = 1) {
    if (!savedBriefsList) return;
    if (savedBriefsStatus) {
      savedBriefsStatus.hidden = false;
      savedBriefsStatus.textContent = 'Memuat daftar brief…';
    }

    try {
      const data = await api(`/api/kids/briefs?page=${page}&page_size=6`);
      briefsPage = data.page;
      briefsTotalPages = data.total_pages;

      if (savedBriefsCount) savedBriefsCount.textContent = String(data.total);

      if (!data.briefs.length) {
        savedBriefsList.innerHTML = '<p class="saved-briefs-empty">Belum ada brief tersimpan. Mulai dari ide di atas atau buat brief baru.</p>';
        if (savedBriefsStatus) savedBriefsStatus.hidden = true;
        if (pagination) pagination.hidden = true;
        return;
      }

      if (savedBriefsStatus) savedBriefsStatus.hidden = true;
      savedBriefsList.innerHTML = '';

      for (const b of data.briefs) {
        const item = document.createElement('article');
        item.className = 'saved-brief-item';
        if (b.brief_id === currentBriefId) item.classList.add('active');

        const catName = catSelect?.querySelector(`option[value="${b.category}"]`)?.textContent || b.category;
        const updated = b.updated_at ? new Date(b.updated_at).toLocaleDateString('id-ID', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '';

        const top = document.createElement('div'); top.className = 'saved-brief-top';
        for (const [cls, value] of [['brief-cat-pill', catName], ['brief-dur-pill', `${b.target_duration}s`], ['brief-rev-pill', `Rev ${b.revision}`]]) {
          const el = document.createElement('span'); el.className = cls; el.textContent = value; top.append(el);
        }
        const heading = document.createElement('h4'); heading.textContent = b.title;
        item.append(top, heading);
        if (b.learning_goal) {
          const goal = document.createElement('p'); goal.className = 'saved-brief-goal'; goal.textContent = b.learning_goal; item.append(goal);
        }
        const bottom = document.createElement('div'); bottom.className = 'saved-brief-bottom';
        const time = document.createElement('time'); time.textContent = updated;
        const load = document.createElement('button'); load.type = 'button'; load.className = 'btn-load-brief';
        load.dataset.id = b.brief_id; load.textContent = 'Buka di editor ↗'; load.disabled = isSaving;
        bottom.append(time, load); item.append(bottom);

        item.querySelector('.btn-load-brief').addEventListener('click', () => {
          if (isSaving) return;
      if (isDirty && !window.confirm('Ada perubahan brief yang belum disimpan. Tetap buka brief lain?')) {
            return;
          }
          loadBriefToForm(b);
          document.querySelectorAll('.saved-brief-item').forEach(el => el.classList.remove('active'));
          item.classList.add('active');
          briefPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });

        savedBriefsList.appendChild(item);
      }

      if (pagination) {
        pagination.hidden = briefsTotalPages <= 1;
        if (pageInfo) pageInfo.textContent = `${briefsPage} / ${briefsTotalPages}`;
        if (prevBtn) prevBtn.disabled = briefsPage <= 1;
        if (nextBtn) nextBtn.disabled = briefsPage >= briefsTotalPages;
      }
    } catch (err) {
      if (savedBriefsStatus) {
        savedBriefsStatus.hidden = false;
        savedBriefsStatus.textContent = 'Gagal memuat brief: ' + err.message;
      }
    }
  }

  if (prevBtn) {
    prevBtn.addEventListener('click', () => {
      if (briefsPage > 1) loadSavedBriefs(briefsPage - 1);
    });
  }
  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      if (briefsPage < briefsTotalPages) loadSavedBriefs(briefsPage + 1);
    });
  }

  updateCounts();
  loadSavedBriefs(1);
}

async function init() {
  try {
    const jobs = await refreshHistory();
    const active = jobs.find(job => !job.done);
    activeJobId = historyState.activeId || active?.id || null;
    if (button) button.disabled = Boolean(activeJobId);
    let saved; try { saved = localStorage.getItem('klip-selected') || localStorage.getItem('klip-job'); } catch (_) {}
    const selectedId = saved || activeJobId || jobs[0]?.id;
    if (selectedId && location.hash !== '#history' && !(document.body.classList.contains('kids-studio') || document.body.classList.contains('kids-source'))) {
      await openJob(selectedId);
    }
    if (activeJobId && !(document.body.classList.contains('kids-studio') || document.body.classList.contains('kids-source'))) poll(activeJobId);
  } catch (error) {
    if (historyMessage) historyMessage.textContent = error instanceof ConnectionError ? connectionMessage : 'Riwayat tidak dapat dimuat: ' + error.message;
  }
  if ((document.body.classList.contains('kids-studio') || document.body.classList.contains('kids-source')) || document.querySelector('#kids-brief-section')) {
    initKidsStudio();
  }
}
init();
