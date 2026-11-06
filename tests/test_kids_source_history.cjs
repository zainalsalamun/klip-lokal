const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/app.js', 'utf8');
const code = source.slice(source.indexOf('async function openJob('), source.indexOf('async function poll('));
async function run(job, kids = true) {
  const elements = Object.fromEntries(['duration','count','language','resolution','subtitle_style','content_profile','brief_id'].map(k => [k,{value:''}]));
  Object.assign(elements.language,{value:'id'}); elements.duration.value='15';
  elements.content_profile.value = kids ? 'kids' : 'general'; elements.brief_id.value='brief-a';
  const url={value:'https://youtu.be/pending-source'}; const upload={value:'selected-file'};
  const ctx = vm.createContext({form:{elements},document:{querySelector:s=>s==='#url'?url:s==='#video'?upload:null,body:{classList:{contains:()=>false}}},
    selectedJobId:null,selectionVersion:0,activeJobId:null,location:{hash:''},mobileWidth:{matches:false},
    hasUnsavedCaptionEdits:()=>false,remember:()=>{},selectHistoryRow:()=>{},syncFormat:()=>{},display:()=>{},
    api:async()=>job,showError:e=>{throw Error(e)},ConnectionError:class extends Error{}});
  vm.runInContext(code,ctx); await ctx.openJob('job'); return {elements,url,upload};
}
(async()=>{
  let state=await run({done:true,language:'en',duration:60,source_url:'https://youtu.be/english',content_profile:'general'});
  assert.equal(state.elements.language.value,'id'); assert.equal(state.elements.duration.value,'15');
  assert.equal(state.url.value,'https://youtu.be/pending-source'); assert.equal(state.upload.value,'selected-file');
  state=await run({done:true,language:'id',duration:30,content_profile:'kids',kids_metadata:{brief_id:'other-brief'}});
  assert.equal(state.elements.duration.value,'15');
  state=await run({done:true,language:'id',duration:30,content_profile:'kids',kids_metadata:{brief_id:'brief-a'}});
  assert.equal(state.elements.duration.value,30); assert.equal(state.elements.language.value,'id');
  state=await run({done:true,language:'en',duration:60,content_profile:'general'},false);
  assert.equal(state.elements.language.value,'en'); assert.equal(state.elements.duration.value,60);
  console.log('PASS: kids source keeps brief/language across unrelated history; matching brief and general prefill retained');
})().catch(err=>{console.error(err);process.exitCode=1});
