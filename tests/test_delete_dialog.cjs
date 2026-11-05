const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/app.js', 'utf8');
const start = source.indexOf('let deleteDialog, finishDeleteConfirmation;');
const end = source.indexOf('async function deleteJob(', start);
assert(start >= 0 && end > start);
class Element {
  constructor() { this.listeners = {}; this.textContent = ''; }
  addEventListener(type, listener) { (this.listeners[type] ||= []).push(listener); }
  emit(type, event = {}) { for (const listener of this.listeners[type] || []) listener(event); }
  focus() { document.activeElement = this; }
  setAttribute() {}
}
class Dialog extends Element {
  constructor() { super(); this.children = new Map(); this.open = false; }
  querySelector(selector) { if (!this.children.has(selector)) this.children.set(selector, new Element()); return this.children.get(selector); }
  showModal() { this.open = true; }
  close() { this.open = false; this.emit('close'); }
  getBoundingClientRect() { return {left:10,right:490,top:10,bottom:600}; }
}
let dialog;
const classes = new Set();
const document = {
  createElement: () => (dialog = new Dialog()),
  body: { append() {}, classList: {add: name => classes.add(name), remove: name => classes.delete(name)} },
};
const context = vm.createContext({document});
vm.runInContext(source.slice(start, end), context);
const confirm = job => context.confirmHistoryDelete(job);
(async () => {
  const job = {title:'<img src=x onerror=alert(1)>',clip_count:1};
  let pending = confirm(job);
  assert.equal(dialog.open,true);
  assert.equal(document.activeElement,dialog.querySelector('.delete-dialog-cancel'));
  assert.equal(dialog.querySelector('#delete-dialog-video').textContent,job.title);
  assert.equal(await confirm(job),false); // no second dialog while one is open
  dialog.querySelector('.delete-dialog-cancel').emit('click');
  assert.equal(await pending,false);
  assert.equal(classes.size,0);
  pending = confirm(job);
  let prevented = false;
  dialog.emit('cancel',{preventDefault(){prevented=true;}});
  assert.equal(await pending,false);assert(prevented);
  pending = confirm(job);
  dialog.emit('click',{target:dialog,clientX:0,clientY:0});
  assert.equal(await pending,false);
  pending = confirm(job);
  dialog.emit('click',{target:dialog,clientX:50,clientY:50});
  assert(dialog.open); // inner padding never confirms or dismisses
  dialog.querySelector('.delete-dialog-close').emit('click');
  assert.equal(await pending,false);
  pending = confirm(job);
  dialog.querySelector('.delete-dialog-confirm').emit('click');
  assert.equal(await pending,true); // boolean only; no API or real data in this test
  assert.equal(classes.size,0);
  console.log('PASS: cancel, Escape, backdrop, close, explicit confirmation, safe title and duplicate guard');
})().catch(error => {console.error(error);process.exitCode=1;});
