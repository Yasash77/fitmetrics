/* FitPulse user platform — single-page app (Yasash). Generated in this order: core, forms, public, onboarding, plans, tracking. */

/* ===== core ===== */
/* FitPulse platform — core: helpers, API client, state, router, layout. No framework, no build step. */
'use strict';

const FP = window.FP = { routes: [], state: { user: null, profile: null, config: null, integrations: null } };

/* ------------------------------------------------------------------ helpers */
const h = (v) => String(v == null ? '' : v).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
const uid = () => (crypto.randomUUID ? crypto.randomUUID().replace(/-/g, '') : Math.random().toString(36).slice(2) + Date.now().toString(36));
const today = () => { const d = new Date(); return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10); };
const fmtDate = (iso, opts) => { if (!iso) return ''; const d = new Date(iso.length === 10 ? iso + 'T12:00:00' : iso); return d.toLocaleDateString(undefined, opts || { day: 'numeric', month: 'short', year: 'numeric' }); };
const plural = (n, w) => `${n} ${w}${n === 1 ? '' : 's'}`;
const DAY_NAMES = { mon: 'Monday', tue: 'Tuesday', wed: 'Wednesday', thu: 'Thursday', fri: 'Friday', sat: 'Saturday', sun: 'Sunday' };
Object.assign(FP, { h, $, $$, uid, today, fmtDate, plural, DAY_NAMES });

/* ------------------------------------------------------------------ API client
   Same-origin only. The session lives in an httpOnly cookie the script cannot read; nothing sensitive
   is ever put in localStorage. Every mutating call carries the CSRF header the server requires. */
FP.api = async function api(method, path, body) {
  const opts = { method, credentials: 'same-origin', headers: { Accept: 'application/json' } };
  if (method !== 'GET') opts.headers['X-Requested-With'] = 'fitpulse';
  if (body !== undefined) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
  let res;
  try {
    res = await fetch('/api' + path, opts);
  } catch (e) {
    return { ok: false, status: 0, error: "Can't reach the FitPulse server. Check your connection and try again." };
  }
  let json = null;
  try { json = await res.json(); } catch (e) { /* non-JSON */ }
  if (res.ok && json && json.success !== false) return { ok: true, status: res.status, data: json.data };
  const out = { ok: false, status: res.status, error: (json && (json.error || json.detail)) || `Request failed (HTTP ${res.status}).`, fields: json && json.fields, data: json && json.data };
  if (res.status === 401 && FP.state.user && !path.startsWith('/auth/')) {
    FP.state.user = null; FP.toast('Your session has ended. Please sign in again.', 'error'); FP.go('/login');
  }
  return out;
};

/* ------------------------------------------------------------------ toasts */
FP.toast = function (msg, kind) {
  const el = document.createElement('div');
  el.className = 'toast' + (kind === 'error' ? ' error' : '');
  el.textContent = msg;
  $('#toasts').appendChild(el);
  setTimeout(() => el.remove(), kind === 'error' ? 7000 : 4000);
};

/* ------------------------------------------------------------------ icons (inline SVG, decorative) */
const ic = (d) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
FP.icons = {
  home: ic('<path d="M3 11 12 4l9 7"/><path d="M5 10v10h14V10"/>'),
  plan: ic('<rect x="4" y="4" width="16" height="17" rx="2"/><path d="M8 2v4M16 2v4M4 10h16"/>'),
  log: ic('<circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/>'),
  progress: ic('<path d="M4 19V5M4 19h16"/><path d="m7 15 4-4 3 3 5-6"/>'),
  goals: ic('<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>'),
  settings: ic('<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>'),
  history: ic('<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l3 2"/>'),
  pulse: '<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M5 17h5l3-7 5 13 3-6h6" fill="none" stroke="white" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
};
FP.brand = (href) => `<a class="brand" href="${href || '#/'}"><span class="mark">${FP.icons.pulse}</span>FitPulse</a>`;

FP.DISC_GLYPH = { gym: 'GY', swimming: 'SW', hiit: 'HI', hyrox: 'HX', running: 'RN', cycling: 'CY', calisthenics: 'CA', yoga: 'YO', mobility: 'MO', sports: 'SP', circuit: 'CI', bands: 'BD', home: 'HM', other: '··' };
FP.discLabel = (id) => { const c = FP.state.config; return (c && c.disciplines[id] && c.disciplines[id].label) || ({ other: 'Other' }[id]) || id; };

/* ------------------------------------------------------------------ banners */
FP.banner = (kind, title, body) => `<div class="banner ${kind}" role="${kind === 'danger' ? 'alert' : 'note'}"><span class="icon" aria-hidden="true"><span>${kind === 'ok' ? '✓' : '!'}</span></span><div><strong>${h(title)}</strong>${body ? `<p class="body small">${body}</p>` : ''}</div></div>`;

FP.systemBanners = function () {
  const s = FP.state.integrations;
  if (!s) return '';
  let out = '';
  if (s.planService.mode === 'mock') out += FP.banner('mock', 'Development mode: plans come from a labelled placeholder', "Maajith's processing system isn't connected on this deployment yet. Any plan you generate here is marked <em>Development mock</em> and is not a personalised recommendation.");
  if (s.planService.mode === 'unconfigured') out += FP.banner('warn', 'Plan generation is not connected yet', "You can complete your profile and log workouts. Plans will be available once Maajith's processing system is connected.");
  if (!s.database.durable) out += FP.banner('warn', 'Temporary storage on this deployment', 'No permanent database is configured, so accounts and data may be cleared when the server restarts.');
  return out ? `<div class="stack" style="margin-bottom:24px">${out}</div>` : '';
};

/* ------------------------------------------------------------------ routing */
FP.route = (pattern, access, render) => FP.routes.push({ pattern, access, render, keys: (pattern.match(/:\w+/g) || []).map((k) => k.slice(1)), re: pattern === '*' ? /(?!)/ : new RegExp('^' + pattern.replace(/:\w+/g, '([^/]+)') + '$') });
FP.go = (path) => { if (location.hash === '#' + path) FP.render(); else location.hash = path; };
FP.query = () => Object.fromEntries(new URLSearchParams((location.hash.split('?')[1]) || ''));

let leaveGuard = null;
FP.setLeaveGuard = (fn) => { leaveGuard = fn; };
window.addEventListener('beforeunload', (e) => { if (leaveGuard && leaveGuard()) { e.preventDefault(); e.returnValue = ''; } });

let lastHash = location.hash;
window.addEventListener('hashchange', () => {
  if (leaveGuard && leaveGuard() && !confirm('You have unsaved changes. Leave this page and discard them?')) {
    history.replaceState(null, '', lastHash); return;
  }
  leaveGuard = null; lastHash = location.hash; FP.render();
});

