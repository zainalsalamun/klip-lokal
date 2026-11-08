// Keep real selects as the form data source; render accessible, themed menus.
(() => {
  const controls = new Set();
  let opened = null;
  function close() {
    if (!opened) return;
    opened.menu.hidden = true;
    opened.trigger.setAttribute('aria-expanded', 'false');
    opened.trigger.removeAttribute('aria-activedescendant');
    opened.wrap.classList.remove('is-open', 'opens-up');
    opened = null;
  }
  function enhance(select) {
    if (select.parentElement.classList.contains('custom-select')) return;
    const label = document.querySelector(`label[for="${select.id}"]`);
    const wrap = document.createElement('div'); wrap.className = 'custom-select';
    const trigger = document.createElement('button'); trigger.type = 'button'; trigger.className = 'select-trigger';
    trigger.id = select.id + '-control'; trigger.setAttribute('role', 'combobox');
    trigger.setAttribute('aria-haspopup', 'listbox'); trigger.setAttribute('aria-expanded', 'false');
    const description = select.getAttribute('aria-describedby');
    if (description) trigger.setAttribute('aria-describedby', description);
    const text = document.createElement('span'); text.className = 'select-value';
    const arrow = document.createElement('span'); arrow.className = 'select-chevron'; arrow.setAttribute('aria-hidden', 'true');
    trigger.append(text, arrow);
    const menu = document.createElement('div'); menu.id = select.id + '-menu'; menu.className = 'select-menu'; menu.hidden = true; menu.setAttribute('role', 'listbox');
    trigger.setAttribute('aria-controls', menu.id);
    if (label) {
      label.id = select.id + '-label'; label.htmlFor = trigger.id;
      trigger.setAttribute('aria-labelledby', label.id); menu.setAttribute('aria-labelledby', label.id);
    }
    select.before(wrap); wrap.append(select, trigger, menu); select.hidden = true;
    const control = {select, wrap, trigger, menu, text, active: select.selectedIndex}; controls.add(control);
    function highlight(index) {
      control.active = Math.max(0, Math.min(select.options.length-1, index));
      [...menu.children].forEach((item, i) => item.classList.toggle('highlighted', i === control.active));
      trigger.setAttribute('aria-activedescendant', menu.children[control.active].id);
      menu.children[control.active].scrollIntoView({block:'nearest'});
    }
    function choose(index) {
      select.selectedIndex = index; refresh(); close(); trigger.focus();
      select.dispatchEvent(new Event('input', {bubbles:true}));
      select.dispatchEvent(new Event('change', {bubbles:true}));
    }
    for (const [index, option] of [...select.options].entries()) {
      const row = document.createElement('div'); row.className = 'select-option'; row.id = select.id + '-option-' + index; row.setAttribute('role', 'option');
      const value = document.createElement('span'); value.textContent = option.textContent;
      const check = document.createElement('span'); check.className = 'option-check'; check.textContent = '✓'; check.setAttribute('aria-hidden', 'true'); row.append(value, check);
      row.addEventListener('mousedown', event => event.preventDefault());
      row.addEventListener('click', () => choose(index));
      row.addEventListener('pointermove', () => highlight(index)); menu.append(row);
    }
    function show() {
      close(); opened = control; menu.hidden = false; wrap.classList.add('is-open'); trigger.setAttribute('aria-expanded', 'true');
      const bounds = trigger.getBoundingClientRect();
      if (window.innerHeight - bounds.bottom < menu.offsetHeight + 12 && bounds.top > menu.offsetHeight + 12) wrap.classList.add('opens-up');
      highlight(select.selectedIndex);
    }
    trigger.addEventListener('click', () => opened === control ? close() : show());
    trigger.addEventListener('keydown', event => {
      const isOpen = opened === control;
      if (event.key === 'Tab') { close(); return; }
      if (event.key === 'Escape') { event.preventDefault(); close(); return; }
      if (['ArrowDown','ArrowUp','Home','End'].includes(event.key)) {
        event.preventDefault(); if (!isOpen) { show(); if (event.key.startsWith('Arrow')) return; }
        highlight(event.key === 'Home' ? 0 : event.key === 'End' ? select.options.length-1 : control.active + (event.key === 'ArrowDown' ? 1 : -1));
      } else if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault(); isOpen ? choose(control.active) : show();
      } else if (event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
        event.preventDefault(); if (!isOpen) show();
        const index = [...select.options].findIndex(option => option.textContent.trim().toLowerCase().startsWith(event.key.toLowerCase()));
        if (index >= 0) highlight(index);
      }
    });
    select.addEventListener('change', refresh);
  }
  function refresh() {
    if (opened && !opened.wrap.isConnected) close();
    for (const control of controls) {
      if (!control.wrap.isConnected) {
        controls.delete(control);
        continue;
      }
      control.text.textContent = control.select.selectedOptions[0]?.textContent || '';
      control.trigger.disabled = control.select.disabled;
      [...control.menu.children].forEach((row, i) => row.setAttribute('aria-selected', String(i === control.select.selectedIndex)));
    }
  }
  document.addEventListener('pointerdown', event => { if (opened && !opened.wrap.contains(event.target)) close(); });
  document.addEventListener('focusin', event => { if (opened && !opened.wrap.contains(event.target)) close(); });
  document.querySelector('#form')?.addEventListener('reset', () => { close(); queueMicrotask(refresh); });
  function mount(root) {
    root.querySelectorAll('.options select, .thumbnail-ratio, #clip-sort').forEach(enhance);
    refresh();
  }
  window.KlipSelect = {mount, refresh};
  mount(document);
})();
