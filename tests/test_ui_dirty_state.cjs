const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const appJs = fs.readFileSync('static/app.js', 'utf8');

// Test dirty state and navigation protection logic extracted from captionEditor
// Extract the captionEditor block
const fnStart = appJs.indexOf('function captionEditor(');
const fnEnd = appJs.indexOf('function render(', fnStart);
const captionEditorCode = appJs.slice(fnStart, fnEnd);

function makeEditor(apiFn) {
  const elements = [];
  function createElement(tag) {
    const el = {
      tagName: tag,
      className: '',
      classList: {
        _classes: new Set(),
        add(c) { this._classes.add(c); },
        remove(c) { this._classes.delete(c); },
        toggle(c, force) {
          if (force === undefined) {
            if (this._classes.has(c)) this._classes.delete(c);
            else this._classes.add(c);
          } else if (force) {
            this._classes.add(c);
          } else {
            this._classes.delete(c);
          }
          return this._classes.has(c);
        },
        contains(c) { return this._classes.has(c); }
      },
      attributes: {},
      setAttribute(k, v) { this.attributes[k] = String(v); },
      removeAttribute(k) { delete this.attributes[k]; },
      style: {},
      children: [],
      append(...args) { this.children.push(...args); },
      replaceChildren(...args) { this.children = [...args]; },
      listeners: {},
      addEventListener(evt, fn) { this.listeners[evt] = fn; },
      value: '',
      disabled: false,
      hidden: false,
      textContent: ''
    };
    elements.push(el);
    return el;
  }

  const localStorageData = {};
  const context = {
    document: {
      createElement,
      querySelector: (sel) => {
        if (sel.includes('.caption-editor.has-unsaved')) {
          const cap = elements.find(e => e.className.includes('caption-editor') && e.classList.contains('has-unsaved'));
          if (cap) return cap;
        }
        if (sel.includes('.watermark-editor.has-unsaved')) {
          const wm = elements.find(e => e.className.includes('watermark-editor') && e.classList.contains('has-unsaved'));
          if (wm) return wm;
        }
        return null;
      }
    },
    localStorage: {
      getItem: (k) => localStorageData[k] || null,
      setItem: (k, v) => { localStorageData[k] = String(v); },
      removeItem: (k) => { delete localStorageData[k]; }
    },
    formatTime: () => '0:00',
    makeCaption: () => 'Caption awal',
    formatSaveTime: () => ' (10:00)',
    api: apiFn || (async () => ({})),
    ConnectionError: class ConnectionError extends Error {},
    connectionMessage: 'Server offline',
    window: { addEventListener: () => {} }
  };

  vm.createContext(context);
  const script = captionEditorCode + '\n({captionEditor, hasUnsavedCaptionEdits: ' +
    appJs.slice(appJs.indexOf('function hasUnsavedCaptionEdits('), appJs.indexOf('window.addEventListener(\'beforeunload\'')) +
    ', getElements: () => elements})';

  return vm.runInContext(script, context);
}

