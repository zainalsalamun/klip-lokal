const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/app.js', 'utf8');
const block = source.slice(source.indexOf('class ConnectionError'), source.indexOf('function showError('));
function client(fetch) {
  const context = {fetch}; vm.createContext(context);
  return vm.runInContext(block + '\n({api, ConnectionError})', context);
}
(async () => {
  let c = client(async () => { throw new TypeError('Failed to fetch'); });
  await assert.rejects(c.api('/test'), error => error instanceof c.ConnectionError);
  assert.equal(new TypeError('Missing DOM element') instanceof c.ConnectionError, false);
  c = client(async () => ({ok:false, status:409, json:async () => ({error:'Video masih diproses'})}));
  await assert.rejects(c.api('/test'), error => !(error instanceof c.ConnectionError) && error.message === 'Video masih diproses');
  c = client(async () => ({ok:false, status:502, json:async () => {throw new SyntaxError('HTML response');}}));
  await assert.rejects(c.api('/test'), error => !(error instanceof c.ConnectionError) && error.message.includes('HTTP 502'));
  c = client(async () => ({ok:true, status:200, json:async () => ({done:true})}));
  assert.equal((await c.api('/test')).done, true);
  console.log('PASS: network, UI TypeError, API rejection, invalid response and success are distinguished');
})().catch(error => {console.error(error);process.exitCode=1;});
