"""JavaScript snippets evaluated inside the browser page."""

DOM_HELPERS = r"""
const visible = (el) => {
  if (el.type === 'hidden') return false;
  const style = window.getComputedStyle(el);
  if (style.display === 'none' || style.visibility === 'hidden') return false;
  const rect = el.getBoundingClientRect();
  return rect.width > 0 && rect.height > 0;
};
const unique = (sel) => { try { return document.querySelectorAll(sel).length === 1; } catch (e) { return false; } };
const attrSel = (tag, attr, value) => `${tag}[${attr}="${value.replace(/"/g, '\\"')}"]`;
const labelOf = (el) => {
  if (el.id) {
    const l = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
    if (l) return l.innerText.trim();
  }
  const parent = el.closest('label');
  return parent ? parent.innerText.trim() : '';
};
const domPath = (el) => {
  const tags = [];
  for (let e = el; e && e.nodeType === 1 && e !== document.body; e = e.parentElement) tags.unshift(e.tagName.toLowerCase());
  return tags.join('>');
};
const fingerprint = (el) => ({
  tag: el.tagName.toLowerCase(),
  id: el.id || '',
  name: el.getAttribute('name') || '',
  type: el.getAttribute('type') || '',
  text: ((el.tagName === 'INPUT' ? el.value : el.innerText) || '').trim().replace(/\s+/g, ' ').slice(0, 80),
  label: labelOf(el).slice(0, 80),
  placeholder: el.getAttribute('placeholder') || '',
  aria_label: el.getAttribute('aria-label') || '',
  classes: Array.from(el.classList),
  href: el.getAttribute('href') || '',
  role: el.getAttribute('role') || '',
  form: el.form ? Array.from(el.form.elements).map((e) => e.name).filter(Boolean).join(',') : '',
  path: domPath(el),
});
const cssFor = (el) => {
  const tag = el.tagName.toLowerCase();
  if (el.id && unique('#' + CSS.escape(el.id))) return '#' + CSS.escape(el.id);
  for (const attr of ['data-testid', 'name', 'href', 'aria-label', 'placeholder']) {
    const v = el.getAttribute(attr);
    if (v) { const s = attrSel(tag, attr, v); if (unique(s)) return s; }
  }
  const parts = [];
  let e = el;
  while (e && e.nodeType === 1 && e !== document.body) {
    if (e.id && unique('#' + CSS.escape(e.id))) { parts.unshift('#' + CSS.escape(e.id)); break; }
    let part = e.tagName.toLowerCase();
    const siblings = Array.from(e.parentNode.children).filter((c) => c.tagName === e.tagName);
    if (siblings.length > 1) part += `:nth-of-type(${siblings.indexOf(e) + 1})`;
    parts.unshift(part);
    e = e.parentElement;
  }
  return parts.join(' > ');
};
const kindOf = (el) => {
  const tag = el.tagName.toLowerCase();
  if (tag === 'a') return 'link';
  if (tag === 'button' || el.getAttribute('role') === 'button') return 'button';
  if (tag === 'input' && ['submit', 'button', 'reset'].includes(el.type)) return 'button';
  if (tag === 'select') return 'select';
  if (tag === 'textarea') return 'textarea';
  return 'input';
};
const describe = (el) => ({ kind: kindOf(el), css: cssFor(el), fingerprint: fingerprint(el), required: !!el.required });
const INTERACTIVE = 'a[href], button, input, select, textarea, [role=button]';
"""

EXTRACT_PAGE_JS = (
    "() => {"
    + DOM_HELPERS
    + r"""
  const inForm = new Set();
  const forms = Array.from(document.forms).filter(visible).map((form) => {
    const fields = [];
    let submit = null;
    for (const el of form.querySelectorAll('input, select, textarea, button')) {
      inForm.add(el);
      if (!visible(el)) continue;
      const d = describe(el);
      if (d.kind === 'button') {
        if (!submit && (el.type === 'submit' || el.tagName === 'BUTTON')) submit = d;
      } else {
        fields.push(d);
      }
    }
    return {
      action: form.getAttribute('action') || '',
      method: (form.getAttribute('method') || 'get').toLowerCase(),
      fields, submit,
    };
  });
  const links = Array.from(document.querySelectorAll('a[href]'))
    .filter((a) => visible(a) && !a.getAttribute('href').startsWith('#')
      && !a.getAttribute('href').startsWith('javascript:') && !a.getAttribute('href').startsWith('mailto:'))
    .map((a) => ({ ...describe(a), absolute: a.href }));
  const buttons = Array.from(document.querySelectorAll('button, [role=button], input[type=submit], input[type=button]'))
    .filter((b) => visible(b) && !inForm.has(b)).map(describe);
  return { title: document.title, links, buttons, forms };
}
"""
)

CANDIDATES_JS = (
    "() => {"
    + DOM_HELPERS
    + r"""
  return Array.from(document.querySelectorAll(INTERACTIVE)).filter(visible).map(describe);
}
"""
)