FP.render = async function () {
  const path = (location.hash.replace(/^#/, '').split('?')[0]) || '/';
  let match = null, params = {};
  for (const r of FP.routes) { const m = path.match(r.re); if (m) { match = r; r.keys.forEach((k, i) => { params[k] = decodeURIComponent(m[i + 1]); }); break; } }
  if (!match) match = FP.routes.find((r) => r.pattern === '*');
  const u = FP.state.user;
  if (match.access === 'guest' && u) return FP.go(u.onboardingComplete ? '/dashboard' : '/onboarding');
  if ((match.access === 'user' || match.access === 'onboarded') && !u) { FP.afterLogin = location.hash.slice(1); return FP.go('/login'); }
  if (match.access === 'onboarded' && u && !u.onboardingComplete) return FP.go('/onboarding');
  window.scrollTo(0, 0);
  try {
    await match.render(params);
  } catch (e) {
    console.error(e);
    $('#app').innerHTML = `<main id="main" class="wrap section"><h1>Something went wrong</h1><p class="muted">This page hit an unexpected error. Your data is safe.</p><a class="btn" href="#/">Go home</a></main>`;
  }
  const h1 = $('#main h1'); if (h1) { h1.setAttribute('tabindex', '-1'); document.title = h1.textContent + ' · FitPulse'; }
};

/* ------------------------------------------------------------------ layouts */
FP.publicLayout = function (inner) {
  const u = FP.state.user;
  $('#app').innerHTML = `
  <header class="topbar"><div class="inner">${FP.brand('#/')}
    <nav class="row" aria-label="Account">${u ? `<a class="btn small" href="#/dashboard">Open app</a>` : `<a class="btn ghost small" href="#/login">Sign in</a><a class="btn small" href="#/register">Create account</a>`}</nav>
  </div></header>
  <main id="main">${inner}</main>`;
};

const NAV = [['/dashboard', 'Dashboard', 'home'], ['/plan', 'My plan', 'plan'], ['/log', 'Log workout', 'log'], ['/workouts', 'History', 'history'], ['/progress', 'Progress', 'progress'], ['/goals', 'Goals', 'goals'], ['/settings', 'Settings', 'settings']];
const MOBILE_NAV = ['/dashboard', '/plan', '/log', '/progress', '/settings'];

FP.appLayout = function (active, inner) {
  const u = FP.state.user;
  const link = ([p, label, icon], cls) => `<a class="${cls}" href="#${p}" ${active === p ? 'aria-current="page"' : ''}>${FP.icons[icon]}<span>${label}</span></a>`;
  $('#app').innerHTML = `
  <div class="shell">
    <aside class="sidenav" aria-label="Main">
      ${FP.brand('#/dashboard')}
      <nav>${NAV.map((n) => link(n, 'navlink')).join('')}</nav>
      <div class="who"><div><strong>${h(u.name)}</strong></div><div class="tiny">${h(u.email)}</div>
        <button class="link-btn small" data-action="logout" style="margin-top:8px">Sign out</button></div>
    </aside>
    <div>
      <div class="mobile-top">${FP.brand('#/dashboard')}<a class="btn ghost small" href="#/workouts">History</a></div>
      <main id="main" class="main">${FP.systemBanners()}${inner}</main>
    </div>
  </div>
  <nav class="bottomnav" aria-label="Main">${NAV.filter((n) => MOBILE_NAV.includes(n[0])).map((n) => link(n, '')).join('')}</nav>`;
};

FP.pageHead = (title, sub, actions) => `<div class="page-head"><div><h1>${h(title)}</h1>${sub ? `<p>${sub}</p>` : ''}</div>${actions ? `<div class="row">${actions}</div>` : ''}</div>`;
FP.loading = (label) => `<div class="card flat" role="status"><div class="row"><span class="spinner" aria-hidden="true"></span><span>${h(label || 'Loading…')}</span></div></div>`;
FP.errorCard = (msg, retry) => `<div class="card flat">${FP.banner('danger', 'Could not load this', h(msg))}${retry ? `<div class="form-actions"><button class="btn secondary" data-action="retry">Try again</button></div>` : ''}</div>`;

document.addEventListener('click', async (e) => {
  const t = e.target.closest('[data-action]');
  if (!t) return;
  if (t.dataset.action === 'logout') {
    e.preventDefault();
    await FP.api('POST', '/auth/logout');
    FP.state.user = null; FP.state.profile = null; FP.setLeaveGuard(null);
    FP.toast('Signed out.'); FP.go('/');
  } else if (t.dataset.action === 'retry') { FP.render(); }
});

/* busy-button helper: prevents duplicate submissions */
FP.busy = async function (btn, fn) {
  if (btn.getAttribute('aria-busy') === 'true') return;
  const label = btn.innerHTML;
  btn.setAttribute('aria-busy', 'true'); btn.disabled = true;
  btn.innerHTML = `<span class="spinner" aria-hidden="true" style="width:16px;height:16px;border-width:2px"></span>${btn.dataset.busyLabel || 'Working…'}`;
  try { return await fn(); } finally { if (btn.isConnected) { btn.removeAttribute('aria-busy'); btn.disabled = false; btn.innerHTML = label; } }
};

/* show field errors returned by the API */
FP.showFieldErrors = function (form, fields) {
  $$('.error-text[data-for]', form).forEach((el) => el.remove());
  $$('[aria-invalid]', form).forEach((el) => el.removeAttribute('aria-invalid'));
  let first = null;
  Object.entries(fields || {}).forEach(([k, msg]) => {
    const input = form.querySelector(`[name="${CSS.escape(k)}"]`);
    const holder = input ? input.closest('.field, fieldset') : null;
    if (!holder) return;
    if (input) input.setAttribute('aria-invalid', 'true');
    const p = document.createElement('p'); p.className = 'error-text'; p.dataset.for = k; p.id = 'err-' + k.replace(/\W/g, '_'); p.textContent = msg;
    holder.appendChild(p);
    if (input) input.setAttribute('aria-describedby', p.id);
    if (!first) first = input;
  });
  if (first) first.focus();
};

FP.loadIntegrations = async function () {
  const r = await FP.api('GET', '/integrations/status');
  FP.state.integrations = r.ok ? r.data : null;
};
FP.loadConfig = async function () {
  if (FP.state.config) return true;
  const r = await FP.api('GET', '/config/onboarding');
  if (r.ok) FP.state.config = r.data;
  return r.ok;
};
FP.loadProfile = async function () {
  const r = await FP.api('GET', '/profile');
  if (r.ok) FP.state.profile = r.data;
  return r;
};

/* theme preference: a per-device convenience only */
FP.applyTheme = function () {
  let t = 'system';
  try { t = localStorage.getItem('fp_theme') || 'system'; } catch (e) { /* storage blocked */ }
  if (t === 'system') document.documentElement.removeAttribute('data-theme'); else document.documentElement.setAttribute('data-theme', t);
  return t;
};

FP.start = async function () {
  FP.applyTheme();
  const [me] = await Promise.all([FP.api('GET', '/auth/me'), FP.loadConfig(), FP.loadIntegrations()]);
  FP.state.user = me.ok && me.data ? me.data : null;
  FP.render();
};
document.addEventListener('DOMContentLoaded', () => FP.start());

/* ===== forms ===== */
/* Config-driven form engine: renders questionnaire fields from /api/config/onboarding and reads them back.
   Used by onboarding, goal management and profile editing, so new questions need no new UI code. */
'use strict';
(function () {
  const { h, $$ } = FP;
  const KG_LB = 2.20462;
  const F = FP.forms = {};

  F.visible = function (f, data) {
    const c = f.showIf; if (!c) return true;
    const v = data[c.field];
    if ('equals' in c) return v === c.equals;
    if ('in' in c) return c.in.includes(v);
    if ('includes' in c) return Array.isArray(v) && v.includes(c.includes);
    return !!v;
  };

  F.dependencies = function (fields) {
    const deps = new Set(['units']);
    fields.forEach((f) => { if (f.showIf) deps.add(f.showIf.field); if (f.excludeField) deps.add(f.excludeField); });
    return deps;
  };

  const opt = (type, name, o, checked, disabled) => `<label class="option"><input type="${type}" name="${h(name)}" value="${h(o.value)}" ${checked ? 'checked' : ''} ${disabled ? 'disabled' : ''}><span>${h(o.label)}</span></label>`;

  F.renderField = function (f, value, ctx) {
    const name = (ctx.prefix || '') + f.id;
    const id = 'q-' + name.replace(/\W/g, '_');
    const help = f.help ? `<p class="help" id="${id}-help">${h(f.help)}</p>` : '';
    const req = f.required ? ' <span class="muted small">(required)</span>' : '';
    const desc = f.help ? `aria-describedby="${id}-help"` : '';
    const imperial = ctx.units === 'imperial';
    switch (f.type) {
      case 'radio': case 'cards': {
        const cls = f.type === 'cards' ? 'cards-options' : 'options';
        const val = value == null ? f.default : value;
        return `<fieldset><legend>${h(f.label)}${req}</legend>${help}<div class="${cls}" role="radiogroup">${f.options.map((o) => opt('radio', name, o, String(val) === o.value)).join('')}</div></fieldset>`;
      }
      case 'multiselect': {
        const vals = Array.isArray(value) ? value : [];
        const excluded = f.excludeField ? ctx.data[f.excludeField] : null;
        const full = f.maxItems && vals.length >= f.maxItems;
        const hint = f.maxItems && f.minItems ? `<p class="help">Choose ${f.minItems}–${f.maxItems}.</p>` : '';
        return `<fieldset data-max="${f.maxItems || ''}"><legend>${h(f.label)}${req}</legend>${help}${hint}<div class="options">${f.options.filter((o) => o.value !== excluded).map((o) => opt('checkbox', name, o, vals.includes(o.value), full && !vals.includes(o.value))).join('')}</div></fieldset>`;
      }
      case 'select':
        return `<div class="field"><label for="${id}">${h(f.label)}${req}</label>${help}<select id="${id}" name="${h(name)}" ${desc}><option value="">Choose…</option>${f.options.map((o) => `<option value="${h(o.value)}" ${String(value) === o.value ? 'selected' : ''}>${h(o.label)}</option>`).join('')}</select></div>`;
      case 'boolean':
        return `<div class="field"><label class="check"><input type="checkbox" name="${h(name)}" ${value === true ? 'checked' : ''} ${desc}><span>${h(f.label)}</span></label>${help}</div>`;
      case 'textarea':
        return `<div class="field"><label for="${id}">${h(f.label)}${req}</label>${help}<textarea id="${id}" name="${h(name)}" maxlength="${f.maxLength || 500}" placeholder="${h(f.placeholder || '')}" ${desc}>${h(value || '')}</textarea></div>`;
      case 'date':
        return `<div class="field"><label for="${id}">${h(f.label)}${req}</label>${help}<input id="${id}" type="date" name="${h(name)}" value="${h(value || '')}" ${f.future ? `min="${FP.today()}"` : `max="${FP.today()}"`} ${desc}></div>`;
      case 'number': {
        if (f.unitKind === 'height' && imperial) {
          const totalIn = value ? value / 2.54 : null;
          const ft = totalIn != null ? Math.floor(totalIn / 12) : '';
          const inch = totalIn != null ? Math.round(totalIn - ft * 12) : '';
          return `<fieldset><legend>${h(f.label)}${req}</legend>${help}<div class="pair">
            <div class="input-unit"><input type="number" inputmode="numeric" name="${h(name)}__ft" value="${ft}" min="3" max="8" aria-label="Feet"><span class="unit">ft</span></div>
            <div class="input-unit"><input type="number" inputmode="numeric" name="${h(name)}__in" value="${inch}" min="0" max="11" aria-label="Inches"><span class="unit">in</span></div></div></fieldset>`;
        }
        let shown = value, unit = f.unit || '', min = f.min, max = f.max, step = f.step || 1;
        if (f.unitKind === 'weight' && imperial) { shown = value != null ? Math.round(value * KG_LB * 10) / 10 : ''; unit = 'lb'; min = f.min != null ? Math.floor(f.min * KG_LB) : undefined; max = f.max != null ? Math.ceil(f.max * KG_LB) : undefined; step = 0.1; }
        const input = `<input id="${id}" type="number" inputmode="decimal" name="${h(name)}" value="${shown == null ? (f.default != null ? f.default : '') : h(shown)}" ${min != null ? `min="${min}"` : ''} ${max != null ? `max="${max}"` : ''} step="${step}" data-kind="${f.unitKind || ''}" ${desc}>`;
        return `<div class="field"><label for="${id}">${h(f.label)}${req}</label>${help}${unit ? `<div class="input-unit">${input}<span class="unit">${h(unit)}</span></div>` : input}</div>`;
      }
      default:
        return `<div class="field"><label for="${id}">${h(f.label)}${req}</label>${help}<input id="${id}" type="text" name="${h(name)}" value="${h(value || '')}" maxlength="${f.maxLength || 200}" placeholder="${h(f.placeholder || '')}" ${desc}></div>`;
    }
  };

  F.renderFields = (fields, data, ctx) => fields.filter((f) => F.visible(f, data)).map((f) => F.renderField(f, data[f.id], { ...ctx, data })).join('');

  /* Read visible fields back into a plain object (metric units). Missing -> null so cleared answers are saved. */
  F.read = function (root, fields, ctx) {
    const out = {};
    const imperial = ctx.units === 'imperial';
    fields.forEach((f) => {
      const name = (ctx.prefix || '') + f.id;
      const els = $$(`[name="${CSS.escape(name)}"]`, root);
      if (f.type === 'number' && f.unitKind === 'height' && imperial) {
        const ft = root.querySelector(`[name="${CSS.escape(name)}__ft"]`), inch = root.querySelector(`[name="${CSS.escape(name)}__in"]`);
        if (!ft) return;
        const a = parseFloat(ft.value), b = parseFloat(inch.value || '0');
        out[f.id] = isNaN(a) ? null : Math.round(((a * 12) + (isNaN(b) ? 0 : b)) * 2.54 * 10) / 10;
        return;
      }
      if (!els.length) return;
      if (f.type === 'radio' || f.type === 'cards') { const c = els.find((e) => e.checked); out[f.id] = c ? c.value : null; }
      else if (f.type === 'multiselect') out[f.id] = els.filter((e) => e.checked).map((e) => e.value);
      else if (f.type === 'boolean') out[f.id] = els[0].checked;
      else if (f.type === 'number') {
        const n = parseFloat(els[0].value);
        if (isNaN(n)) out[f.id] = null;
        else out[f.id] = (f.unitKind === 'weight' && imperial) ? Math.round(n / KG_LB * 10) / 10 : n;
      } else out[f.id] = els[0].value.trim() || null;
    });
    return out;
  };

  /* Client-side required check for quick feedback; the server re-validates everything. */
  F.requiredErrors = function (fields, data, prefix) {
    const errs = {};
    fields.forEach((f) => {
      if (!F.visible(f, data)) return;
      const v = data[f.id];
      const empty = v == null || v === '' || (Array.isArray(v) && !v.length);
      if (f.required && empty) errs[(prefix || '') + f.id] = `${f.label.replace(/ \(optional.*\)$/, '')} is required.`;
      else if (f.mustBeTrue && v !== true) errs[(prefix || '') + f.id] = 'Please confirm to continue.';
      else if (f.type === 'multiselect' && f.minItems && Array.isArray(v) && v.length && v.length < f.minItems) errs[(prefix || '') + f.id] = `Choose at least ${f.minItems}.`;
      else if (f.type === 'number' && v != null && ((f.min != null && v < f.min) || (f.max != null && v > f.max))) errs[(prefix || '') + f.id] = `${f.label} must be between ${f.min} and ${f.max}${f.unit ? ' ' + f.unit : ''}.`;
    });
    return errs;
  };

  /* keep multiselect maxItems enforced live */
  document.addEventListener('change', (e) => {
    const fs = e.target.closest('fieldset[data-max]');
    if (!fs || !fs.dataset.max) return;
    const max = +fs.dataset.max;
    const boxes = $$('input[type=checkbox]', fs);
    const n = boxes.filter((b) => b.checked).length;
    boxes.forEach((b) => { if (!b.checked) b.disabled = n >= max; });
  });

  /* human-readable value for summaries */
  F.display = function (f, v, units) {
    if (v == null || v === '' || (Array.isArray(v) && !v.length)) return '—';
    const lab = (x) => { const o = (f.options || []).find((o) => o.value === String(x)); return o ? o.label : x; };
    if (f.type === 'multiselect') return v.map(lab).join(', ');
    if (f.options) return lab(v);
    if (f.type === 'boolean') return v ? 'Yes' : 'No';
    if (f.type === 'date') return FP.fmtDate(v);
    if (f.type === 'number') {
      if (f.unitKind === 'weight') return units === 'imperial' ? `${Math.round(v * KG_LB * 10) / 10} lb` : `${v} kg`;
      if (f.unitKind === 'height') { if (units === 'imperial') { const t = v / 2.54; const ft = Math.floor(t / 12); return `${ft} ft ${Math.round(t - ft * 12)} in`; } return `${v} cm`; }
      return `${v}${f.unit ? ' ' + f.unit : ''}`;
    }
    return String(v);
  };

  F.findField = function (id) {
    for (const s of FP.state.config.steps) for (const f of s.fields) if (f.id === id) return f;
    return null;
  };
})();

/* ===== public ===== */
/* Public screens: landing, sign-in, registration, password reset, 404. */
'use strict';
(function () {
  const { h, $, api, route } = { ...FP, route: FP.route };

  /* ------------------------------------------------------------------ landing */
  route('/', 'public', () => {
    const discs = FP.state.config ? Object.entries(FP.state.config.disciplines) : [];
    FP.publicLayout(`
      <section class="wrap hero">
        <div>
          <p class="eyebrow">Personal training plans</p>
          <h1>A plan that fits your goals, your week and your kit.</h1>
          <p class="lead">Tell FitPulse what you're training for, when you can train and what equipment you have. Your answers go to the FitPulse processing system, which builds the plan. You follow it, log each session and see your real progress in one place.</p>
          <div class="row" style="margin-top:24px">
            <a class="btn" href="#/register">Create your free account</a>
            <a class="btn secondary" href="#/login">Sign in</a>
          </div>
          <p class="small muted" style="margin-top:16px">Free to use. No card required. You can export or delete your data at any time.</p>
        </div>
        <div class="hero-visual" aria-label="Example of a plan session layout">
          <div class="row between"><span class="day-pill">Tuesday</span><span class="badge">Example layout</span></div>
          <h3 style="margin-top:8px">Strength session · 45 min</h3>
          <div class="block" style="margin-top:12px">
            <div class="block-head"><h4>Main lifts</h4><span class="badge">3 exercises</span></div>
            <div class="table-wrap"><table><thead><tr><th>Exercise</th><th class="num">Sets</th><th class="num">Reps</th></tr></thead>
              <tbody><tr><td>Squat</td><td class="num">3</td><td class="num">8–10</td></tr><tr><td>Bench press</td><td class="num">3</td><td class="num">8–10</td></tr><tr><td>Cable row</td><td class="num">3</td><td class="num">10–12</td></tr></tbody></table></div>
          </div>
          <p class="tiny muted" style="margin:12px 0 0">Illustration of how sessions are displayed — not a real recommendation.</p>
        </div>
      </section>
      <section class="section alt"><div class="wrap">
        <h2>How it works</h2>
        <ol class="steps-list" style="margin-top:24px">
          <li><h3>Tell us about you</h3><p class="muted">A guided set of questions: goals, timeline, experience, schedule, equipment and anything to work around. Save and come back any time.</p></li>
          <li><h3>Your plan is built</h3><p class="muted">Your profile is sent securely to the FitPulse processing system, which analyses it and returns a structured plan. Every plan shows where it came from.</p></li>
          <li><h3>Train and track</h3><p class="muted">Follow sessions laid out for each training style, log what you did, and watch your own numbers — never invented ones.</p></li>
        </ol>
      </div></section>
      <section class="section"><div class="wrap">
        <h2>Built for how you actually train</h2>
        <p class="muted">Choose up to four training styles. Each one gets its own short questionnaire and its own session layout.</p>
        <div class="disc-grid" style="margin-top:20px">${discs.map(([id, d]) => `<div class="disc-tile"><span class="glyph" aria-hidden="true">${FP.DISC_GLYPH[id] || ''}</span>${h(d.label)}</div>`).join('')}</div>
      </div></section>
      <section class="section alt"><div class="wrap grid two">
        <div><h2>Your data stays yours</h2><p class="muted">Passwords are hashed, sessions use secure cookies, and only you can see your profile, plans and progress. The processing system receives what it needs to plan your training — not your name or e-mail.</p></div>
        <div><h2>Safe by design</h2><p class="muted">FitPulse gives general fitness guidance, not medical advice. It flags weight targets that are too fast, and it will never promise guaranteed results. Talk to a healthcare professional if you have a medical condition or injury.</p></div>
      </div></section>
      <footer class="footer"><div class="wrap row between"><span>FitPulse · user platform by Yasash · processing by Maajith</span><a href="#/login">Sign in</a></div></footer>`);
  });

  /* ------------------------------------------------------------------ auth helpers */
  function authPage(title, sub, form, foot) {
    FP.publicLayout(`<div class="auth-shell"><div class="card auth-card">
      <h1 style="font-size:1.7rem">${h(title)}</h1><p class="muted">${sub}</p>
      <div id="form-error" class="form-error" aria-live="assertive"></div>
      ${form}
      ${foot ? `<p class="small muted" style="margin-top:20px">${foot}</p>` : ''}</div></div>`);
  }
  const errBox = (msg) => { $('#form-error').innerHTML = msg ? FP.banner('danger', msg) : ''; };
  const field = (name, label, type, extra) => `<div class="field"><label for="f-${name}">${label}</label><input id="f-${name}" name="${name}" type="${type}" ${extra || ''}></div>`;

  async function afterAuth(user) {
    FP.state.user = user;
    await FP.loadIntegrations();
    const next = FP.afterLogin; FP.afterLogin = null;
    FP.go(!user.onboardingComplete ? '/onboarding' : (next && next !== '/login' ? next : '/dashboard'));
  }

  /* ------------------------------------------------------------------ sign in */
  route('/login', 'guest', () => {
    authPage('Welcome back', 'Sign in to see your plan and progress.', `
      <form id="login" novalidate>
        ${field('email', 'E-mail', 'email', 'autocomplete="email" required')}
        ${field('password', 'Password', 'password', 'autocomplete="current-password" required')}
        <div class="form-actions"><button class="btn block" type="submit" data-busy-label="Signing in…">Sign in</button></div>
        <p class="small" style="margin-top:12px"><a href="#/forgot">Forgot your password?</a></p>
      </form>`, `New to FitPulse? <a href="#/register">Create an account</a>`);
    $('#login').addEventListener('submit', (e) => {
      e.preventDefault();
      const f = e.target, btn = f.querySelector('button[type=submit]');
      FP.busy(btn, async () => {
        errBox('');
        const email = f.email.value.trim(), password = f.password.value;
        if (!email || !password) return errBox('Enter your e-mail and password.');
        const r = await api('POST', '/auth/login', { email, password });
        if (!r.ok) { f.password.value = ''; return errBox(r.status === 422 ? 'Enter a valid e-mail address.' : r.error); }
        await afterAuth(r.data);
      });
    });
  });

  /* ------------------------------------------------------------------ register */
  route('/register', 'guest', () => {
    authPage('Create your account', 'It takes about five minutes to set up your profile. You can save and finish later.', `
      <form id="register" novalidate>
        ${field('name', 'First name or nickname', 'text', 'autocomplete="given-name" maxlength="80" required')}
        ${field('email', 'E-mail', 'email', 'autocomplete="email" required')}
        <div class="field"><label for="f-password">Password</label><input id="f-password" name="password" type="password" autocomplete="new-password" required aria-describedby="pw-help">
          <p class="help" id="pw-help">At least 10 characters, with a letter and a number.</p></div>
        <div class="form-actions"><button class="btn block" type="submit" data-busy-label="Creating account…">Create account</button></div>
      </form>`, `Already have an account? <a href="#/login">Sign in</a>`);
    $('#register').addEventListener('submit', (e) => {
      e.preventDefault();
      const f = e.target, btn = f.querySelector('button[type=submit]');
      FP.busy(btn, async () => {
        errBox('');
        const body = { name: f.name.value.trim(), email: f.email.value.trim(), password: f.password.value };
        const local = {};
        if (!body.name) local.name = 'Enter a name.';
        if (!/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(body.email)) local.email = 'Enter a valid e-mail address.';
        if (body.password.length < 10) local.password = 'Use at least 10 characters.';
        if (Object.keys(local).length) return FP.showFieldErrors(f, local);
        FP.showFieldErrors(f, {});
        const r = await api('POST', '/auth/register', body);
        if (!r.ok) return r.fields ? FP.showFieldErrors(f, r.fields) : errBox(r.error);
        FP.toast('Account created. Let’s set up your profile.');
        await afterAuth(r.data);
      });
    });
  });

  /* ------------------------------------------------------------------ forgot / reset */
  route('/forgot', 'guest', () => {
    authPage('Reset your password', 'Enter the e-mail you signed up with.', `
      <form id="forgot" novalidate>${field('email', 'E-mail', 'email', 'autocomplete="email" required')}
        <div class="form-actions"><button class="btn block" type="submit" data-busy-label="Sending…">Send reset link</button></div></form>
      <div id="forgot-result"></div>`, `<a href="#/login">Back to sign in</a>`);
    $('#forgot').addEventListener('submit', (e) => {
      e.preventDefault();
      const f = e.target, btn = f.querySelector('button[type=submit]');
      FP.busy(btn, async () => {
        errBox('');
        const r = await api('POST', '/auth/forgot', { email: f.email.value.trim() });
        if (!r.ok) return errBox(r.status === 422 ? 'Enter a valid e-mail address.' : r.error);
        const d = r.data;
        $('#forgot-result').innerHTML = `<div style="margin-top:16px">${FP.banner(d.emailDelivery ? 'ok' : 'warn', d.emailDelivery ? 'Check your inbox' : 'E-mail is not set up here', h(d.message))}
          ${d.devResetLink ? `<p class="small" style="margin-top:12px">Local development link: <a href="${h(d.devResetLink)}">open reset page</a></p>` : ''}</div>`;
      });
    });
  });

  route('/reset', 'public', () => {
    const token = FP.query().token || '';
    authPage('Choose a new password', 'This will sign you out on every device.', token ? `
      <form id="reset" novalidate>
        <div class="field"><label for="f-password">New password</label><input id="f-password" name="password" type="password" autocomplete="new-password" required aria-describedby="pw-help"><p class="help" id="pw-help">At least 10 characters, with a letter and a number.</p></div>
        ${field('confirm', 'Confirm new password', 'password', 'autocomplete="new-password" required')}
        <div class="form-actions"><button class="btn block" type="submit" data-busy-label="Saving…">Save new password</button></div></form>`
      : FP.banner('danger', 'This reset link is incomplete.', 'Request a new link from the sign-in page.'), `<a href="#/login">Back to sign in</a>`);
    const f = $('#reset'); if (!f) return;
    f.addEventListener('submit', (e) => {
      e.preventDefault();
      FP.busy(f.querySelector('button[type=submit]'), async () => {
        errBox('');
        if (f.password.value !== f.confirm.value) return FP.showFieldErrors(f, { confirm: 'Passwords do not match.' });
        const r = await api('POST', '/auth/reset', { token, password: f.password.value });
        if (!r.ok) return errBox(r.error);
        FP.state.user = null;
        FP.toast('Password updated. Sign in with your new password.');
        FP.go('/login');
      });
    });
  });

  /* ------------------------------------------------------------------ 404 */
  route('*', 'public', () => {
    FP.publicLayout(`<section class="wrap section"><h1>Page not found</h1><p class="muted">That page doesn't exist.</p><a class="btn" href="${FP.state.user ? '#/dashboard' : '#/'}">Go back</a></section>`);
  });
})();

/* ===== onboarding ===== */
/* Guided onboarding — multi-step, config-driven, saved to the server after every step. */
'use strict';
(function () {
  const { h, $, $$, api, route } = FP;
  const F = FP.forms;

  function steps() { return [...FP.state.config.steps, { id: 'review', title: 'Review', description: 'Check your answers before your plan is requested.', fields: [] }]; }
  function stepFields(step, data) {
    if (step.dynamic === 'disciplines') return (data.disciplines || []).map((d) => ({ d, fields: (FP.state.config.disciplines[d] || {}).fields || [] }));
    return step.fields;
  }

  let draft = null, version = null, dirty = false;

  async function ensureLoaded() {
    if (!(await FP.loadConfig())) return 'Could not load the questionnaire.';
    const r = await FP.loadProfile();
    if (!r.ok) return r.error;
    draft = JSON.parse(JSON.stringify(FP.state.profile.data || {}));
    version = FP.state.profile.version;
    dirty = false;
    return null;
  }

  function firstIncomplete() {
    for (const s of steps()) {
      if (s.id === 'review') return 'review';
      if (s.dynamic) continue;
      if (Object.keys(F.requiredErrors(s.fields, draft)).length) return s.id;
    }
    return 'review';
  }

  route('/onboarding', 'user', async () => {
    const err = await ensureLoaded();
    if (err) return shell('', FP.errorCard(err, true));
    FP.go('/onboarding/' + (FP.state.profile.onboardingComplete ? 'basics' : firstIncomplete()));
  });

  function shell(progressHtml, body) {
    const editing = FP.state.profile && FP.state.profile.onboardingComplete;
    $('#app').innerHTML = `
      <header class="topbar"><div class="inner">${FP.brand(editing ? '#/dashboard' : '#/onboarding')}
        <div class="row">${editing ? '<a class="btn ghost small" href="#/settings">Back to settings</a>' : '<span class="small muted">Answers save after each step</span>'}
        <button class="btn ghost small" data-action="logout">Sign out</button></div></div></header>
      <main id="main" class="onb">${progressHtml}${body}</main>`;
  }

  route('/onboarding/:step', 'user', async ({ step }) => {
    if (!draft || !FP.state.profile) { const err = await ensureLoaded(); if (err) return shell('', FP.errorCard(err, true)); }
    const all = steps();
    const idx = all.findIndex((s) => s.id === step);
    if (idx < 0) return FP.go('/onboarding');
    const s = all[idx];
    if (s.dynamic && !(draft.disciplines || []).length) return FP.go('/onboarding/disciplines');
    const editing = FP.state.profile.onboardingComplete;
    const pct = Math.round((idx / (all.length - 1)) * 100);
    const progress = `<div class="progress" role="progressbar" aria-label="Onboarding progress" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}"><span style="width:${pct}%"></span></div>
      <div class="stepper-meta"><span>Step ${idx + 1} of ${all.length}</span><span>${h(s.title)}</span></div>`;
    if (s.id === 'review') return renderReview(progress, idx);
    shell(progress, `
      <div class="card">
        <h1 style="font-size:1.6rem">${h(s.title)}</h1>
        <p class="muted">${h(s.description || '')}</p>
        <div id="form-error" aria-live="assertive"></div>
        <form id="step-form" novalidate><div id="step-fields"></div>
          ${s.id === 'constraints' ? `<div class="banner info disclaimer" style="margin-top:20px"><span class="icon" aria-hidden="true"><span>i</span></span><div class="body">${h(FP.state.config.disclaimer)}</div></div>` : ''}
          <div class="form-actions">
            ${idx > 0 ? '<button type="button" class="btn secondary" id="back">Back</button>' : ''}
            <button type="submit" class="btn" data-busy-label="Saving…">${editing ? 'Save' : 'Save and continue'}</button>
            ${editing ? `<a class="btn ghost" href="#/onboarding/review">Review all</a>` : ''}
          </div>
        </form>
      </div>`);
    const holder = $('#step-fields');
    const ctx = () => ({ units: draft.units || 'metric' });
    const paint = () => {
      if (s.dynamic) {
        holder.innerHTML = stepFields(s, draft).map(({ d, fields }) => {
          const answers = (draft.disciplineDetails || {})[d] || {};
          return `<section class="disc-section" aria-labelledby="h-${d}"><h2 id="h-${d}" style="font-size:1.15rem">${h(FP.discLabel(d))}</h2>${F.renderFields(fields, answers, { ...ctx(), prefix: d + '.' })}</section>`;
        }).join('');
      } else holder.innerHTML = F.renderFields(s.fields, draft, ctx());
    };
    const collect = () => {
      if (s.dynamic) {
        const details = { ...(draft.disciplineDetails || {}) };
        stepFields(s, draft).forEach(({ d, fields }) => { details[d] = { ...(details[d] || {}), ...F.read(holder, fields, { ...ctx(), prefix: d + '.' }) }; });
        draft.disciplineDetails = details;
      } else Object.assign(draft, F.read(holder, s.fields, ctx()));
    };
    paint();
    const deps = s.dynamic ? new Set() : F.dependencies(s.fields);
    holder.addEventListener('input', () => { dirty = true; });
    holder.addEventListener('change', (e) => {
      dirty = true;
      const name = e.target.name;
      if (deps.has(name)) {
        collect(); paint();
        const again = holder.querySelector(`[name="${CSS.escape(name)}"][value="${CSS.escape(e.target.value)}"]`) || holder.querySelector(`[name="${CSS.escape(name)}"]`);
        if (again) again.focus();
      }
    });
    FP.setLeaveGuard(() => dirty);
    const back = $('#back');
    if (back) back.addEventListener('click', () => { collect(); save(false).then((ok) => { if (ok !== false) FP.go('/onboarding/' + all[idx - 1].id); }); });
    $('#step-form').addEventListener('submit', (e) => {
      e.preventDefault();
      FP.busy(e.submitter || $('#step-form button[type=submit]'), async () => {
        collect();
        const local = s.dynamic ? {} : F.requiredErrors(s.fields, draft);
        if (Object.keys(local).length) { FP.showFieldErrors($('#step-form'), local); return; }
        const ok = await save(true);
        if (!ok) return;
        if (editing) { FP.toast('Saved.'); return; }
        let next = idx + 1;
        if (all[next].dynamic && !(draft.disciplines || []).length) next++;
        FP.go('/onboarding/' + all[next].id);
      });
    });

    async function save(strict) {
      $('#form-error').innerHTML = '';
      const r = await api('PUT', '/profile', { data: draft, version });
      if (r.status === 409 && r.data) {
        $('#form-error').innerHTML = FP.banner('warn', 'Your profile was changed in another tab or device.', 'Choose which version to keep.') +
          `<div class="row" style="margin:12px 0 20px"><button type="button" class="btn small" id="keep-mine">Keep my answers</button><button type="button" class="btn secondary small" id="load-latest">Load the latest version</button></div>`;
        $('#keep-mine').onclick = async () => { version = r.data.version; const again = await save(strict); if (again) FP.toast('Saved your answers.'); };
        $('#load-latest').onclick = () => { draft = JSON.parse(JSON.stringify(r.data.data)); version = r.data.version; dirty = false; FP.state.profile = r.data; paint(); $('#form-error').innerHTML = ''; };
        return false;
      }
      if (!r.ok) {
        if (r.fields) FP.showFieldErrors($('#step-form'), r.fields);
        $('#form-error').innerHTML = FP.banner('danger', r.error);
        return false;
      }
      FP.state.profile = r.data; version = r.data.version; dirty = false;
      draft = JSON.parse(JSON.stringify(r.data.data));
      const stepIds = new Set(s.dynamic ? [] : s.fields.map((f) => f.id));
      const mine = Object.fromEntries(Object.entries(r.data.fieldErrors || {}).filter(([k]) => stepIds.has(k) || (s.dynamic && k.includes('.'))));
      if (strict && Object.keys(mine).length) { paint(); FP.showFieldErrors($('#step-form'), mine); return false; }
      return true;
    }
  });

  function renderReview(progress, idx) {
    const all = steps();
    const units = draft.units || 'metric';
    const sections = all.filter((s) => s.id !== 'review').map((s) => {
      let rows = '';
      if (s.dynamic) {
        rows = (draft.disciplines || []).map((d) => {
          const fields = (FP.state.config.disciplines[d] || {}).fields || [];
          const ans = (draft.disciplineDetails || {})[d] || {};
          const parts = fields.filter((f) => ans[f.id] != null && ans[f.id] !== '').map((f) => `${h(f.label.replace(/ \(optional.*\)$/, ''))}: ${h(F.display(f, ans[f.id], units))}`);
          return `<dt>${h(FP.discLabel(d))}</dt><dd>${parts.length ? parts.join('<br>') : '<span class="muted">No details given</span>'}</dd>`;
        }).join('');
      } else {
        rows = s.fields.filter((f) => F.visible(f, draft) && f.id !== 'disclaimerAccepted').map((f) => `<dt>${h(f.label.replace(/ \(optional.*\)$/, ''))}</dt><dd>${h(F.display(f, draft[f.id], units))}</dd>`).join('');
      }
      if (!rows) return '';
      return `<section class="card flat review" style="margin-top:16px"><div class="row between"><h2 style="font-size:1.1rem;margin:0">${h(s.title)}</h2><a class="btn ghost small" href="#/onboarding/${s.id}" aria-label="Edit ${h(s.title)}">Edit</a></div><dl style="margin-top:12px">${rows}</dl></section>`;
    }).join('');
    const editing = FP.state.profile.onboardingComplete;
    shell(progress, `
      <h1 style="font-size:1.6rem">Review your answers</h1>
      <p class="muted">This is what will be sent to the processing system to build your plan (your name and e-mail are not included).</p>
      <div id="form-error" aria-live="assertive"></div>
      ${draft.healthCheck === 'unsure' ? FP.banner('warn', 'Consider a health check first', 'You said you are not sure whether a condition affects your exercise. FitPulse will still work, but please speak to a healthcare professional before starting anything strenuous.') : ''}
      ${sections}
      <div class="form-actions">
        <a class="btn secondary" href="#/onboarding/${all[idx - 1].id}">Back</a>
        <button class="btn" id="finish" data-busy-label="Checking…">${editing ? 'Done' : 'Finish and continue'}</button>
      </div>`);
    $('#finish').addEventListener('click', (e) => FP.busy(e.currentTarget, async () => {
      if (editing) return FP.go('/settings');
      const r = await api('POST', '/profile/complete');
      if (!r.ok) {
        const list = Object.entries(r.fields || {}).map(([k, msg]) => {
          const stepId = (all.find((s) => s.fields.some((f) => f.id === k)) || {}).id || (k.includes('.') ? 'discipline_details' : 'basics');
          return `<li><a href="#/onboarding/${stepId}">${h(msg)}</a></li>`;
        }).join('');
        $('#form-error').innerHTML = FP.banner('danger', r.error, list ? `<ul style="margin:6px 0 0;padding-left:18px">${list}</ul>` : '');
        return;
      }
      FP.state.profile = r.data;
      FP.state.user.onboardingComplete = true;
      FP.toast('Profile complete.');
      FP.go('/plan/new');
    }));
  }
})();

/* ===== plans ===== */
/* Plans: request a plan, show the result with discipline-specific layouts, session detail. */
'use strict';
(function () {
  const { h, $, $$, api, route, plural } = FP;

  /* ------------------------------------------------------------------ shared bits */
  FP.sourceBadge = (p) => p.isMock
    ? '<span class="badge mock"><span class="dot"></span>Development mock — not a real recommendation</span>'
    : `<span class="badge ok"><span class="dot"></span>Generated by Maajith's processing system</span>`;

  const secs = (s) => { if (s == null) return ''; if (s < 60) return `${s}s`; const m = Math.floor(s / 60), r = s % 60; return r ? `${m}m ${r}s` : `${m} min`; };
  const dist = (m) => m == null ? '' : (m >= 1000 ? `${(m / 1000).toFixed(m % 1000 ? 1 : 0)} km` : `${m} m`);

  function energyCard(e) {
    if (!e) return '';
    if (e.status !== 'ok') {
      return `<div class="card flat"><h3>Energy targets</h3><p class="muted small">${h(e.reason || 'Not available.')}</p><p class="tiny muted">Source: ${h(e.source)}</p></div>`;
    }
    const c = e.calories || {}, g = e.goalPlan, m = c.macros || {};
    const safety = g ? `<span class="badge ${g.safety === 'Unsafe' || g.safety === 'Aggressive' ? 'danger' : g.safety === 'Safe' || g.safety === 'Gentle' ? 'ok' : 'info'}">${h(g.safety)} pace</span>` : '';
    return `<div class="card flat"><div class="row between"><h3 style="margin:0">Energy targets</h3>${safety}</div>
      <div class="grid four" style="margin-top:16px">
        ${c.tdee ? `<div class="kpi"><span class="value">${h(c.tdee)}</span><span class="label">Maintenance kcal/day</span></div>` : ''}
        ${(g ? g.dailyCalorieTarget : c.targetCalories) ? `<div class="kpi"><span class="value">${h(g ? g.dailyCalorieTarget : c.targetCalories)}</span><span class="label">Suggested kcal/day</span></div>` : ''}
        ${m.proteinGrams ? `<div class="kpi"><span class="value">${h(m.proteinGrams)} g</span><span class="label">Protein/day</span></div>` : ''}
        ${g && g.weeklyChangeKg != null ? `<div class="kpi"><span class="value">${g.weeklyChangeKg > 0 ? '+' : ''}${h(g.weeklyChangeKg)} kg</span><span class="label">Planned change/week</span></div>` : ''}
      </div>
      ${e.goalPlanError ? `<p class="small muted" style="margin:12px 0 0">${h(e.goalPlanError)}</p>` : ''}
      ${g && g.advice ? `<p class="small" style="margin:12px 0 0">${h(g.advice)}${g.recommendedWeeks && (g.safety === 'Unsafe' || g.safety === 'Aggressive') ? ` A safer timeframe is about ${h(Math.ceil(g.recommendedWeeks))} weeks.` : ''}</p>` : ''}
      <p class="tiny muted" style="margin:10px 0 0">Calculated by ${h(e.source)} from your profile. Estimates only — individual needs vary.</p></div>`;
  }
  FP.energyCard = energyCard;

  /* discipline-aware block rendering */
  function renderBlock(b, discipline) {
    const items = b.items || [];
    const meta = [];
    if (b.rounds) meta.push(`${b.rounds} rounds`);
    if (b.workSec) meta.push(`${b.workSec}s work`);
    if (b.restSec) meta.push(`${b.restSec}s rest`);
    let inner = '';
    if (b.type === 'stations') {
      inner = `<ol class="station-list">${items.map((it, i) => `<li><span class="station-no" aria-hidden="true">${i + 1}</span><div><strong>${h(it.name)}</strong> <span class="muted small">${[dist(it.distanceM), it.reps ? it.reps + ' reps' : '', it.load || ''].filter(Boolean).map(h).join(' · ')}</span></div></li>`).join('')}</ol>`;
    } else if (b.type === 'flow') {
      inner = `<div class="flow-list">${items.map((it) => `<div class="flow-item"><strong>${h(it.name)}</strong><div class="small muted">${[it.durationSec ? 'Hold ' + secs(it.durationSec) : '', it.sets ? it.sets + ' × ' + (it.reps || '') : ''].filter(Boolean).map(h).join(' · ')}</div></div>`).join('')}</div>`;
    } else {
      if ((b.type === 'intervals' || b.type === 'circuit') && b.rounds && b.workSec) {
        const n = Math.min(b.rounds * Math.max(items.length, 1), 40);
        inner += `<div class="interval-strip" aria-hidden="true">${Array.from({ length: n }, () => `<span class="w" style="width:${Math.max(8, b.workSec / 4)}px"></span>${b.restSec ? `<span class="r" style="width:${Math.max(6, b.restSec / 4)}px"></span>` : ''}`).join('')}</div>`;
      }
      const cols = [['sets', 'Sets', (v) => v], ['reps', 'Reps', (v) => v], ['load', 'Load', (v) => v], ['distanceM', 'Distance', dist], ['durationSec', 'Time', secs], ['stroke', 'Stroke', (v) => v], ['pace', 'Pace', (v) => v], ['zone', 'Zone', (v) => v], ['restSec', 'Rest', secs]]
        .filter(([k]) => items.some((it) => it[k] != null && it[k] !== ''));
      inner += `<div class="table-wrap"><table><thead><tr><th scope="col">${discipline === 'swimming' ? 'Set' : 'Exercise'}</th>${cols.map(([, l]) => `<th scope="col" class="num">${l}</th>`).join('')}</tr></thead>
        <tbody>${items.map((it) => `<tr><td>${h(it.name)}${it.notes ? `<div class="tiny muted">${h(it.notes)}</div>` : ''}</td>${cols.map(([k, , f]) => `<td class="num">${it[k] != null ? h(f(it[k])) : '—'}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
      if (discipline === 'swimming') {
        const total = items.reduce((a, it) => a + (it.distanceM || 0) * (it.sets || 1), 0);
        if (total) meta.push(`${dist(total)} total`);
      }
    }
    return `<section class="block"><div class="block-head"><h4>${h(b.name)}</h4>${meta.length ? `<span class="small muted">${meta.map(h).join(' · ')}</span>` : ''}</div>${inner}</section>`;
  }
  FP.renderBlock = renderBlock;

  function sessionCard(planId, s, done) {
    return `<a class="card card-link session-card" href="#/session/${h(planId)}/${h(s.id)}">
      <div class="meta"><span class="day-pill">${h(FP.DAY_NAMES[s.day] || s.day || 'Any day')}</span>${done ? '<span class="done-mark">✓ Logged</span>' : ''}</div>
      <h3 style="margin:0">${h(s.title)}</h3>
      <div class="meta small muted"><span>${h(FP.discLabel(s.discipline))}</span>${s.durationMin ? `<span>· ${h(s.durationMin)} min</span>` : ''}${s.intensity ? `<span>· ${h(s.intensity)}</span>` : ''}</div>
    </a>`;
  }
  FP.sessionCard = sessionCard;

  FP.currentWeek = (p) => { const start = new Date(p.createdAt); const w = Math.floor((Date.now() - start.getTime()) / (7 * 864e5)) + 1; return Math.max(1, w); };

  /* ------------------------------------------------------------------ request a plan */
  route('/plan/new', 'onboarded', async () => {
    FP.appLayout('/plan', FP.pageHead('Get your plan', 'Your saved profile is sent to the processing system, which builds the plan.') + FP.loading());
    await FP.loadIntegrations();
    const pr = await FP.loadProfile();
    if (!pr.ok) return ($('#main').innerHTML = FP.errorCard(pr.error, true));
    const mode = FP.state.integrations ? FP.state.integrations.planService.mode : 'unknown';
    const d = FP.state.profile.data;
    const F = FP.forms;
    const summaryRow = (id) => { const f = F.findField(id); return f ? `<dt>${h(f.label.replace(/ \(optional.*\)$/, ''))}</dt><dd>${h(F.display(f, d[id], d.units))}</dd>` : ''; };
    $('#main').innerHTML = FP.systemBanners() + FP.pageHead('Get your plan', 'Your saved profile is sent to the processing system, which builds the plan.') + `
      <div class="grid two">
        <div class="card review"><h2 style="font-size:1.15rem">What will be sent</h2>
          <dl>${['primaryGoal', 'timeline', 'experienceLevel', 'disciplines', 'daysPerWeek', 'sessionMinutes', 'locations'].map(summaryRow).join('')}</dl>
          <p class="small muted" style="margin-top:12px">Plus the rest of your questionnaire answers and your age, height and weight. Your name, e-mail and date of birth are not sent. <a href="#/onboarding/review">Review or edit everything</a></p></div>
        <div class="card"><h2 style="font-size:1.15rem">Where your plan comes from</h2>
          ${mode === 'live' ? FP.banner('ok', "Connected to Maajith's processing system", 'Your plan will be generated by his system and shown exactly as returned.')
            : mode === 'mock' ? FP.banner('mock', 'Development mock in use', "The real processing system isn't connected here yet. You'll get a clearly labelled placeholder plan made from fixed templates — useful for trying the app, not for training advice.")
            : FP.banner('warn', 'Plan generation is not connected yet', "Maajith's processing system isn't configured on this deployment, so a plan can't be generated right now. Your profile is saved.")}
          <p class="small muted" style="margin-top:16px">Energy targets are calculated separately by the FitPulse API (Maajith) when you share the details it needs.</p>
          <div id="gen-error" aria-live="assertive"></div>
          <div class="form-actions"><button class="btn" id="generate" data-busy-label="Requesting your plan…" ${mode === 'unconfigured' ? 'disabled' : ''}>Generate my plan</button></div>
          <ul class="loading-steps" id="gen-steps" hidden>
            <li data-i="0"><span class="spinner" aria-hidden="true" style="width:14px;height:14px;border-width:2px"></span>Sending your profile securely</li>
            <li data-i="1">Waiting for the processing system</li>
            <li data-i="2">Checking the plan matches the agreed format</li></ul>
        </div>
      </div>`;
    const key = 'plan-' + FP.uid();      // one key per page view: double clicks and retries never create two plans
    $('#generate').addEventListener('click', (e) => FP.busy(e.currentTarget, async () => {
      $('#gen-error').innerHTML = '';
      const stepsEl = $('#gen-steps'); stepsEl.hidden = false;
      let i = 0; const tick = setInterval(() => { i = Math.min(i + 1, 2); $$('li', stepsEl).forEach((li) => li.classList.toggle('active', +li.dataset.i === i)); }, 1200);
      const r = await api('POST', '/plans', { idempotencyKey: key });
      clearInterval(tick); stepsEl.hidden = true;
      if (!r.ok) {
        const title = r.status === 503 ? 'The processing system is unavailable' : r.status === 502 ? 'The returned plan was invalid' : 'Could not create a plan';
        $('#gen-error').innerHTML = `<div style="margin-top:16px">${FP.banner('danger', title, h(r.error))}</div>`;
        return;
      }
      FP.toast(r.data.isMock ? 'Placeholder plan created (development mock).' : 'Your plan is ready.');
      FP.go('/plan/' + r.data.id);
    }));
  });

  /* ------------------------------------------------------------------ current plan */
  route('/plan', 'onboarded', async () => {
    FP.appLayout('/plan', FP.pageHead('My plan') + FP.loading());
    const r = await api('GET', '/plans/current');
    if (!r.ok) return ($('#main').innerHTML = FP.pageHead('My plan') + FP.errorCard(r.error, true));
    if (r.data) return FP.go('/plan/' + r.data.id);
    $('#main').innerHTML = FP.systemBanners() + FP.pageHead('My plan') + `<div class="card empty"><h3>No plan yet</h3><p>Request a plan built from your profile.</p><a class="btn" href="#/plan/new">Get my plan</a></div>`;
  });

  route('/plan/:id', 'onboarded', async ({ id }) => {
    FP.appLayout('/plan', FP.pageHead('My plan') + FP.loading('Loading your plan…'));
    const [r, wr, pr, list] = await Promise.all([api('GET', '/plans/' + encodeURIComponent(id)), api('GET', '/workouts?limit=200'), FP.loadProfile(), api('GET', '/plans')]);
    if (!r.ok) return ($('#main').innerHTML = FP.pageHead('My plan') + FP.errorCard(r.status === 404 ? 'This plan was not found.' : r.error, r.status !== 404));
    const p = r.data;
    const done = new Set((wr.ok ? wr.data : []).filter((w) => w.planId === p.id && w.sessionId).map((w) => w.sessionId));
    const outdated = pr.ok && FP.state.profile.version > p.profileVersion;
    const head = FP.pageHead((p.plan && p.plan.summary && p.plan.summary.title) || 'My plan', `Created ${FP.fmtDate(p.createdAt)}`,
      `<a class="btn secondary small" href="#/plan/new">New plan</a>`);
    let body = '';
    if (p.status === 'processing') {
      body = `<div class="card">${FP.banner('info', 'Your plan is still being prepared', 'The processing system accepted the request and is working on it.')}<div class="form-actions"><button class="btn" id="refresh" data-busy-label="Checking…">Check again</button></div></div>`;
    } else if (p.status !== 'ready') {
      body = `<div class="card">${FP.banner('danger', 'This plan request failed', h(p.error || 'No plan was produced.'))}<div class="form-actions"><a class="btn" href="#/plan/new">Try again</a></div></div>`;
    } else {
      const plan = p.plan;
      const weeks = plan.weeks || [];
      const cw = Math.min(FP.currentWeek(p), weeks.length ? weeks[weeks.length - 1].week : 1);
      body = `
        <div class="row" style="margin-bottom:16px">${FP.sourceBadge(p)}<span class="badge">${plural(plan.summary.weeks, 'week')}</span>${plan.summary.sessionsPerWeek ? `<span class="badge">${h(plan.summary.sessionsPerWeek)} sessions/week</span>` : ''}</div>
        ${(plan.warnings || []).length ? `<div class="stack">${plan.warnings.map((w) => FP.banner(p.isMock ? 'mock' : 'warn', w)).join('')}</div>` : ''}
        ${outdated ? `<div style="margin-top:12px">${FP.banner('info', 'Your profile has changed since this plan was made', 'Request a new plan to reflect your latest goals and availability. <a href="#/plan/new">Get an updated plan</a>')}</div>` : ''}
        ${plan.summary.overview ? `<p style="margin-top:16px">${h(plan.summary.overview)}</p>` : ''}
        <div class="grid" style="margin-top:16px">${energyCard(p.energy)}</div>
        ${(plan.guidance || []).length ? `<div class="card flat" style="margin-top:16px"><h3>Guidance</h3><ul>${plan.guidance.map((g) => `<li>${h(g)}</li>`).join('')}</ul></div>` : ''}
        <h2 style="margin-top:32px">Schedule</h2>
        <div class="tabs" role="tablist" aria-label="Weeks">${weeks.map((w) => `<button class="tab" role="tab" id="tab-${w.week}" aria-controls="week-panel" aria-selected="${w.week === cw}" data-week="${w.week}">Week ${w.week}${w.week === FP.currentWeek(p) ? ' · now' : ''}</button>`).join('')}</div>
        <div id="week-panel" role="tabpanel" style="margin-top:16px"></div>`;
      setTimeout(() => {
        const paint = (wk) => {
          const w = weeks.find((x) => x.week === wk) || weeks[0];
          $$('.tab').forEach((t) => t.setAttribute('aria-selected', String(+t.dataset.week === w.week)));
          $('#week-panel').setAttribute('aria-labelledby', 'tab-' + w.week);
          $('#week-panel').innerHTML = `${w.focus ? `<p class="muted">Focus: ${h(w.focus)}</p>` : ''}<div class="grid three">${w.sessions.map((s) => sessionCard(p.id, s, done.has(s.id))).join('')}</div>`;
        };
        $$('.tab').forEach((t) => t.addEventListener('click', () => paint(+t.dataset.week)));
        $('.tabs').addEventListener('keydown', (e) => {
          if (!['ArrowRight', 'ArrowLeft'].includes(e.key)) return;
          const tabs = $$('.tab'); const i = tabs.indexOf(document.activeElement); if (i < 0) return;
          const n = tabs[(i + (e.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length]; n.focus(); n.click();
        });
        if (weeks.length) paint(cw);
      });
    }
    const older = (list.ok ? list.data : []).filter((x) => x.id !== p.id);
    const history = older.length ? `<details class="card flat" style="margin-top:32px"><summary><strong>Previous plans (${older.length})</strong></summary><ul class="status-list" style="margin-top:8px">${older.map((x) => `<li><a href="#/plan/${h(x.id)}">${h(x.title || 'Plan')} · ${FP.fmtDate(x.createdAt)}</a><span>${x.isMock ? '<span class="badge mock">Mock</span>' : ''} <span class="badge ${x.status === 'ready' ? 'ok' : x.status === 'failed' ? 'danger' : 'info'}">${h(x.status)}</span></span></li>`).join('')}</ul></details>` : '';
    $('#main').innerHTML = FP.systemBanners() + head + body + history;
    const rf = $('#refresh');
    if (rf) rf.addEventListener('click', (e) => FP.busy(e.currentTarget, async () => { const x = await api('POST', `/plans/${encodeURIComponent(p.id)}/refresh`); if (!x.ok) FP.toast(x.error, 'error'); FP.render(); }));
  });

  /* ------------------------------------------------------------------ session detail */
  route('/session/:planId/:sid', 'onboarded', async ({ planId, sid }) => {
    FP.appLayout('/plan', FP.loading());
    const [r, wr] = await Promise.all([api('GET', '/plans/' + encodeURIComponent(planId)), api('GET', '/workouts?limit=200')]);
    if (!r.ok) return ($('#main').innerHTML = FP.errorCard(r.status === 404 ? 'Plan not found.' : r.error, r.status !== 404));
    const p = r.data;
    let s = null, wk = null;
    ((p.plan && p.plan.weeks) || []).forEach((w) => w.sessions.forEach((x) => { if (x.id === sid) { s = x; wk = w.week; } }));
    if (!s) return ($('#main').innerHTML = FP.errorCard('Session not found in this plan.'));
    const logs = (wr.ok ? wr.data : []).filter((w) => w.planId === p.id && w.sessionId === sid);
    $('#main').innerHTML = FP.systemBanners() + `
      <p class="small"><a href="#/plan/${h(p.id)}">← Back to plan</a></p>
      ${FP.pageHead(s.title, `Week ${wk} · ${h(FP.DAY_NAMES[s.day] || s.day || 'Any day')} · ${h(FP.discLabel(s.discipline))}${s.durationMin ? ' · ' + h(s.durationMin) + ' min' : ''}`,
        `<a class="btn" href="#/log?plan=${encodeURIComponent(p.id)}&session=${encodeURIComponent(s.id)}">${logs.length ? 'Log again' : 'Log this session'}</a>`)}
      <div class="row" style="margin-bottom:16px">${FP.sourceBadge(p)}${s.intensity ? `<span class="badge">Intensity: ${h(s.intensity)}</span>` : ''}</div>
      ${p.isMock ? FP.banner('mock', 'Placeholder content', 'This session comes from fixed development templates, not from a personalised analysis.') : ''}
      ${s.notes ? `<p>${h(s.notes)}</p>` : ''}
      <div style="margin-top:16px">${(s.blocks || []).map((b) => renderBlock(b, s.discipline)).join('') || '<p class="muted">No details provided for this session.</p>'}</div>
      ${logs.length ? `<div class="card flat" style="margin-top:24px"><h3>Your logs for this session</h3><ul class="status-list">${logs.map((l) => `<li><a href="#/workouts/${h(l.id)}">${FP.fmtDate(l.date)} · ${h(l.durationMin)} min</a>${l.rpe ? `<span class="muted">Effort ${h(l.rpe)}/10</span>` : ''}</li>`).join('')}</ul></div>` : ''}
      <p class="tiny muted" style="margin-top:24px">Stop if anything hurts, and adjust loads to how you feel today.</p>`;
  });
})();

/* ===== tracking ===== */
/* Dashboard, workout logging, history, progress, goals, settings. Shows only the user's real data. */
'use strict';
(function () {
  const { h, $, $$, api, route, plural } = FP;
  const F = FP.forms;

  /* ------------------------------------------------------------------ charts (single series, real data only) */
  const tip = (() => { let el; return { show(x, y, html) { if (!el) { el = document.createElement('div'); el.className = 'chart-tip'; el.setAttribute('role', 'tooltip'); document.body.appendChild(el); } el.innerHTML = html; el.style.left = Math.min(x + 12, innerWidth - 180) + 'px'; el.style.top = (y - 36) + 'px'; el.hidden = false; }, hide() { if (el) el.hidden = true; } }; })();
  function bindTips(svg) {
    $$('[data-tip]', svg).forEach((m) => {
      const show = (e) => { const r = m.getBoundingClientRect(); tip.show(e.clientX || r.left + r.width / 2, e.clientY || r.top, m.dataset.tip); };
      m.addEventListener('mousemove', show); m.addEventListener('focus', show);
      m.addEventListener('mouseleave', tip.hide); m.addEventListener('blur', tip.hide);
    });
  }
  function niceMax(v) { if (v <= 0) return 1; const p = Math.pow(10, Math.floor(Math.log10(v))); return Math.ceil(v / p) * p; }

  function barChart(rows, label, unit) {
    const W = 640, H = 220, L = 40, B = 28, T = 12, max = niceMax(Math.max(...rows.map((r) => r.v)));
    const bw = (W - L - 8) / rows.length;
    const y = (v) => T + (H - T - B) * (1 - v / max);
    const grid = [0, .5, 1].map((f) => `<line x1="${L}" x2="${W}" y1="${y(max * f)}" y2="${y(max * f)}"/><text x="${L - 6}" y="${y(max * f) + 4}" text-anchor="end">${Math.round(max * f)}</text>`).join('');
    const bars = rows.map((r, i) => {
      const x = L + i * bw + bw * .22, w = bw * .56, top = y(r.v), hgt = Math.max(0, H - B - top);
      const path = hgt > 0 ? `M${x},${H - B} V${top + Math.min(4, hgt)} q0,-4 4,-4 h${w - 8} q4,0 4,4 V${H - B} Z` : '';
      return `<g><rect class="hit" x="${L + i * bw}" y="${T}" width="${bw}" height="${H - T - B}" fill="transparent" tabindex="0" data-tip="${h(r.label)}: <b>${h(r.v)} ${h(unit)}</b>" aria-label="${h(r.label)}: ${h(r.v)} ${h(unit)}"></rect>${path ? `<path class="bar" d="${path}"></path>` : ''}<text x="${L + i * bw + bw / 2}" y="${H - 8}" text-anchor="middle">${h(r.short)}</text></g>`;
    }).join('');
    return `<figure style="margin:0"><svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="${h(label)}"><g class="grid">${grid}</g>${bars}</svg>
      <details class="table-toggle"><summary>Show as table</summary><div class="table-wrap"><table><thead><tr><th>Week starting</th><th class="num">${h(unit)}</th></tr></thead><tbody>${rows.map((r) => `<tr><td>${h(r.label)}</td><td class="num">${h(r.v)}</td></tr>`).join('')}</tbody></table></div></details></figure>`;
  }

  function lineChart(points, label, unit) {
    const W = 960, H = 220, L = 44, B = 28, T = 14;
    const vs = points.map((p) => p.v), lo = Math.min(...vs), hi = Math.max(...vs), pad = Math.max((hi - lo) * .15, .5);
    const min = lo - pad, max = hi + pad;
    const t0 = new Date(points[0].d).getTime(), t1 = new Date(points[points.length - 1].d).getTime();
    const x = (d) => points.length === 1 ? (L + W) / 2 : L + 10 + (W - L - 20) * ((new Date(d).getTime() - t0) / Math.max(1, t1 - t0));
    const y = (v) => T + (H - T - B) * (1 - (v - min) / (max - min));
    const grid = [0, .5, 1].map((f) => { const v = min + (max - min) * f; return `<line x1="${L}" x2="${W}" y1="${y(v)}" y2="${y(v)}"/><text x="${L - 6}" y="${y(v) + 4}" text-anchor="end">${v.toFixed(1)}</text>`; }).join('');
    const path = points.map((p, i) => `${i ? 'L' : 'M'}${x(p.d).toFixed(1)},${y(p.v).toFixed(1)}`).join(' ');
    const dots = points.map((p) => `<circle class="pt" cx="${x(p.d)}" cy="${y(p.v)}" r="5" tabindex="0" data-tip="${h(FP.fmtDate(p.d))}: <b>${h(p.v)} ${h(unit)}</b>" aria-label="${h(FP.fmtDate(p.d))}: ${h(p.v)} ${h(unit)}"></circle>`).join('');
    const ends = `<text x="${x(points[0].d)}" y="${H - 8}" text-anchor="start">${h(FP.fmtDate(points[0].d, { day: 'numeric', month: 'short' }))}</text>${points.length > 1 ? `<text x="${x(points[points.length - 1].d)}" y="${H - 8}" text-anchor="end">${h(FP.fmtDate(points[points.length - 1].d, { day: 'numeric', month: 'short' }))}</text>` : ''}`;
    return `<figure style="margin:0"><svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="${h(label)}"><g class="grid">${grid}</g><path class="line" d="${path}"></path>${dots}${ends}</svg></figure>`;
  }

  /* ------------------------------------------------------------------ dashboard */
  route('/dashboard', 'onboarded', async () => {
    const u = FP.state.user;
    FP.appLayout('/dashboard', FP.pageHead(`Hi, ${u.name}`) + FP.loading());
    const [pl, wo, pg] = await Promise.all([api('GET', '/plans/current'), api('GET', '/workouts?limit=5'), api('GET', '/progress')]);
    if (!pl.ok || !wo.ok || !pg.ok) return ($('#main').innerHTML = FP.pageHead(`Hi, ${u.name}`) + FP.errorCard((pl.error || wo.error || pg.error), true));
    const p = pl.data, prog = pg.data, thisWeek = prog.weekly[prog.weekly.length - 1];
    const logged = new Set();
    let planHtml;
    if (!p) {
      planHtml = `<div class="card empty"><h3>No plan yet</h3><p>Request a plan built from your profile.</p><a class="btn" href="#/plan/new">Get my plan</a></div>`;
    } else if (p.status !== 'ready') {
      planHtml = `<div class="card">${FP.banner('info', 'Your plan is being prepared')}<p style="margin-top:12px"><a href="#/plan/${h(p.id)}">Check status</a></p></div>`;
    } else {
      const allLogs = await api('GET', '/workouts?limit=200');
      (allLogs.ok ? allLogs.data : []).forEach((w) => { if (w.planId === p.id && w.sessionId) logged.add(w.sessionId); });
      const cw = FP.currentWeek(p), weeks = p.plan.weeks;
      const w = weeks.find((x) => x.week === cw);
      if (!w) {
        planHtml = `<div class="card"><h3>You've reached the end of this plan's schedule</h3><p class="muted">Request a new plan to keep going.</p><a class="btn" href="#/plan/new">Get a new plan</a></div>`;
      } else {
        const next = w.sessions.find((s) => !logged.has(s.id));
        planHtml = `<div class="row between" style="margin-bottom:12px"><h2 style="margin:0">Week ${cw} of ${p.plan.summary.weeks}</h2>${FP.sourceBadge(p)}</div>
          ${next ? `<p class="muted">Next up: <strong>${h(next.title)}</strong></p>` : `<p class="muted">All of this week's sessions are logged.</p>`}
          <div class="grid three">${w.sessions.map((s) => FP.sessionCard(p.id, s, logged.has(s.id))).join('')}</div>
          <p class="small" style="margin-top:12px"><a href="#/plan/${h(p.id)}">See the full plan</a></p>`;
      }
    }
    const ad = prog.adherence;
    $('#main').innerHTML = FP.systemBanners() + FP.pageHead(`Hi, ${u.name}`, 'Here’s where things stand.', '<a class="btn" href="#/log">Log a workout</a>') + `
      <div class="grid four" style="margin-bottom:24px">
        <div class="card tight kpi"><span class="value">${thisWeek.sessions}</span><span class="label">Workouts this week</span></div>
        <div class="card tight kpi"><span class="value">${thisWeek.minutes}</span><span class="label">Minutes this week</span></div>
        <div class="card tight kpi"><span class="value">${ad ? `${ad.sessionsCompleted}/${ad.sessionsDue}` : '—'}</span><span class="label">Plan sessions done so far</span></div>
        <div class="card tight kpi"><span class="value">${prog.totalWorkouts12w}</span><span class="label">Workouts in 12 weeks</span></div>
      </div>
      <section aria-label="This week's plan">${planHtml}</section>
      <section class="card flat" style="margin-top:24px"><div class="row between"><h2 style="margin:0;font-size:1.2rem">Recent workouts</h2><a class="small" href="#/workouts">View all</a></div>
        ${wo.data.length ? `<ul class="status-list" style="margin-top:8px">${wo.data.map((w) => `<li><a href="#/workouts/${h(w.id)}">${h(w.title)}</a><span class="muted small">${FP.fmtDate(w.date)} · ${h(w.durationMin)} min</span></li>`).join('')}</ul>`
          : `<div class="empty"><p>No workouts logged yet. Your history and progress charts fill in as you log sessions.</p></div>`}
      </section>`;
  });

  /* ------------------------------------------------------------------ log a workout */
  const DISCS = ['gym', 'running', 'cycling', 'swimming', 'hiit', 'hyrox', 'calisthenics', 'yoga', 'mobility', 'sports', 'circuit', 'bands', 'home', 'other'];
  const STRENGTH = new Set(['gym', 'calisthenics', 'bands', 'home', 'circuit', 'hyrox']);
  const DISTANCE = new Set(['running', 'cycling', 'swimming', 'hyrox']);

  route('/log', 'onboarded', async () => {
    const q = FP.query();
    FP.appLayout('/log', FP.pageHead('Log a workout') + FP.loading());
    let session = null, planId = null;
    if (q.plan && q.session) {
      const r = await api('GET', '/plans/' + encodeURIComponent(q.plan));
      if (r.ok) (r.data.plan.weeks || []).forEach((w) => w.sessions.forEach((s) => { if (s.id === q.session) { session = s; planId = r.data.id; } }));
    }
    const prof = FP.state.profile || (await FP.loadProfile()).data || {};
    const hasResting = prof.data && prof.data.restingHr;
    const presetEx = session ? (session.blocks || []).filter((b) => ['main', 'accessory', 'skill'].includes(b.type)).flatMap((b) => b.items).filter((i) => i.sets || i.reps).slice(0, 8) : [];
    const disc = session ? (DISCS.includes(session.discipline) ? session.discipline : 'other') : ((prof.data && (prof.data.disciplines || [])[0]) || 'gym');
    const clientId = 'w-' + FP.uid();
    $('#main').innerHTML = FP.pageHead('Log a workout', session ? `From your plan: ${h(session.title)}` : 'Record what you did. Only you can see it.') + `
      <form id="log" class="card" novalidate>
        <div id="form-error" aria-live="assertive"></div>
        <div class="grid two">
          <div class="field"><label for="l-date">Date</label><input id="l-date" type="date" name="date" value="${FP.today()}" max="${FP.today()}" required></div>
          <div class="field"><label for="l-disc">Training style</label><select id="l-disc" name="discipline">${DISCS.map((d) => `<option value="${d}" ${d === disc ? 'selected' : ''}>${h(FP.discLabel(d))}</option>`).join('')}</select></div>
          <div class="field"><label for="l-title">Title</label><input id="l-title" type="text" name="title" maxlength="80" value="${h(session ? session.title : '')}" placeholder="e.g. Upper body, easy run" required></div>
          <div class="field"><label for="l-dur">Duration</label><div class="input-unit"><input id="l-dur" type="number" name="durationMin" min="1" max="600" inputmode="numeric" value="${session && session.durationMin ? h(session.durationMin) : ''}" required><span class="unit">min</span></div></div>
        </div>
        <div class="field" style="margin-top:16px"><label for="l-rpe">How hard was it? <span id="rpe-out" class="muted">—</span></label>
          <input id="l-rpe" type="range" name="rpe" min="1" max="10" step="1" value="5" aria-describedby="rpe-help"><p class="help" id="rpe-help">1 = very easy, 10 = maximal effort. Leave untouched to skip.</p></div>
        <div class="grid two" style="margin-top:8px">
          <div class="field"><label for="l-hr">Average heart rate (optional)</label><div class="input-unit"><input id="l-hr" type="number" name="avgHr" min="40" max="230" inputmode="numeric"><span class="unit">bpm</span></div>
            <p class="help">${hasResting ? 'With this, FitMetrics analyses calories, zone and training load.' : 'Add your resting heart rate in your profile to get FitMetrics analysis.'}</p></div>
          <div class="field" id="dist-field"><label for="l-dist">Distance (optional)</label><div class="input-unit"><input id="l-dist" type="number" name="distanceKm" min="0" max="1000" step="0.01" inputmode="decimal"><span class="unit">km</span></div></div>
        </div>
        <fieldset id="ex-section" style="margin-top:20px"><legend>Exercises (optional)</legend><div id="ex-rows"></div>
          <button type="button" class="btn secondary small" id="add-ex" style="margin-top:10px">Add exercise</button></fieldset>
        <div class="field" style="margin-top:16px"><label for="l-notes">Notes (optional)</label><textarea id="l-notes" name="notes" maxlength="1000"></textarea></div>
        <div class="form-actions"><button type="submit" class="btn" data-busy-label="Saving…">Save workout</button><a class="btn ghost" href="${session ? `#/session/${h(planId)}/${h(session.id)}` : '#/dashboard'}">Cancel</a></div>
      </form>`;
    const f = $('#log');
    let dirty = false, rpeTouched = false;
    FP.setLeaveGuard(() => dirty);
    f.addEventListener('input', () => { dirty = true; });
    $('#l-rpe').addEventListener('input', (e) => { rpeTouched = true; $('#rpe-out').textContent = e.target.value + '/10'; });
    const exRow = (ex) => `<div class="exercise-row"><div class="field name"><label class="sr-only">Exercise</label><input type="text" data-k="name" maxlength="80" placeholder="Exercise" value="${h(ex.name || '')}" aria-label="Exercise name"></div>
      <div class="field"><input type="number" data-k="sets" min="0" max="50" placeholder="Sets" value="${h(ex.sets || '')}" aria-label="Sets"></div>
      <div class="field"><input type="text" data-k="reps" maxlength="20" placeholder="Reps" value="${h(ex.reps || '')}" aria-label="Reps"></div>
      <div class="field"><input type="number" data-k="loadKg" min="0" max="1000" step="0.5" placeholder="kg" aria-label="Load in kg"></div>
      <button type="button" class="btn ghost small" data-remove aria-label="Remove exercise">Remove</button></div>`;
    const rows = $('#ex-rows');
    rows.innerHTML = presetEx.map(exRow).join('');
    $('#add-ex').addEventListener('click', () => { rows.insertAdjacentHTML('beforeend', exRow({})); rows.lastElementChild.querySelector('input').focus(); });
    rows.addEventListener('click', (e) => { if (e.target.matches('[data-remove]')) { e.target.closest('.exercise-row').remove(); dirty = true; } });
    const sync = () => { const d = $('#l-disc').value; $('#ex-section').hidden = !STRENGTH.has(d) && !rows.children.length; $('#dist-field').hidden = !DISTANCE.has(d); };
    $('#l-disc').addEventListener('change', sync); sync();
    f.addEventListener('submit', (e) => {
      e.preventDefault();
      FP.busy(f.querySelector('button[type=submit]'), async () => {
        $('#form-error').innerHTML = '';
        const num = (v) => (v === '' || v == null ? null : Number(v));
        const exercises = $$('.exercise-row', rows).map((r) => { const o = {}; $$('input', r).forEach((i) => { const v = i.value.trim(); if (v) o[i.dataset.k] = i.type === 'number' ? Number(v) : v; }); return o; }).filter((o) => o.name);
        const body = { clientId, date: f.date.value, discipline: f.discipline.value, title: f.title.value.trim(), durationMin: num(f.durationMin.value),
          rpe: rpeTouched ? Number(f.rpe.value) : null, avgHr: num(f.avgHr.value), distanceKm: DISTANCE.has(f.discipline.value) ? num(f.distanceKm.value) : null,
          notes: f.notes.value.trim() || null, exercises, planId, sessionId: session ? session.id : null };
        const local = {};
        if (!body.title) local.title = 'Add a short title.';
        if (!body.durationMin || body.durationMin <= 0) local.durationMin = 'Enter how many minutes you trained.';
        if (!body.date || body.date > FP.today()) local.date = 'Choose today or an earlier date.';
        if (Object.keys(local).length) return FP.showFieldErrors(f, local);
        const r = await api('POST', '/workouts', body);
        if (!r.ok) { if (r.fields) FP.showFieldErrors(f, r.fields); $('#form-error').innerHTML = FP.banner('danger', r.status === 0 ? r.error : 'Workout not saved', r.status === 0 ? 'Your entries are still here — try again when you are back online.' : h(r.error)); return; }
        dirty = false; FP.setLeaveGuard(null);
        FP.toast(r.data.duplicate ? 'Already saved.' : 'Workout saved.');
        FP.go('/workouts/' + r.data.id);
      });
    });
  });

  /* ------------------------------------------------------------------ history & detail */
  const ANALYSIS_TEXT = {
    analysed: null,
    skipped_no_heart_rate: 'Not analysed: no average heart rate was entered.',
    skipped_no_resting_hr: 'Not analysed: add your resting heart rate in your profile, then re-run the analysis.',
    skipped_sex_not_shared: "Not analysed: FitMetrics' training-load equation needs the sex value used for energy equations.",
    skipped_profile_incomplete: 'Not analysed: your profile is missing age or weight.',
    analysis_rejected: 'FitMetrics could not analyse these values.',
  };

  route('/workouts', 'onboarded', async () => {
    FP.appLayout('/workouts', FP.pageHead('Workout history') + FP.loading());
    const r = await api('GET', '/workouts?limit=200');
    if (!r.ok) return ($('#main').innerHTML = FP.pageHead('Workout history') + FP.errorCard(r.error, true));
    $('#main').innerHTML = FP.systemBanners() + FP.pageHead('Workout history', plural(r.data.length, 'workout') + ' logged', '<a class="btn" href="#/log">Log a workout</a>') +
      (r.data.length ? `<div class="card flat" style="padding:0"><div class="table-wrap"><table><thead><tr><th>Date</th><th>Workout</th><th>Style</th><th class="num">Minutes</th><th class="num">Effort</th><th>Analysis</th></tr></thead><tbody>
        ${r.data.map((w) => `<tr><td class="nowrap">${FP.fmtDate(w.date)}</td><td><a href="#/workouts/${h(w.id)}">${h(w.title)}</a>${w.sessionId ? ' <span class="badge">Plan</span>' : ''}</td><td>${h(FP.discLabel(w.discipline))}</td><td class="num">${h(w.durationMin)}</td><td class="num">${w.rpe ? h(w.rpe) + '/10' : '—'}</td><td>${w.analysisStatus === 'analysed' ? `<span class="badge ok">${h(w.analysis.trainingLoad)} load</span>` : '<span class="muted small">—</span>'}</td></tr>`).join('')}
        </tbody></table></div></div>` : `<div class="card empty"><h3>Nothing logged yet</h3><p>Every workout you log appears here.</p><a class="btn" href="#/log">Log your first workout</a></div>`);
  });

  route('/workouts/:id', 'onboarded', async ({ id }) => {
    FP.appLayout('/workouts', FP.loading());
    const r = await api('GET', '/workouts/' + encodeURIComponent(id));
    if (!r.ok) return ($('#main').innerHTML = FP.errorCard(r.status === 404 ? 'Workout not found.' : r.error, r.status !== 404));
    const w = r.data, a = w.analysis;
    const ex = (w.details.exercises || []);
    $('#main').innerHTML = `<p class="small"><a href="#/workouts">← History</a></p>` + FP.pageHead(w.title, `${FP.fmtDate(w.date)} · ${h(FP.discLabel(w.discipline))}`, `<button class="btn secondary small" id="del">Delete</button>`) + `
      <div class="grid four">
        <div class="card tight kpi"><span class="value">${h(w.durationMin)}</span><span class="label">Minutes</span></div>
        <div class="card tight kpi"><span class="value">${w.rpe ? h(w.rpe) + '/10' : '—'}</span><span class="label">Effort</span></div>
        <div class="card tight kpi"><span class="value">${w.avgHr ? h(w.avgHr) : '—'}</span><span class="label">Avg heart rate</span></div>
        <div class="card tight kpi"><span class="value">${w.details.distanceKm ? h(w.details.distanceKm) + ' km' : '—'}</span><span class="label">Distance</span></div>
      </div>
      <div class="card flat" style="margin-top:16px"><h3>Workout analysis</h3>
        ${w.analysisStatus === 'analysed' ? `<div class="grid four" style="margin-top:12px">
            <div class="kpi"><span class="value">${h(a.caloriesBurned)}</span><span class="label">kcal (estimate)</span></div>
            <div class="kpi"><span class="value" style="font-size:1.2rem">${h(a.zone || '')}</span><span class="label">Heart-rate zone</span></div>
            <div class="kpi"><span class="value">${h(a.trainingLoad)}</span><span class="label">Training load (TRIMP)</span></div>
            <div class="kpi"><span class="value">${h(a.recoveryHours)} h</span><span class="label">Suggested recovery</span></div></div>
            <p class="tiny muted" style="margin:12px 0 0">Analysed by ${h(a.analysedBy)}.</p>`
          : `<p class="muted">${h(ANALYSIS_TEXT[w.analysisStatus] || 'Not analysed.')}${a && a.error ? ' (' + h(a.error) + ')' : ''}</p>${w.avgHr ? '<button class="btn secondary small" id="reanalyse" data-busy-label="Analysing…">Run analysis again</button>' : ''}`}
      </div>
      ${ex.length ? `<div class="card flat" style="margin-top:16px;padding:0"><div class="table-wrap"><table><thead><tr><th>Exercise</th><th class="num">Sets</th><th class="num">Reps</th><th class="num">Load</th></tr></thead><tbody>${ex.map((e) => `<tr><td>${h(e.name)}</td><td class="num">${h(e.sets || '—')}</td><td class="num">${h(e.reps || '—')}</td><td class="num">${e.loadKg != null ? h(e.loadKg) + ' kg' : '—'}</td></tr>`).join('')}</tbody></table></div></div>` : ''}
      ${w.notes ? `<div class="card flat" style="margin-top:16px"><h3>Notes</h3><p>${h(w.notes)}</p></div>` : ''}
      ${w.planId ? `<p class="small" style="margin-top:16px"><a href="#/session/${h(w.planId)}/${h(w.sessionId)}">View the planned session</a></p>` : ''}`;
    const re = $('#reanalyse');
    if (re) re.addEventListener('click', (e) => FP.busy(e.currentTarget, async () => { const x = await api('POST', `/workouts/${encodeURIComponent(w.id)}/analyse`); if (!x.ok) FP.toast(x.error, 'error'); FP.render(); }));
    $('#del').addEventListener('click', (e) => {
      const btn = e.currentTarget;
      if (btn.dataset.confirm !== '1') { btn.dataset.confirm = '1'; btn.textContent = 'Tap again to delete'; btn.classList.add('danger'); return; }
      FP.busy(btn, async () => { const x = await api('DELETE', '/workouts/' + encodeURIComponent(w.id)); if (!x.ok) return FP.toast(x.error, 'error'); FP.toast('Workout deleted.'); FP.go('/workouts'); });
    });
  });

  /* ------------------------------------------------------------------ progress */
  route('/progress', 'onboarded', async () => {
    FP.appLayout('/progress', FP.pageHead('Progress') + FP.loading());
    const r = await api('GET', '/progress');
    if (!r.ok) return ($('#main').innerHTML = FP.pageHead('Progress') + FP.errorCard(r.error, true));
    const p = r.data, units = (FP.state.profile && FP.state.profile.data.units) || 'metric';
    const weekly = p.weekly.map((w) => ({ label: FP.fmtDate(w.weekStart), short: FP.fmtDate(w.weekStart, { day: 'numeric', month: 'short' }), v: w.minutes }));
    const anyMinutes = weekly.some((w) => w.v > 0);
    const weights = p.measurements.filter((m) => m.weight != null).map((m) => ({ d: m.date, v: units === 'imperial' ? Math.round(m.weight * 22.0462) / 10 : m.weight }));
    const wu = units === 'imperial' ? 'lb' : 'kg';
    const tb = p.trainingBalance, ad = p.adherence;
    const tbHtml = tb.status === 'ok'
      ? `<div class="row"><span class="badge ${tb.injuryRisk === 'Low' ? 'ok' : tb.injuryRisk === 'Moderate' ? 'warn' : 'danger'}">${h(tb.zone)}</span><span class="muted small">Acute:chronic ratio ${h(tb.acwr)}</span></div>${tb.advice ? `<p class="small" style="margin-top:8px">${h(tb.advice)}</p>` : ''}<p class="tiny muted">Calculated by ${h(tb.source)} from your analysed workouts in the last 28 days.</p>`
      : `<p class="muted small">${h(tb.reason || 'Not available yet.')}</p>`;
    $('#main').innerHTML = FP.systemBanners() + FP.pageHead('Progress', 'Built only from what you have logged.') + `
      <div class="grid two">
        <div class="card flat"><h3>Training minutes per week</h3>${anyMinutes ? barChart(weekly, 'Training minutes per week, last 8 weeks', 'min') : '<div class="empty"><p>Log workouts to see your weekly training time.</p></div>'}</div>
        <div class="card flat"><h3>Plan adherence</h3>${ad ? `<div class="kpi" style="margin-top:8px"><span class="value">${ad.sessionsCompleted} of ${ad.sessionsDue}</span><span class="label">sessions due so far (week ${ad.currentWeek}) logged against your plan</span></div><p class="small muted" style="margin-top:12px">${ad.sessionsCompletedTotal} of ${ad.sessionsPlannedTotal} planned sessions logged in total.</p>` : '<p class="muted small">Adherence appears once you have a plan and log its sessions.</p>'}
          <hr class="hr"><h3>Training balance</h3>${tbHtml}</div>
      </div>
      <div class="card flat" style="margin-top:16px"><div class="row between"><h3 style="margin:0">Body measurements</h3></div>
        ${weights.length ? lineChart(weights, `Body weight over time in ${wu}`, wu) : '<p class="muted small" style="margin-top:8px">No measurements yet. Add one below — the chart only shows what you enter.</p>'}
        <form id="meas" class="grid four" style="margin-top:16px;align-items:end" novalidate>
          <div class="field"><label for="m-date">Date</label><input id="m-date" type="date" name="date" value="${FP.today()}" max="${FP.today()}"></div>
          <div class="field"><label for="m-w">Weight (${wu})</label><input id="m-w" type="number" name="weight" step="0.1" inputmode="decimal"></div>
          <div class="field"><label for="m-waist">Waist (cm)</label><input id="m-waist" type="number" name="waist" step="0.5" inputmode="decimal"></div>
          <div class="field"><label for="m-bf">Body fat (%)</label><input id="m-bf" type="number" name="bodyFat" step="0.1" inputmode="decimal"></div>
          <div><button class="btn" type="submit" data-busy-label="Saving…">Add measurement</button></div>
        </form>
        ${p.measurements.length ? `<details class="table-toggle"><summary>All measurements (${p.measurements.length})</summary><div class="table-wrap"><table><thead><tr><th>Date</th><th class="num">Weight</th><th class="num">Waist</th><th class="num">Body fat</th></tr></thead><tbody>${p.measurements.slice().reverse().map((m) => `<tr><td>${FP.fmtDate(m.date)}</td><td class="num">${m.weight != null ? h(units === 'imperial' ? (m.weight * 2.20462).toFixed(1) : m.weight) + ' ' + wu : '—'}</td><td class="num">${m.waist != null ? h(m.waist) + ' cm' : '—'}</td><td class="num">${m.bodyFat != null ? h(m.bodyFat) + '%' : '—'}</td></tr>`).join('')}</tbody></table></div></details>` : ''}
      </div>`;
    $$('svg.chart').forEach(bindTips);
    const f = $('#meas');
    f.addEventListener('submit', (e) => {
      e.preventDefault();
      FP.busy(f.querySelector('button'), async () => {
        const n = (v) => (v === '' ? null : Number(v));
        let weight = n(f.weight.value); if (weight != null && units === 'imperial') weight = Math.round(weight / 2.20462 * 10) / 10;
        const x = await api('POST', '/measurements', { date: f.date.value, weight, waist: n(f.waist.value), bodyFat: n(f.bodyFat.value) });
        if (!x.ok) return x.fields ? FP.showFieldErrors(f, x.fields) : FP.toast(x.error, 'error');
        FP.toast('Measurement added.'); FP.render();
      });
    });
  });

  /* ------------------------------------------------------------------ goals */
  route('/goals', 'onboarded', async () => {
    FP.appLayout('/goals', FP.pageHead('Goals') + FP.loading());
    const [pr, pl] = await Promise.all([FP.loadProfile(), api('GET', '/plans/current')]);
    if (!pr.ok) return ($('#main').innerHTML = FP.pageHead('Goals') + FP.errorCard(pr.error, true));
    const cfg = FP.state.config, steps = cfg.steps.filter((s) => ['goals', 'timeline'].includes(s.id));
    const fields = steps.flatMap((s) => s.fields);
    let data = JSON.parse(JSON.stringify(FP.state.profile.data)), dirty = false;
    const plan = pl.ok ? pl.data : null;
    $('#main').innerHTML = FP.systemBanners() + FP.pageHead('Goals', 'Change what you are training for. Your plan won’t change until you request a new one.') + `
      ${plan && plan.energy ? `<div style="margin-bottom:16px">${FP.energyCard(plan.energy)}</div>` : ''}
      <form id="goals" class="card" novalidate><div id="form-error" aria-live="assertive"></div><div id="goal-fields"></div>
        <div class="form-actions"><button class="btn" type="submit" data-busy-label="Saving…">Save goals</button></div></form>`;
    const holder = $('#goal-fields');
    const paint = () => { holder.innerHTML = F.renderFields(fields, data, { units: data.units || 'metric' }); };
    paint();
    const deps = F.dependencies(fields);
    holder.addEventListener('change', (e) => { dirty = true; if (deps.has(e.target.name)) { Object.assign(data, F.read(holder, fields, { units: data.units })); paint(); } });
    holder.addEventListener('input', () => { dirty = true; });
    FP.setLeaveGuard(() => dirty);
    $('#goals').addEventListener('submit', (e) => {
      e.preventDefault();
      FP.busy(e.target.querySelector('button'), async () => {
        Object.assign(data, F.read(holder, fields, { units: data.units }));
        const local = F.requiredErrors(fields, data);
        if (Object.keys(local).length) return FP.showFieldErrors(e.target, local);
        const r = await api('PUT', '/profile', { data, version: FP.state.profile.version });
        if (r.status === 409) { $('#form-error').innerHTML = FP.banner('warn', 'Your profile changed elsewhere.', 'Reload this page to see the latest version before saving.'); return; }
        if (!r.ok) { if (r.fields) FP.showFieldErrors(e.target, r.fields); $('#form-error').innerHTML = FP.banner('danger', r.error); return; }
        FP.state.profile = r.data; data = JSON.parse(JSON.stringify(r.data.data)); dirty = false;
        $('#form-error').innerHTML = FP.banner('ok', 'Goals saved.', plan ? 'Your current plan was built for your previous goals. <a href="#/plan/new">Request an updated plan</a> when you are ready.' : '<a href="#/plan/new">Request a plan</a> for these goals.');
      });
    });
  });

  /* ------------------------------------------------------------------ settings */
  route('/settings', 'onboarded', async () => {
    FP.appLayout('/settings', FP.pageHead('Settings') + FP.loading());
    await FP.loadIntegrations();
    const s = FP.state.integrations, u = FP.state.user;
    const statusBadge = (st) => st === 'up' ? '<span class="badge ok">Connected</span>' : st === 'not_configured' ? '<span class="badge warn">Not configured</span>' : '<span class="badge danger">Unavailable</span>';
    const mode = s ? s.planService.mode : null;
    const theme = FP.applyTheme();
    $('#main').innerHTML = FP.pageHead('Settings') + `
      <div class="grid two">
        <form id="acct" class="card" novalidate><h2 style="font-size:1.15rem">Account</h2>
          <div class="field"><label for="s-name">Name</label><input id="s-name" name="name" type="text" maxlength="80" value="${h(u.name)}"></div>
          <div class="field"><label>E-mail</label><p style="margin:0">${h(u.email)}</p></div>
          <div class="form-actions"><button class="btn secondary" type="submit" data-busy-label="Saving…">Save name</button></div></form>
        <form id="pw" class="card" novalidate><h2 style="font-size:1.15rem">Change password</h2>
          <div class="field"><label for="s-cur">Current password</label><input id="s-cur" name="currentPassword" type="password" autocomplete="current-password"></div>
          <div class="field"><label for="s-new">New password</label><input id="s-new" name="newPassword" type="password" autocomplete="new-password" aria-describedby="s-new-help"><p class="help" id="s-new-help">At least 10 characters, with a letter and a number. Other devices will be signed out.</p></div>
          <div class="form-actions"><button class="btn secondary" type="submit" data-busy-label="Saving…">Update password</button></div></form>
        <div class="card"><h2 style="font-size:1.15rem">Training profile</h2><p class="muted small">Edit your answers from onboarding: basics, experience, training styles, availability, equipment and health notes.</p>
          <div class="row"><a class="btn secondary" href="#/onboarding/basics">Edit profile</a><a class="btn ghost" href="#/onboarding/review">Review all answers</a></div></div>
        <div class="card"><h2 style="font-size:1.15rem">Appearance</h2><fieldset><legend class="sr-only">Theme</legend><div class="options">
          ${['system', 'light', 'dark'].map((t) => `<label class="option"><input type="radio" name="theme" value="${t}" ${theme === t ? 'checked' : ''}><span>${t[0].toUpperCase() + t.slice(1)}</span></label>`).join('')}</div></fieldset>
          <p class="help" style="margin-top:8px">Saved on this device only.</p></div>
        <div class="card"><h2 style="font-size:1.15rem">Connected services</h2>
          ${s ? `<ul class="status-list">
            <li><span>Plan generation (Maajith's processing system)</span>${mode === 'live' ? '<span class="badge ok">Connected</span>' : mode === 'mock' ? '<span class="badge mock">Development mock</span>' : '<span class="badge warn">Not configured</span>'}</li>
            <li><span>${h(s.fitpulse.label)}</span>${statusBadge(s.fitpulse.status)}</li>
            <li><span>${h(s.fitmetrics.label)}</span>${statusBadge(s.fitmetrics.status)}</li>
            <li><span>Database</span>${s.database.durable ? '<span class="badge ok">Permanent</span>' : '<span class="badge warn">Temporary</span>'}</li>
            <li><span>Password-reset e-mail</span>${s.emailDelivery ? '<span class="badge ok">Configured</span>' : '<span class="badge warn">Not configured</span>'}</li></ul>` : '<p class="muted">Status unavailable.</p>'}
          <p class="tiny muted" style="margin-top:8px">Developer tools: <a href="/tools.html">FitMetrics API console</a> · <a href="/docs">API reference</a></p></div>
        <div class="card"><h2 style="font-size:1.15rem">Your data</h2><p class="muted small">Download everything FitPulse stores about you, or delete your account permanently.</p>
          <div class="row"><button class="btn secondary" id="export" data-busy-label="Preparing…">Download my data</button></div>
          <hr class="hr"><form id="del" novalidate><div class="field"><label for="s-delpw">Delete account — confirm with your password</label><input id="s-delpw" name="password" type="password" autocomplete="current-password"></div>
          <div class="form-actions"><button class="btn danger" type="submit" data-busy-label="Deleting…">Delete my account</button></div></form></div>
      </div>
      <div class="form-actions"><button class="btn ghost" data-action="logout">Sign out</button></div>`;
    $('#acct').addEventListener('submit', (e) => { e.preventDefault(); FP.busy(e.target.querySelector('button'), async () => {
      const r = await api('PUT', '/account', { name: e.target.name.value.trim() });
      if (!r.ok) return FP.toast(r.status === 422 ? 'Enter a name (up to 80 characters).' : r.error, 'error');
      FP.state.user.name = r.data.name; FP.toast('Name saved.'); FP.render(); }); });
    $('#pw').addEventListener('submit', (e) => { e.preventDefault(); const f = e.target; FP.busy(f.querySelector('button'), async () => {
      const r = await api('POST', '/account/password', { currentPassword: f.currentPassword.value, newPassword: f.newPassword.value });
      if (!r.ok) return FP.showFieldErrors(f, { [/current/i.test(r.error) ? 'currentPassword' : 'newPassword']: r.status === 422 ? 'Fill in both fields.' : r.error });
      f.reset(); FP.showFieldErrors(f, {}); FP.toast('Password updated.'); }); });
    $$('input[name=theme]').forEach((i) => i.addEventListener('change', () => { try { localStorage.setItem('fp_theme', i.value); } catch (err) { /* blocked */ } FP.applyTheme(); }));
    $('#export').addEventListener('click', (e) => FP.busy(e.currentTarget, async () => {
      const r = await api('GET', '/account/export');
      if (!r.ok) return FP.toast(r.error, 'error');
      const url = URL.createObjectURL(new Blob([JSON.stringify(r.data, null, 2)], { type: 'application/json' }));
      const a = document.createElement('a'); a.href = url; a.download = `fitpulse-data-${FP.today()}.json`; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    }));
    $('#del').addEventListener('submit', (e) => { e.preventDefault(); const f = e.target; FP.busy(f.querySelector('button'), async () => {
      if (!f.password.value) return FP.showFieldErrors(f, { password: 'Enter your password to confirm.' });
      const r = await api('DELETE', '/account', { password: f.password.value });
      if (!r.ok) return FP.showFieldErrors(f, { password: r.error });
      FP.state.user = null; FP.toast('Your account and data were deleted.'); FP.go('/'); }); });
  });
})();
