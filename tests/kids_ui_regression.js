// Runs inside the real Studio Anak page with fixture API only; never touches user data.
const titleField = document.querySelector('#brief-title');
const saveControl = document.querySelector('#save-brief-btn');
const literalTitle = '<img src=x onerror="window.kidsInjected=true">';
const literalGoal = '<svg onload="window.kidsInjected=true">';
let resolveSave, rejectSave, calls = 0;
const fixtureBrief = {brief_id:'a'.repeat(32), revision:1, title:literalTitle,
  learning_goal:literalGoal, category:'warna', target_duration:30,
  outline:'Uji', asset_notes:'', age_band:'3_5', language:'id'};
window.api = async (url, opts) => {
  if (opts?.method === 'POST') {
    calls++;
    return new Promise((resolve, reject) => {resolveSave = resolve; rejectSave = reject;});
  }
  return {briefs:[fixtureBrief], total:1, page:1, total_pages:1};
};
// Let the initial page requests finish before editing.
for (let attempt = 0; attempt < 100 && !document.querySelector("#saved-briefs-list h4"); attempt++) {
  await new Promise(resolve => setTimeout(resolve, 20));
}
assert(Boolean(document.querySelector("#saved-briefs-list h4")), "Studio initialized before editing");
titleField.value = literalTitle; titleField.dispatchEvent(new Event('input'));
document.querySelector('#brief-goal').value = literalGoal;
assert(document.querySelector('#kids-brief-section').classList.contains('has-unsaved'), 'Draft participates in navigation guard');
const dirtyEvent = new Event('beforeunload', {cancelable:true});
window.dispatchEvent(dirtyEvent);
assert(dirtyEvent.defaultPrevented, 'beforeunload protects dirty brief');
let confirms = 0;
window.confirm = () => {confirms++; return false;};
const studioLink = document.createElement('a'); studioLink.href = '/global'; document.body.append(studioLink);
const clickEvent = new MouseEvent('click', {bubbles:true, cancelable:true});
studioLink.dispatchEvent(clickEvent);
assert(clickEvent.defaultPrevented && confirms === 1, 'Studio navigation cancelled without discarding draft');
saveControl.click(); saveControl.click();
assert(calls === 1, 'No duplicate save');
assert(titleField.disabled && saveControl.disabled, 'Form locked during pending save');
assert(document.querySelector('#new-brief-btn').disabled, 'Context switch locked during save');
const firstIdea = document.querySelector('.use-kids-idea');
firstIdea.click();
assert(titleField.value === literalTitle, 'Pending save cannot switch to another idea');
rejectSave(new Error('Disk error'));
await new Promise(resolve => setTimeout(resolve, 20));
assert(!titleField.disabled && !saveControl.disabled, 'Controls recover after failure');
assert(titleField.value === literalTitle && hasUnsavedCaptionEdits(), 'Failure preserves draft protection');
saveControl.click(); resolveSave({brief:fixtureBrief});
await new Promise(resolve => setTimeout(resolve, 30));
assert(!hasUnsavedCaptionEdits(), 'Successful save clears dirty state');
const list = document.querySelector('#saved-briefs-list');
assert(list.querySelector('h4').textContent === literalTitle, 'Title rendered literally');
assert(list.querySelector('.saved-brief-goal').textContent === literalGoal, 'Goal rendered literally');
assert(!list.querySelector('img,svg') && !window.kidsInjected, 'Brief text creates no executable markup');
const cleanEvent = new Event('beforeunload', {cancelable:true}); window.dispatchEvent(cleanEvent);
assert(!cleanEvent.defaultPrevented, 'Clean brief does not block unload');
