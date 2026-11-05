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
  for (const nav of sidebar.querySelectorAll('.nav:not(.history-nav)')) nav.classList.toggle('active', !showingHistory && new URL(nav.href).pathname === location.pathname);
  document.querySelector('header>span').textContent = 'Workspace / ' + (showingHistory ? 'Riwayat klip' : document.body.classList.contains('global-studio') ? 'Studio Global' : 'Studio klip');
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
function syncFormat() { window.KlipSelect?.refresh(); syncSubtitleStyle(); document.querySelector('#format-details').textContent = outputSizes[form.elements.resolution.value] + ' · MP4 · crop mengikuti pembicara'; }
function syncSubtitleStyle() {
  const select = form.elements.subtitle_style;
  document.querySelector('.subtitle-preview').dataset.style = select.value;
  document.querySelector('#subtitle-style-description').textContent = select.selectedOptions[0].dataset.description;
}
form.elements.subtitle_style.addEventListener('change', syncSubtitleStyle);
syncSubtitleStyle();
form.elements.resolution.addEventListener('change', syncFormat);
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
  errorEl.textContent = message;
  button.disabled = Boolean(activeJobId);
  document.querySelector('#progress').hidden = false;
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
  return Boolean(document.querySelector('.caption-editor.has-unsaved'));
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
  let currentRevision = clip.metadata_revision || 1;

  const header = document.createElement('div'); header.className = 'caption-editor-header';
  const label = document.createElement('label'); label.textContent = 'Caption posting'; label.htmlFor = 'caption-' + clipId;
  const targetBadge = document.createElement('span'); targetBadge.className = 'caption-target-badge';
  targetBadge.textContent = audience === 'global_en' ? 'Target AI: English' : 'Target AI: Indonesia';
  header.append(label, targetBadge);

  const statusBadge = document.createElement('div'); statusBadge.className = 'caption-status-badge';
  statusBadge.setAttribute('role', 'status'); statusBadge.setAttribute('aria-live', 'polite');

  function updateStatus(state, msg) {
    statusBadge.className = 'caption-status-badge state-' + state;
    box.classList.toggle('has-unsaved', state === 'modified');
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

  const textarea = document.createElement('textarea'); textarea.id = label.htmlFor; textarea.rows = 4;
  textarea.maxLength = 2000; textarea.placeholder = 'Buat caption AI dari pembahasan klip, atau tulis sendiri…'; textarea.value = savedCaption;

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
  const saveBtn = document.createElement('button'); saveBtn.type = 'button'; saveBtn.className = 'btn-save-caption'; saveBtn.textContent = 'Simpan caption'; saveBtn.disabled = true;
  const copy = document.createElement('button'); copy.type = 'button'; copy.className = 'btn-copy-caption'; copy.textContent = 'Salin caption';
  const saveTxt = document.createElement('button'); saveTxt.type = 'button'; saveTxt.className = 'btn-download-txt'; saveTxt.textContent = 'Unduh TXT';
  const generate = document.createElement('button'); generate.type = 'button'; generate.className = 'btn-ai-caption'; generate.textContent = 'Buat caption AI lokal';
  const cancel = document.createElement('button'); cancel.type = 'button'; cancel.className = 'btn-cancel-caption'; cancel.textContent = 'Batal'; cancel.hidden = true;
  const feedback = document.createElement('span'); feedback.className = 'caption-feedback'; feedback.setAttribute('role', 'status');

  textarea.addEventListener('input', () => {
    updateCharCount();
    const isModified = textarea.value !== savedCaption;
    saveBtn.disabled = !isModified;
    if (isModified) {
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
        saveBtn.disabled = false;
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
    saveBtn.disabled = true; generate.disabled = true; textarea.disabled = true;
    updateStatus('saving'); feedback.textContent = ''; feedback.classList.remove('is-error');
    try {
      const res = await api('/api/jobs/' + encodeURIComponent(jobId) + '/clips/' + encodeURIComponent(clipId) + '/caption', {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({caption: textarea.value, expected_revision: currentRevision})
      });
      clip.caption = res.caption; clip.caption_source = res.caption_source; clip.caption_language = res.caption_language;
      clip.caption_updated_at = res.caption_updated_at; clip.metadata_revision = res.metadata_revision;
      currentRevision = res.metadata_revision; savedCaption = res.caption;
      try { localStorage.removeItem(legacyKey); } catch (_) {}
      legacyDraft = null; draftBanner.hidden = true; conflictBanner.hidden = true;
      updateNote(); updateStatus('saved'); saveBtn.disabled = true;
      feedback.textContent = 'Caption manual berhasil disimpan ke server.';
    } catch (err) {
      if (err.data && err.data.conflict) {
        updateStatus('conflict');
        showConflictUI(err.data);
      } else {
        updateStatus('error');
        feedback.textContent = err instanceof ConnectionError ? connectionMessage : (err.message || 'Gagal menyimpan caption.');
        feedback.classList.add('is-error');
        saveBtn.disabled = false;
      }
    } finally {
      generate.disabled = false; textarea.disabled = false;
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
      updateCharCount(); updateNote(); updateStatus('saved'); saveBtn.disabled = true; conflictBanner.hidden = true;
      feedback.textContent = 'Versi server dimuat.';
    });
    const overwriteBtn = document.createElement('button'); overwriteBtn.type = 'button';
    overwriteBtn.textContent = 'Timpa dengan teks ini';
    overwriteBtn.addEventListener('click', () => {
      currentRevision = data.current_revision; conflictBanner.hidden = true; saveBtn.disabled = false; saveBtn.click();
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
    const isModified = textarea.value !== savedCaption;
    const hasCustomText = textarea.value.trim().length > 0;
    if (!replaceConfirmed && (isModified || hasCustomText)) {
      replaceConfirmed = true; cancel.hidden = false; generate.textContent = 'Ganti teks & buat AI';
      feedback.textContent = 'Teks caption saat ini akan diganti oleh AI. Klik sekali lagi untuk melanjutkan, atau pilih Batal.';
      return;
    }
    replaceConfirmed = false; cancel.hidden = true; feedback.classList.remove('is-error');
    generate.disabled = true; saveBtn.disabled = true; textarea.disabled = true;
    generate.textContent = 'Merangkum pembahasan…'; feedback.textContent = 'AI berjalan di laptop; proses pertama bisa lebih lama.';

    try {
      const result = await api('/api/jobs/' + encodeURIComponent(jobId) + '/clips/' + encodeURIComponent(clipId) + '/caption', {method: 'POST'});
      Object.assign(clip, result); textarea.value = result.caption; savedCaption = result.caption;
      currentRevision = result.metadata_revision || (currentRevision + 1); clip.metadata_revision = currentRevision;
      updateCharCount(); updateNote(); updateStatus('saved'); saveBtn.disabled = true;
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
      generate.disabled = false; textarea.disabled = false; generate.textContent = 'Buat caption AI lokal';
    }
  });

  actions.append(saveBtn, copy, saveTxt, generate, cancel);
  box.append(header, statusBadge, draftBanner, conflictBanner, textarea, metaBar, actions, feedback);
  return box;
}
function render(job) {
  const resultsNote = document.querySelector('#results-note') || document.querySelector('#results .results-head p');
  if (resultsNote) resultsNote.textContent = job.audience === 'global_en' ? 'Subtitle dan caption: English · suara asli dipertahankan. Tinjau terjemahan dan konteks sebelum posting.' : 'Pilihan berdasarkan transkrip, bukan jaminan viral. Tinjau framing dan batas ucapan sebelum posting.';
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
    card.append(video, heading, time, framing, text, download, captionEditor(c, i, job.id, job.audience)); grid.append(card);
  });
}
function display(job) {
  document.querySelector('#progress').hidden = false;
  statusEl.textContent = job.status;
  document.querySelector('#percent').textContent = (job.progress || 0) + '%';
  document.querySelector('#bar').style.width = (job.progress || 0) + '%';
  errorEl.textContent = job.error || '';
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
    document.querySelector('#url').value = job.source_url || '';
    document.querySelector('#video').value = '';
    document.querySelector('#upload-label').textContent = '＋ Pilih file video';
    for (const key of ['duration', 'count', 'language']) if (job[key] != null) form.elements[key].value = job[key];
    form.elements.resolution.value = job.resolution || '720';
    form.elements.subtitle_style.value = job.subtitle_style || 'classic';
    if (form.elements.topic) form.elements.topic.value = job.topic || 'general';
    syncFormat();
    display(job);
    if (!job.done && !activeJobId) { activeJobId = id; button.disabled = true; poll(id); }
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
    activeJobId = null; button.disabled = false;
    try { localStorage.removeItem('klip-job'); } catch (_) {}
  }
  try { if (selectedJobId === id) display(job); }
  catch (error) {
    showError('Hasil belum dapat ditampilkan di antarmuka. Muat ulang halaman. (' + error.message + ')');
  }
  if (job.done) { refreshHistory().catch(historyError); return; }
  timer = setTimeout(() => poll(id), 1800);
}
document.querySelector('#video').addEventListener('change', event => {
  document.querySelector('#upload-label').textContent = event.target.files[0]?.name || '＋ Pilih file video';
  if (event.target.files.length) document.querySelector('#url').value = '';
});
document.querySelector('#url').addEventListener('input', event => {
  if (event.target.value) { document.querySelector('#video').value = ''; document.querySelector('#upload-label').textContent = '＋ Pilih file video'; }
});
document.querySelector('#new-job').addEventListener('click', () => {
  if (hasUnsavedCaptionEdits()) {
    if (!window.confirm('Ada perubahan caption yang belum disimpan ke server. Tetap buat klip baru tanpa menyimpan?')) return;
  }
  history.replaceState(null, '', location.pathname + location.search); syncView(); window.scrollTo(0, 0);
  ++selectionVersion; selectedJobId = null; remember(null); form.reset(); syncFormat();
  document.querySelector('#upload-label').textContent = '＋ Pilih file video';
  document.querySelector('#results').hidden = true;
  document.querySelector('#progress').hidden = !activeJobId;
  errorEl.textContent = '';
  if (activeJobId) { statusEl.textContent = 'Ada video sedang diproses. Kamu bisa membuka hasil lama dari riwayat.'; document.querySelector('#percent').textContent = ''; }
  button.disabled = Boolean(activeJobId); selectHistoryRow();
  if (mobileWidth.matches) setSidebar(false, false);
  document.querySelector('#url').focus();
});
form.addEventListener('submit', async event => {
  event.preventDefault(); if (activeJobId) return;
  button.disabled = true; errorEl.textContent = '';
  document.querySelector('#progress').hidden = false; statusEl.textContent = 'Mengirim video…';
  try {
    if (form.elements.audience?.value === 'global_en') {
      const health = await api('/api/health');
      if (!health.capabilities?.includes('global_en')) throw Error('Studio Global memerlukan server versi baru. Setelah video aktif selesai, restart server lalu coba lagi.');
    }
    const result = await api('/api/jobs', {method:'POST', body:new FormData(form)});
    clearTimeout(timer); ++selectionVersion;
    activeJobId = selectedJobId = result.id; remember(result.id);
    try { localStorage.setItem('klip-job', result.id); } catch (_) {}
    document.querySelector('#results').hidden = true;
    document.querySelector('#percent').textContent = '0%'; document.querySelector('#bar').style.width = '0%';
    poll(result.id);
    historyState.page = 1; historyState.query = ''; historyState.status = 'all';
    document.querySelector('#history-search').value = '';
    refreshHistory().catch(() => { historyMessage.textContent = 'Riwayat belum dapat dimuat. Proses video tetap berjalan.'; });
  } catch (error) { showError(error instanceof ConnectionError ? connectionMessage : error.message); }
});
for (const idea of document.querySelectorAll('.use-idea')) idea.addEventListener('click', () => {
  form.elements.topic.value = idea.dataset.topic; form.elements.duration.value = idea.dataset.duration;
  window.KlipSelect?.refresh();
  document.querySelector('#idea-selected').textContent = 'Fokus dipilih: ' + idea.closest('.idea-card').querySelector('h3').textContent + '. Pilih video yang sesuai dengan fokus ini.';
  form.scrollIntoView({behavior:'smooth', block:'center'}); document.querySelector('#url').focus({preventScroll:true});
});
async function init() {
  try {
    const jobs = await refreshHistory();
    const active = jobs.find(job => !job.done);
    activeJobId = historyState.activeId || active?.id || null; button.disabled = Boolean(activeJobId);
    let saved; try { saved = localStorage.getItem('klip-selected') || localStorage.getItem('klip-job'); } catch (_) {}
    const selectedId = saved || activeJobId || jobs[0]?.id;
    if (selectedId && location.hash !== '#history') await openJob(selectedId);
    if (activeJobId) poll(activeJobId);
  } catch (error) { historyMessage.textContent = error instanceof ConnectionError ? connectionMessage : 'Riwayat tidak dapat dimuat: ' + error.message; }
}
init();