// Run test
(async () => {
  // 1. Initial state and typing
  const m1 = makeEditor();
  const clip1 = { clip_id: 'c1', caption: 'Versi tersimpan', metadata_revision: 1 };
  const box1 = m1.captionEditor(clip1, 0, 'j1', 'local');
  const ta1 = box1.children.find(c => c.tagName === 'textarea');
  const acts1 = box1.children.find(c => c.className === 'caption-actions');
  const save1 = acts1.children.find(c => c.className === 'btn-save-caption');

  assert.equal(box1.classList.contains('has-unsaved'), false);
  assert.equal(m1.hasUnsavedCaptionEdits(), false);
  assert.equal(save1.disabled, true);

  ta1.value = 'Perubahan manual baru';
  ta1.listeners.input();

  assert.equal(box1.classList.contains('has-unsaved'), true);
  assert.equal(m1.hasUnsavedCaptionEdits(), true);
  assert.equal(save1.disabled, false);

  // 2. Save fails with 500 error: saving state must keep has-unsaved, and error state must keep has-unsaved
  let duringSavingDirty = false;
  let duringSavingSaveDisabled = false;
  let saveAttempted = false;
  const m2 = makeEditor(async () => {
    saveAttempted = true;
    duringSavingDirty = box2.classList.contains('has-unsaved');
    duringSavingSaveDisabled = save2.disabled;
    throw new Error('500 Server error: disk failure');
  });

  const box2 = m2.captionEditor({ clip_id: 'c2', caption: 'Versi tersimpan', metadata_revision: 1 }, 0, 'j2', 'local');
  const ta2 = box2.children.find(c => c.tagName === 'textarea');
  const acts2 = box2.children.find(c => c.className === 'caption-actions');
  const save2 = acts2.children.find(c => c.className === 'btn-save-caption');

  ta2.value = 'Teks baru belum tersimpan';
  ta2.listeners.input();
  assert.equal(box2.classList.contains('has-unsaved'), true);

  await save2.listeners.click();
  assert.equal(saveAttempted, true);
  assert.equal(duringSavingDirty, true, 'has-unsaved must remain true during saving');
  assert.equal(duringSavingSaveDisabled, true, 'Save button must remain disabled while saving is pending');
  assert.equal(box2.classList.contains('has-unsaved'), true, 'has-unsaved must remain true after error');
  assert.equal(save2.disabled, false, 'Save button must be re-enabled after error');
  assert.equal(ta2.value, 'Teks baru belum tersimpan', 'Text must not be lost');
  assert.equal(m2.hasUnsavedCaptionEdits(), true, 'hasUnsavedCaptionEdits must remain true');

  // 3. Conflict 409 error
  const m3 = makeEditor(async () => {
    const err = new Error('Konflik revisi');
    err.data = { conflict: true, current_revision: 2, server_caption: 'Versi server lain' };
    err.status = 409;
    throw err;
  });

  const box3 = m3.captionEditor({ clip_id: 'c3', caption: 'Versi tersimpan', metadata_revision: 1 }, 0, 'j3', 'local');
  const ta3 = box3.children.find(c => c.tagName === 'textarea');
  const acts3 = box3.children.find(c => c.className === 'caption-actions');
  const save3 = acts3.children.find(c => c.className === 'btn-save-caption');

  ta3.value = 'Teks konflik';
  ta3.listeners.input();

  await save3.listeners.click();
  assert.equal(box3.classList.contains('has-unsaved'), true, 'has-unsaved must remain true after conflict');
  assert.equal(save3.disabled, false, 'Save button must remain enabled after conflict');
  assert.equal(m3.hasUnsavedCaptionEdits(), true, 'hasUnsavedCaptionEdits must remain true');

  // 4. AI failure while text is dirty
  const m4 = makeEditor(async () => {
    throw new Error('AI Ollama offline');
  });

  const box4 = m4.captionEditor({ clip_id: 'c4', caption: 'Versi tersimpan', metadata_revision: 1 }, 0, 'j4', 'local');
  const ta4 = box4.children.find(c => c.tagName === 'textarea');
  const acts4 = box4.children.find(c => c.className === 'caption-actions');
  const save4 = acts4.children.find(c => c.className === 'btn-save-caption');
  const ai4 = acts4.children.find(c => c.className === 'btn-ai-caption');

  ta4.value = 'Teks sebelum AI coba jalan';
  ta4.listeners.input();
  assert.equal(save4.disabled, false);

  // Click AI (first click confirms replace)
  await ai4.listeners.click();
  // Second click triggers execution and throws error
  await ai4.listeners.click();

  assert.equal(box4.classList.contains('has-unsaved'), true, 'has-unsaved must remain true after AI failure');
  assert.equal(save4.disabled, false, 'Save button must not be locked after AI failure');
  assert.equal(ta4.value, 'Teks sebelum AI coba jalan', 'Draft text preserved');

  // 5. Success clears dirty state
  const m5 = makeEditor(async () => ({
    caption: 'Teks sukses tersimpan',
    caption_source: 'manual',
    metadata_revision: 2,
    caption_updated_at: new Date().toISOString()
  }));

  const box5 = m5.captionEditor({ clip_id: 'c5', caption: 'Versi tersimpan', metadata_revision: 1 }, 0, 'j5', 'local');
  const ta5 = box5.children.find(c => c.tagName === 'textarea');
  const acts5 = box5.children.find(c => c.className === 'caption-actions');
  const save5 = acts5.children.find(c => c.className === 'btn-save-caption');

  ta5.value = 'Teks sukses tersimpan';
  ta5.listeners.input();
  assert.equal(box5.classList.contains('has-unsaved'), true);

  await save5.listeners.click();

  assert.equal(box5.classList.contains('has-unsaved'), false, 'has-unsaved must be false after successful save');
  assert.equal(save5.disabled, true, 'Save button must be disabled after successful save');
  assert.equal(m5.hasUnsavedCaptionEdits(), false);

  // 6. Deferred Promise: Save pending disables saveBtn while keeping dirty=true, prevents double submission, and re-enables on error
  let resolveSave6, rejectSave6;
  let save6CallCount = 0;
  const deferredSave6 = new Promise((res, rej) => {
    resolveSave6 = res;
    rejectSave6 = rej;
  });

  const m6 = makeEditor(() => {
    save6CallCount++;
    return deferredSave6;
  });

  const box6 = m6.captionEditor({ clip_id: 'c6', caption: 'Versi tersimpan', metadata_revision: 1 }, 0, 'j6', 'local');
  const ta6 = box6.children.find(c => c.tagName === 'textarea');
  const acts6 = box6.children.find(c => c.className === 'caption-actions');
  const save6 = acts6.children.find(c => c.className === 'btn-save-caption');
  const ai6 = acts6.children.find(c => c.className === 'btn-ai-caption');

  ta6.value = 'Draft deferred error';
  ta6.listeners.input();
  assert.equal(save6.disabled, false);
  assert.equal(box6.classList.contains('has-unsaved'), true);

  // Start save (pending)
  const save6Promise = save6.listeners.click();

  // During pending:
  assert.equal(save6CallCount, 1);
  assert.equal(save6.disabled, true, 'Save button must be strictly disabled while pending');
  assert.equal(ai6.disabled, true, 'AI button must be disabled while saving is pending');
  assert.equal(ta6.disabled, true, 'Textarea must be disabled while saving is pending');
  assert.equal(box6.classList.contains('has-unsaved'), true, 'has-unsaved must remain true during pending');
  assert.equal(m6.hasUnsavedCaptionEdits(), true, 'Unsaved protection must remain active during pending');

  // Second click while pending must NOT fire a duplicate request
  save6.listeners.click();
  save6.listeners.click();
  assert.equal(save6CallCount, 1, 'Repeated clicks during pending must not trigger duplicate API calls');

  // Now reject with 500 error
  rejectSave6(new Error('500 Internal error'));
  await save6Promise;

  // After error:
  assert.equal(save6.disabled, false, 'Save button must be enabled after error');
  assert.equal(ai6.disabled, false, 'AI button must be enabled after error');
  assert.equal(ta6.disabled, false, 'Textarea must be re-enabled after error');
  assert.equal(ta6.value, 'Draft deferred error', 'Draft text preserved');
  assert.equal(box6.classList.contains('has-unsaved'), true, 'has-unsaved remains true after error');
  assert.equal(m6.hasUnsavedCaptionEdits(), true, 'Unsaved protection remains active after error');

  // 7. Deferred Promise: Save pending disables saveBtn, prevents double submission, and disables saveBtn on success (dirty false)
  let resolveSave7;
  let save7CallCount = 0;
  const deferredSave7 = new Promise((res) => {
    resolveSave7 = res;
  });

  const m7 = makeEditor(() => {
    save7CallCount++;
    return deferredSave7;
  });

  const box7 = m7.captionEditor({ clip_id: 'c7', caption: 'Versi tersimpan', metadata_revision: 1 }, 0, 'j7', 'local');
  const ta7 = box7.children.find(c => c.tagName === 'textarea');
  const acts7 = box7.children.find(c => c.className === 'caption-actions');
  const save7 = acts7.children.find(c => c.className === 'btn-save-caption');
  const ai7 = acts7.children.find(c => c.className === 'btn-ai-caption');

  ta7.value = 'Draft deferred success';
  ta7.listeners.input();
  assert.equal(save7.disabled, false);
  assert.equal(box7.classList.contains('has-unsaved'), true);

  // Start save (pending)
  const save7Promise = save7.listeners.click();

  // During pending:
  assert.equal(save7CallCount, 1);
  assert.equal(save7.disabled, true, 'Save button must be disabled while pending');
  assert.equal(ai7.disabled, true, 'AI button must be disabled while saving is pending');
  assert.equal(ta7.disabled, true, 'Textarea must be disabled while saving is pending');
  assert.equal(box7.classList.contains('has-unsaved'), true, 'has-unsaved must remain true during pending');

  // Second click while pending
  save7.listeners.click();
  assert.equal(save7CallCount, 1, 'Repeated clicks during pending must not trigger duplicate API calls');

  // Now resolve with success
  resolveSave7({
    caption: 'Draft deferred success',
    caption_source: 'manual',
    metadata_revision: 2,
    caption_updated_at: new Date().toISOString()
  });
  await save7Promise;

  // After success:
  assert.equal(save7.disabled, true, 'Save button must be disabled after success');
  assert.equal(ai7.disabled, false, 'AI button must be enabled after success');
  assert.equal(ta7.disabled, false, 'Textarea must be re-enabled after success');
  assert.equal(box7.classList.contains('has-unsaved'), false, 'has-unsaved must be false after success');
  assert.equal(m7.hasUnsavedCaptionEdits(), false, 'Unsaved protection cleared after success');

  // 8. Deferred Promise: AI generation pending disables both AI and Save button, preserves draft dirty state, and re-enables Save button on AI error
  let rejectAi8;
  let ai8CallCount = 0;
  const deferredAi8 = new Promise((_, rej) => {
    rejectAi8 = rej;
  });

  const m8 = makeEditor(() => {
    ai8CallCount++;
    return deferredAi8;
  });

  const box8 = m8.captionEditor({ clip_id: 'c8', caption: 'Versi tersimpan', metadata_revision: 1 }, 0, 'j8', 'local');
  const ta8 = box8.children.find(c => c.tagName === 'textarea');
  const acts8 = box8.children.find(c => c.className === 'caption-actions');
  const save8 = acts8.children.find(c => c.className === 'btn-save-caption');
  const ai8 = acts8.children.find(c => c.className === 'btn-ai-caption');

  ta8.value = 'Draft sebelum AI deferred';
  ta8.listeners.input();
  assert.equal(save8.disabled, false);
  assert.equal(box8.classList.contains('has-unsaved'), true);

  // Click AI 1 (confirm)
  await ai8.listeners.click();
  assert.equal(ai8CallCount, 0);

  // Click AI 2 (starts request)
  const ai8Promise = ai8.listeners.click();
  assert.equal(ai8CallCount, 1);

  // During AI pending:
  assert.equal(ai8.disabled, true, 'AI button must be disabled while AI is pending');
  assert.equal(save8.disabled, true, 'Save button must be disabled while AI is busy');
  assert.equal(ta8.disabled, true, 'Textarea must be disabled while AI is busy');
  assert.equal(box8.classList.contains('has-unsaved'), true, 'has-unsaved must remain true during AI pending');

  // Repeated clicks on AI or Save while AI is busy
  ai8.listeners.click();
  save8.listeners.click();
  assert.equal(ai8CallCount, 1, 'Duplicate clicks while AI is busy must be blocked');

  // Reject AI
  rejectAi8(new Error('AI Ollama timeout'));
  await ai8Promise;

  // After AI failure:
  assert.equal(save8.disabled, false, 'Save button must not be locked after AI failure');
  assert.equal(ai8.disabled, false, 'AI button must be re-enabled after AI failure');
  assert.equal(ta8.disabled, false, 'Textarea must be re-enabled after AI failure');
  assert.equal(ta8.value, 'Draft sebelum AI deferred', 'Draft text preserved after AI failure');
  assert.equal(box8.classList.contains('has-unsaved'), true, 'has-unsaved remains true after AI failure');

  console.log('PASS: UI dirty state correctly maintained across saving, error, conflict, and AI failure');
})().catch(err => {
  console.error(err);
  process.exitCode = 1;
});
