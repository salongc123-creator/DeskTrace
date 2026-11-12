'use strict';
/* DeskTrace (桌迹) — front end. Talks to server.py over JSON + Server-Sent Events.
   All user-facing text goes through t() from i18n.js. */

const TOKEN = document.querySelector('meta[name=token]').content;
const VERSION = document.querySelector('meta[name=version]')?.content || '0';
const atLeast = v => {
  const a = VERSION.split('.').map(Number), b = v.split('.').map(Number);
  for (let i = 0; i < Math.max(a.length, b.length); i++) if ((a[i] || 0) !== (b[i] || 0)) return (a[i] || 0) > (b[i] || 0);
  return true;
};
// Functions that arrive with the 1.6.1 version license: notes on versions, timed pause,
// do-not-disturb, the Explorer menu switch, ignored folders and diagnostics.
const F161 = atLeast('1.6.1');
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const ICON = {
  plus: '<path d="M12 5v14M5 12h14"/>',
  edit: '<path d="M4 20h4L19 9l-4-4L4 16v4z"/><path d="m13.5 6.5 4 4"/>',
  trash: '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>',
  move: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  folder: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  open: '<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
  copy: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/>',
  check: '<path d="m5 12 5 5L20 7"/>',
  restore: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>',
  download: '<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>',
  pause: '<rect x="6" y="5" width="4" height="14" rx="1"/><rect x="14" y="5" width="4" height="14" rx="1"/>',
  play: '<path d="M7 5v14l11-7z"/>',
  gear: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon: '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>',
  x: '<path d="M6 6l12 12M18 6 6 18"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
  warn: '<path d="M12 3 2 20h20L12 3z"/><path d="M12 10v4M12 17h.01"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
  globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
  power: '<path d="M12 3v8"/><path d="M6.3 6.3a8 8 0 1 0 11.4 0"/>',
  chev: '<path d="m6 9 6 6 6-6"/>',
  star: '<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L12 17.3l-5.6 2.9 1.1-6.2L3 9.6l6.2-.9z"/>',
  compare: '<path d="M8 3v13M5 6l3-3 3 3M16 21V8M13 18l3 3 3-3"/>',
  chart: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
  code: '<path d="m8 8-4 4 4 4M16 8l4 4-4 4M14 5l-4 14"/>',
  image: '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="m21 16-5-5-9 9"/>',
  shield: '<path d="M12 3 4 6v6c0 4.5 3.4 8 8 9 4.6-1 8-4.5 8-9V6z"/><path d="m9 12 2 2 4-4"/>',
  note: '<path d="M5 4h10l4 4v12H5z"/><path d="M15 4v4h4M8 12h8M8 16h5"/>',
  eyeoff: '<path d="M3 3l18 18"/><path d="M10.6 6.1A9.7 9.7 0 0 1 12 6c6 0 9.5 6 9.5 6a17 17 0 0 1-2.6 3.3M6.6 6.6A17 17 0 0 0 2.5 12S6 18 12 18a9 9 0 0 0 4.4-1.1"/><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
};
const svg = (name, cls = '') => `<svg viewBox="0 0 24 24" class="${cls}">${ICON[name]}</svg>`;

const KIND_ICON = { created: 'plus', modified: 'edit', deleted: 'trash', renamed: 'move' };
const CAT_TAG = { word: 'DOC', excel: 'XLS', ppt: 'PPT', pdf: 'PDF', markdown: 'MD', text: 'TXT', code: '</>', image: 'IMG', archive: 'ZIP', media: 'AV', other: 'FILE' };
const UNIT = { docx: 'paragraph', xlsx: 'cell' };
const WEB_IMG = /\.(png|jpe?g|gif|bmp|webp)$/i;

const S = {
  mode: 'changes', events: [], byId: new Map(), sel: null, kinds: new Set(), cats: new Set(), q: '', more: false,
  files: [], fileTotal: 0, fileSel: null, sort: 'recent', openGroups: new Set(), selGroup: null,
  smode: 'name', filesReq: 0, indexed: 0, range: 'all', starOnly: false, loadingMore: false,
  diffView: null,
  fresh: new Set(), status: null, stats: null, connected: false, wasDown: false, tab: null, req: 0, unseen: 0,
};

/* ------------------------------------------------------------------ helpers */
const qs = params => Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')
  .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`).join('&');
async function get(path, params = {}) {
  const r = await fetch(path + (Object.keys(params).length ? '?' + qs(params) : ''));
  return r.json();
}
async function post(path, body = {}) {
  if (/^\/api\/(clean\/|chat-media-clean)/.test(path)) S.cleanActs = (S.cleanActs || 0) + 1;  // something changed on a drive (2.7.0 O4)
  const r = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Token': TOKEN }, body: JSON.stringify(body) });
  return r.json();
}
const blobUrl = (hash, name) => `/api/blob?${qs({ hash, name })}`;
const fileUrl = path => `/api/file?${qs({ path })}`;
const basename = p => p.split(/[\\/]/).pop();
const dirname = p => p.slice(0, Math.max(p.lastIndexOf('\\'), p.lastIndexOf('/')));
const loc = () => LANGS[LANG].locale;
const num = n => Number(n || 0).toLocaleString(loc());
const errText = r => (r.code ? t('err.' + r.code, { size: fmtSize(r.size) }) : (r.error || t('err.generic')))
  + (r.by && r.by.length ? ' ' + t('err.lockedBy', { apps: r.by.join(', ') }) : '');  // who has it open (2.6.0 #19)

function fmtSize(n) {
  if (n == null) return '—';
  const u = ['B', 'KB', 'MB', 'GB', 'TB']; let i = 0; n = +n;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return i ? `${n.toLocaleString(loc(), { maximumFractionDigits: n < 10 ? 1 : 0 })} ${u[i]}` : `${n} B`;
}
const fmtTime = ts => new Date(ts * 1000).toLocaleTimeString(loc(), { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
const fmtFull = ts => new Date(ts * 1000).toLocaleString(loc(), { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
function rel(ts) {
  const s = Date.now() / 1000 - ts;
  if (s < 10) return t('time.justNow');
  if (s < 60) return t('time.s', { n: s | 0 });
  if (s < 3600) return t('time.m', { n: (s / 60) | 0 });
  if (s < 86400) return t('time.h', { n: (s / 3600) | 0 });
  return t('time.d', { n: (s / 86400) | 0 });
}
function dayLabel(ts) {
  const d = new Date(ts * 1000), now = new Date();
  const diff = Math.round((new Date(now.getFullYear(), now.getMonth(), now.getDate()) - new Date(d.getFullYear(), d.getMonth(), d.getDate())) / 864e5);
  if (diff === 0) return t('day.today');
  if (diff === 1) return t('day.yesterday');
  return d.toLocaleDateString(loc(), { weekday: 'long', month: 'short', day: 'numeric', year: d.getFullYear() !== now.getFullYear() ? 'numeric' : undefined });
}
function colName(n) { let s = ''; while (n > 0) { const r = (n - 1) % 26; s = String.fromCharCode(65 + r) + s; n = (n - 1 - r) / 26; } return s; }

function ficon(cat, ext, big = false) {
  const tag = (ext || '').slice(1, 5).toUpperCase() || CAT_TAG[cat] || 'FILE';
  return `<div class="ficon c-${cat || 'other'}${big ? ' big' : ''}">${esc(tag)}</div>`;
}
const kbadge = kind => `<span class="kbadge k-${kind}">${svg(KIND_ICON[kind])}${t('kind.' + kind)}</span>`;
function crumb(e) {
  return [e.root_name, ...(e.rel_dir || '').split(/[\\/]/)].filter(Boolean).join(' › ') || e.dir;
}
function relTo(root, p) {
  if (root && p.toLowerCase().startsWith(root.toLowerCase())) {
    const r = p.slice(root.length).replace(/^[\\/]/, '');
    return [basename(root), ...r.split(/[\\/]/)].filter(Boolean).join(' › ');
  }
  return p;
}
const loadingHTML = () => `<div class="loading"><span class="spin"></span></div>`;
const noteHTML = (html, warn = false) => `<div class="note${warn ? ' warn' : ''}">${svg(warn ? 'warn' : 'info')}<div>${html}</div></div>`;

/* ------------------------------------------------------------------ theme & language */
function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch { /* storage unavailable */ } return null; }
function getTheme() { return store('dw-theme') || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'); }
function setTheme(th) {
  document.documentElement.dataset.theme = th;
  $('#themeBtn').innerHTML = svg(th === 'dark' ? 'sun' : 'moon');
  store('dw-theme', th);
  hostMessage({ theme: th });  // the app window colours its title bar to match
}
// Messages to the native app window (window.py); harmless anywhere else.
function hostMessage(msg) { try { window.chrome?.webview?.postMessage(msg); } catch { /* not in the app window */ } }

function applyStatic() {
  document.documentElement.lang = LANGS[LANG].html;
  $$('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
  document.title = t('app.name');
  $$('[data-i18n-ph]').forEach(el => { el.placeholder = t(el.dataset.i18nPh); });
  $$('[data-i18n-title]').forEach(el => { el.title = t(el.dataset.i18nTitle); el.setAttribute('aria-label', el.title); });
  $('#starBtn').innerHTML = svg('star');
  $('#exportBtn').innerHTML = `${svg('download')}${t('export.btn')}`;
  $('#langBtn').innerHTML = `${svg('globe')}<span class="code">${LANGS[LANG].short}</span>`;
  $('#langMenu').innerHTML = Object.entries(LANGS).map(([code, l]) =>
    `<button role="menuitemradio" aria-checked="${code === LANG}" class="${code === LANG ? 'on' : ''}" data-lang="${code}"><span class="code">${l.short}</span>${l.name}${code === LANG ? svg('check') : ''}</button>`).join('');
}

function setLang(code, persist = true) {
  if (!LANGS[code]) return;
  LANG = code;
  store('dw-lang', code);
  if (persist) post('/api/settings', { lang: code });
  applyStatic();
  renderStatus(); renderKpis(); renderChart(); renderCats(); renderScope(); renderFilters(); renderList();
  const cur = currentItem();
  if (S.selGroup) renderGroupDetail(findGroup(S.selGroup));
  else if (cur) renderDetail(cur); else renderWelcome();
}

/* ------------------------------------------------------------------ summaries */
function parseSum(e) {
  if (e.summary == null) return null;
  try { const s = JSON.parse(e.summary); if (s && typeof s === 'object') return s; } catch { /* legacy text */ }
  return { raw: e.summary };
}
function summaryText(e) {
  const s = parseSum(e);
  if (!s) return e.kind === 'renamed' ? t('sum.renamed') : null;
  if (s.raw) return s.raw;
  switch (s.t) {
    case 'new': return s.n ? t('sum.newN', { n: num(s.n), unit: unitWord(s.u, s.n) }) : t('sum.new');
    case 'del': return s.n ? t('sum.delN', { n: num(s.n), unit: unitWord(s.u, s.n) }) : t('sum.del');
    case 'big': return t('sum.big', { size: fmtSize(s.size) });
    case 'size': return t('sum.size', { d: (s.d >= 0 ? '+' : '−') + fmtSize(Math.abs(s.d)) });
    case 'diff': return `+${e.added} −${e.removed} ${unitWord(s.u, (e.added || 0) + (e.removed || 0))}`;
    default: return t('sum.' + s.t);
  }
}
function summaryHTML(e) {
  const s = parseSum(e);
  if (!s && e.kind !== 'renamed') return `<span class="spin"></span><span class="sum">${t('analyzing')}</span>`;
  if (s && s.t === 'diff')
    return `<span class="plus">+${num(e.added)}</span><span class="minus">−${num(e.removed)}</span><span class="sum">${esc(unitWord(s.u, (e.added || 0) + (e.removed || 0)))}</span>`;
  return `<span class="sum">${esc(summaryText(e))}</span>`;
}

/* ------------------------------------------------------------------ data */
// The chosen date range as [since, until] in seconds (either may be missing).
function rangeBounds() {
  const d = new Date(), today = new Date(d.getFullYear(), d.getMonth(), d.getDate()) / 1000;
  if (S.day) return [S.day.since, S.day.since + 86400];          // one day picked with "Go to a day"
  if (S.range === 'today') return [today];
  if (S.range === 'yesterday') return [today - 86400, today];
  if (S.range === '7' || S.range === '30') return [Date.now() / 1000 - +S.range * 86400];
  return [];
}
const rangeSince = () => rangeBounds()[0];

// The current change-list filters as query parameters (for the list and the Excel export).
function eventParams() {
  const p = {};
  if (S.kinds.size) p.kinds = [...S.kinds].join(',');
  if (S.cats.size) p.cats = [...S.cats].join(',');
  if (S.q) p.q = S.q;
  const [since, until] = rangeBounds();
  if (since) p.since = since;
  if (until) p.until = until;
  if (S.starOnly) p.starred = 1;
  if (S.notedOnly) p.noted = 1;
  if (S.folder) p.folder = S.folder;
  if (S.goneOnly) p.gone = 1;  // deleted and still missing (2.4.2)
  return p;
}
const inFolder = (p, f) => !!p && p.startsWith(f.replace(/[\\/]+$/, '') + '\\');

function matches(e) {
  if (S.goneOnly && e.kind !== 'deleted') return false;
  if (S.kinds.size && !S.kinds.has(e.kind)) return false;
  if (S.cats.size && !S.cats.has(e.cat)) return false;
  if (S.starOnly && !e.starred) return false;
  if (S.notedOnly && !e.note) return false;
  if (S.folder && !inFolder(e.path, S.folder) && !inFolder(e.old_path, S.folder)) return false;
  const [since, until] = rangeBounds();
  if ((since && e.ts < since) || (until && e.ts >= until)) return false;
  if (S.q) {
    const q = S.q.toLowerCase();
    if (!e.path.toLowerCase().includes(q) && !(e.old_path || '').toLowerCase().includes(q) && !(e.note || '').toLowerCase().includes(q)) return false;
  }
  return true;
}

async function loadEvents(append = false) {
  if (append && S.loadingMore) return;
  const params = { limit: 150, ...eventParams() };
  if (append && S.events.length) params.before = S.events[S.events.length - 1].id;
  S.loadingMore = append;
  const r = await get('/api/events', params).finally(() => { S.loadingMore = false; });
  r.events.forEach(e => S.byId.set(e.id, e));
  S.events = append ? S.events.concat(r.events) : r.events;
  S.more = r.more;
  if (S.mode === 'changes') renderList();
  renderFilters();
  if (!append && S.mode === 'changes' && S.sel == null && S.events.length && window.innerWidth > 860) select(S.events[0].id, { scroll: false });
}

const contentSearch = () => S.mode === 'files' && S.smode === 'content';

async function loadFiles(append = false) {
  if (append && (S.loadingMore || S.smode === 'content')) return;
  const params = { limit: 200, sort: S.sort, offset: append ? S.files.length : 0 };
  if (S.cats.size) params.cats = [...S.cats].join(',');
  if (S.changedOnly) params.changed = 1;
  if (S.q) params.q = S.q;
  if (S.starOnly) params.starred = 1;
  const req = ++S.filesReq;
  S.loadingMore = append;
  const r = await (S.smode === 'content' ? get('/api/search', { q: S.q, cats: params.cats }) : get('/api/files', params))
    .finally(() => { S.loadingMore = false; });
  if (req !== S.filesReq) return;  // a newer search has already been sent
  if (S.smode === 'content') {
    S.indexed = r.indexed;
    if (S.starOnly) { r.files = r.files.filter(f => f.starred); r.total = r.files.length; }
  }
  S.files = append ? S.files.concat(r.files) : r.files;
  S.fileTotal = r.total;
  const sel = S.fileSel && S.files.find(f => f.path === S.fileSel);
  if (sel) S.fileItem = { ...sel, kind: 'file' };
  $('#fileCount').textContent = num(r.total);
  if (S.mode === 'files') renderList();
}

let filesTimer = null;
function scheduleFiles() { clearTimeout(filesTimer); filesTimer = setTimeout(() => loadFiles(), 1500); }

let statsTimer = null;
function scheduleStats(delay = 700) { clearTimeout(statsTimer); statsTimer = setTimeout(loadStats, delay); }
async function loadStats() {
  S.stats = await get('/api/stats');
  S.status = S.stats.status;
  renderKpis(); renderChart(); renderCats(); renderScope(); renderStatus();
  const nc = $('#notesCount'); if (nc) nc.textContent = S.stats.notes ? num(S.stats.notes) : '';
}

function connect() {
  const es = S.es = new EventSource('/api/stream');
  es.onopen = () => {
    S.connected = true; renderStatus();
    if (S.wasDown) { S.wasDown = false; loadEvents(); loadFiles(); loadStats(); }
  };
  es.onerror = () => { if (S.stopped) return; S.connected = false; S.wasDown = true; renderStatus(); };
  es.onmessage = m => {
    const msg = JSON.parse(m.data);
    if (msg.type === 'event') onEvent(msg.event);
    else if (msg.type === 'update') onUpdate(msg.event);
    else if (msg.type === 'app-update') { S.update = msg.update; renderUpdateBadge(); if (!S.updating) showUpdate(); }
    else if (msg.type === 'status') { S.status = msg.status; renderStatus(); renderScope(); }
    else if (msg.type === 'drive') {  // a removable drive was plugged in (2.6.0 #21)
      const d = msg.drive; S.cleanDrives = null;
      notifyAction(t('usb.text', { d: esc(d.drive.slice(0, 2)), label: esc(d.label || t('cl.removable')), free: fmtSize(d.free), total: fmtSize(d.total) }),
        t('usb.look'), () => { S.cleanDrive = d.drive; S.clean = null; S.cleanFolder = null; setMode('clean'); loadClean(); }, 15000);
    }
    else if (msg.type === 'milestone') notify(t('ms.' + msg.kind, { n: msg.kind === 'freed' ? fmtSize(msg.step) : num(msg.step) }));  // 2.6.0 #50
    else if (msg.type === 'cleared') { S.sel = null; S.selGroup = null; S.byId.clear(); loadEvents(); loadStats(); if (!S.fileSel) renderWelcome(); }
  };
}

// A burst of changes (a folder copied in, unzipped or deleted) redraws the list a few times, not once per
// file (2.1.0: 1,000 files copied in meant 1,000 full redraws, over 5 seconds of work for the window).
let listRenderTimer = 0;
function scheduleListRender() {
  if (listRenderTimer) return;
  listRenderTimer = setTimeout(() => { listRenderTimer = 0; if (S.mode === 'changes') renderList(true); }, 100);
}

function onEvent(e) {
  S.byId.set(e.id, e);
  const added = matches(e) && !S.events.some(x => x.id === e.id);
  if (added) {
    S.events.unshift(e);
    S.fresh.add(e.id);
    setTimeout(() => S.fresh.delete(e.id), 2600);
  }
  if (e.kind === 'deleted') toast(e);  // the list already highlights the rest; a deletion gets its Restore button (2.0.1)
  if (document.hidden) {  // minimized or hidden: keep the data, but redraw and reload nothing until shown (2.1.0)
    S.unseen++; document.title = `(${S.unseen}) ${t('app.name')}`;
    S.missed = true;
    return;
  }
  if (added && S.mode === 'changes') scheduleListRender();
  $('#count').textContent = S.events.length ? num(S.events.length) : '';
  scheduleStats();
  scheduleFiles();
  scheduleGroupDetail();
  scheduleDups();
  scheduleSpace();
}

function onUpdate(e) {
  const before = S.byId.get(e.id);
  S.byId.set(e.id, e);
  const i = S.events.findIndex(x => x.id === e.id);
  if (i >= 0) S.events[i] = e;
  if (document.hidden) { S.missed = true; return; }  // drawn when the window is shown again (2.1.0)
  if (i >= 0) {
    const card = $(`.card[data-id="${e.id}"]`);
    if (card) card.outerHTML = cardHTML(e);
  }
  if (S.sel === e.id && !S.fileSel) {
    const m = $('#dSummary');
    if (m) m.innerHTML = summaryHTML(e);
    const n = $('#dNote');
    if (n && !n.querySelector('.editing')) n.innerHTML = noteViewHTML(e);
    const b = $('#noteAddBtn'); if (b) b.hidden = !!e.note;
  }
  scheduleGroupDetail();
}

// A selected bulk-change card keeps its detail panel current as files are added or analysed.
let groupTimer = null;
function scheduleGroupDetail() {
  if (!S.selGroup) return;
  clearTimeout(groupTimer);
  groupTimer = setTimeout(() => { if (S.selGroup) { renderGroupDetail(findGroup(S.selGroup)); highlight(); } }, 400);
}

/* ------------------------------------------------------------------ list (changes + files) */
function whereHTML(e) {
  if (e.kind === 'renamed' && e.old_path) {
    if (dirname(e.old_path).toLowerCase() === e.dir.toLowerCase())
      return `<span class="sum">${esc(basename(e.old_path))}</span><span class="arrow">→</span><span class="sum">${esc(e.name)}</span>`;
    return `${svg('folder')}<span class="sum">${esc(relTo(e.root, dirname(e.old_path)))}</span><span class="arrow">→</span><span class="sum">${esc(crumb(e))}</span>`;
  }
  return `${svg('folder')}<span class="sum where-link" data-folder-filter="${esc(e.dir)}" title="${esc(t('folder.only'))}">${esc(crumb(e))}</span>`;
}

const STAR_MARK = () => `<span class="starmark" title="${esc(t('star.remove'))}">★</span>`;

// A file name with the part matching the name search highlighted.
function hlName(name) {
  const q = S.q && !contentSearch() ? S.q.toLowerCase() : '';
  const i = q ? name.toLowerCase().indexOf(q) : -1;
  if (i < 0) return esc(name);
  return esc(name.slice(0, i)) + `<mark class="nm">${esc(name.slice(i, i + q.length))}</mark>` + esc(name.slice(i + q.length));
}

function cardHTML(e) {
  const tags = ((e.flags || []).includes('offline') ? `<span class="tag" title="${esc(t('tag.awayTitle'))}">${t('tag.away')}</span>` : '')
;
  return `<div class="card k-${e.kind}${S.sel === e.id && !S.fileSel ? ' sel' : ''}${S.fresh.has(e.id) ? ' fresh' : ''}" data-id="${e.id}">
    <span class="rail"></span>${ficon(e.cat, e.ext)}
    <div class="cbody">
      <div class="crow1"><span class="fname" title="${esc(e.path)}">${hlName(e.name)}</span>${e.starred ? STAR_MARK() : ''}${kbadge(e.kind)}</div>
      <div class="crow2">${whereHTML(e)}${e.kind === 'deleted' ? (e.has_prev_blob ? `<span class="rs-ok" title="${esc(t('rs.okWhy'))}">${t('rs.ok')}</span>` : `<span class="rs-no" title="${esc(t('rs.noWhy'))}">${t('rs.no')}</span>`) : ''}</div>
      <div class="crow3">${summaryHTML(e)}${tags}<span class="time" data-ts="${e.ts}" title="${esc(fmtFull(e.ts))}">${rel(e.ts)} · ${fmtTime(e.ts)}</span></div>
      ${F161 && e.note ? `<div class="cnote" title="${esc(e.note)}">${svg('note')}<span>${esc(e.note)}</span></div>` : ''}
    </div></div>`;
}

function fileCardHTML(f) {
  return `<div class="card k-file${S.fileSel === f.path ? ' sel' : ''}" data-path="${esc(f.path)}">
    ${ficon(f.cat, f.ext)}
    <div class="cbody">
      <div class="crow1"><span class="fname" title="${esc(f.path)}">${hlName(f.name)}</span>${f.starred ? STAR_MARK() : ''}${f.changes ? `<button class="fchanges" data-to-history title="${esc(t('tab.history'))}">${t('files.changes', { n: f.changes })}</button>` : ''}</div>
      <div class="crow2">${svg('folder')}<span class="sum">${esc(crumb(f))}</span></div>
      <div class="crow3"><span class="sum">${fmtSize(f.size)}</span>${f.protect && f.protect !== 'kept' ? protHTML(f.protect) : ''}<span class="time" title="${esc(fmtFull(f.mtime))}">${t('fd.modified', { time: fmtFull(f.mtime) })}</span></div>
      ${f.snippet ? `<div class="snip">${snippetHTML(f.snippet)}</div>` : ''}
    </div></div>`;
}

// Search snippets mark the match with \x02 … \x03.
function snippetHTML(s) {
  return esc(localizeMarkers(s.replace(/\s*\n\s*/g, ' · '), true)).replace(/\x02/g, '<mark>').replace(/\x03/g, '</mark>');
}

const ART = `<svg class="art" viewBox="0 0 160 130"><defs><linearGradient id="ag" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#6d7cff"/><stop offset="1" stop-color="#39b5ff"/></linearGradient></defs>
  <circle cx="80" cy="64" r="58" style="fill:url(#ag)" opacity=".07"/><circle cx="80" cy="64" r="40" style="fill:url(#ag)" opacity=".09"/>
  <g transform="rotate(-9 70 62)"><rect x="46" y="30" width="46" height="60" rx="7" style="fill:var(--panel);stroke:var(--line-2)" stroke-width="1.5"/>
  <rect x="54" y="42" width="22" height="4" rx="2" style="fill:var(--line-2)"/><rect x="54" y="51" width="30" height="4" rx="2" style="fill:var(--line-2)"/></g>
  <rect x="64" y="34" width="48" height="62" rx="7" style="fill:var(--panel);stroke:url(#ag)" stroke-width="2"/>
  <rect x="73" y="47" width="22" height="4.5" rx="2.2" fill="#6d7cff" opacity=".8"/><rect x="73" y="57" width="30" height="4" rx="2" style="fill:var(--line-2)"/>
  <rect x="73" y="66" width="26" height="4" rx="2" style="fill:var(--line-2)"/><rect x="73" y="75" width="18" height="4" rx="2" style="fill:var(--line-2)"/>
  <path d="M76 86l9-12 7 6 10-15" fill="none" stroke="#5b5bf0" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" opacity=".85"/>
  <circle cx="76" cy="86" r="2.6" fill="#5b5bf0"/><circle cx="85" cy="74" r="2.6" fill="#5b5bf0"/><circle cx="92" cy="80" r="2.6" fill="#5b5bf0"/>
  <circle cx="112" cy="92" r="15" style="fill:url(#ag)"/><path d="M104.5 95l4.5-6 3.5 3 5-7" fill="none" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="117.5" cy="85" r="2.8" fill="#34d399" stroke="#fff" stroke-width="1.2"/></svg>`;

const VIEW_GROUPS = { history: ['changes', 'files'], clean: ['clean', 'dups', 'space'] };
const TAB_LABEL = { changes: 'tab.changes', files: 'mode.files', clean: 'cl.tabDrive', dups: 'dup.nav', space: 'sp.tab' };
const TAB_BADGE = { changes: '#count', files: '#fileCount', clean: '#cleanFree', dups: '#dupCount', space: '#spaceTotal' };
const groupOf = m => Object.keys(VIEW_GROUPS).find(g => VIEW_GROUPS[g].includes(m)) || 'history';
function renderTabs() {
  const g = groupOf(S.mode);
  $('#viewTabs').innerHTML = VIEW_GROUPS[g].map(m => `<button data-mode="${m}" class="${m === S.mode ? 'on' : ''}">${t(TAB_LABEL[m])}<span class="n">${esc($(TAB_BADGE[m])?.textContent || '')}</span></button>`).join('');
}

function renderList(prepended = false) {
  const list = $('#list');
  const top = list.scrollTop, before = list.scrollHeight;
  $$('#modeSeg button').forEach(b => b.classList.toggle('on', b.dataset.mode === S.mode || (b.dataset.group && b.dataset.group === groupOf(S.mode))));
  renderTabs();
  $('#pageTitle').textContent = t({ changes: 'page.changes', files: 'page.files', dups: 'page.dups', space: 'page.space', clean: 'page.clean' }[S.mode]);
  $('#dupsTools').hidden = S.mode !== 'dups';
  $('#spaceTools').hidden = S.mode !== 'space';
  $('#cleanTools').hidden = S.mode !== 'clean';
  $('#starBtn').hidden = ['dups', 'space', 'clean'].includes(S.mode);
  $('#notedBtn').hidden = S.mode !== 'changes' || !F161;
  $('#changesTools').hidden = S.mode !== 'changes';
  $('#goneBtn').hidden = S.mode !== 'changes';
  $('#filesTools').hidden = S.mode !== 'files';
  if (S.mode === 'dups') { $('#q').placeholder = t('search.placeholder'); return renderDups(); }
  if (S.mode === 'space') { $('#q').placeholder = t('search.placeholder'); return renderSpace(); }
  if (S.mode === 'clean') { $('#q').placeholder = t('search.placeholder'); return renderClean(); }

  $('#sortSel').hidden = S.smode === 'content';
  $$('#rangeSeg button').forEach(b => b.classList.toggle('on', !S.day && b.dataset.range === S.range));
  $('#starBtn').classList.toggle('on', S.starOnly);
  $('#starBtn').setAttribute('aria-pressed', S.starOnly);
  $$('#searchSeg button').forEach(b => b.classList.toggle('on', b.dataset.smode === S.smode));
  $('#q').placeholder = t(contentSearch() ? 'search.contentPh' : S.mode === 'changes' && F161 ? 'search.withNotes' : 'search.placeholder');
  $('#count').textContent = S.events.length ? `${num(S.events.length)}${S.more ? '+' : ''}` : '';
  if (contentSearch() && !S.files.length) {
    list.innerHTML = `<div class="empty-state">${ART}<h3>${S.q ? t('files.contentEmpty', { q: esc(S.q) }) : t('files.byContent')}</h3>
      <p>${t('files.contentHint', { n: num(S.indexed || 0) })}</p></div>`;
    return;
  }
  if (S.mode === 'files') {
    list.innerHTML = S.files.length
      ? S.files.map(fileCardHTML).join('') + (S.files.length < S.fileTotal
        ? `<div class="more" style="text-align:center"><div class="excl" style="margin-bottom:6px">${t('files.shown', { shown: num(S.files.length), total: num(S.fileTotal) })}</div><button class="btn sm" id="moreFilesBtn">${t('files.more')}</button></div>` : '')
      : `<div class="empty-state">${ART}<h3>${t('files.empty')}</h3></div>`;
    return;
  }
  if (!S.events.length && S.goneOnly) {
    list.innerHTML = `<div class="empty-state">${ART}<h3>${t('del.empty')}</h3><p>${t('del.emptyText')}</p></div>`;
  } else if (!S.events.length) {
    const filtered = S.kinds.size || S.cats.size || S.q || S.day || S.notedOnly || S.starOnly || S.folder || S.range !== 'all';
    list.innerHTML = S.notedOnly && !S.q
      ? `<div class="empty-state">${ART}<h3>${t('notes.emptyTitle')}</h3><p>${t('notes.emptyText')}</p></div>`
      : `<div class="empty-state">${ART}<h3>${t(filtered ? 'list.noMatchTitle' : 'list.emptyTitle')}</h3><p>${t(filtered ? 'list.noMatchText' : 'list.emptyText')}</p></div>`;
  } else {
    let html = S.goneOnly ? `<div class="gone-lead">${svg('restore')}<span>${t('del.lead')}</span></div>` + draftsHTML() : '', last = '';
    if (S.folder && !S.goneOnly) html += `<div class="gone-lead">${svg('clock')}<span>${t('fa.lead')}</span><button class="btn sm" id="folderAtBtn">${t('fa.btn')}…</button></div>`;
    // only deletions shown: offer to bring them all back at once (2.0.1)
    const back = S.kinds.size === 1 && S.kinds.has('deleted') ? S.events.filter(e => e.kind === 'deleted' && e.has_prev_blob) : [];
    if (back.length > 1) html += `<div class="restore-all"><span>${t('restoreAll.text', { n: num(back.length) })}</span>
      <button class="btn sm primary" id="restoreShown">${svg('restore')}${t('restoreAll.btn', { n: num(back.length) })}</button></div>`;
    const perDay = {};  // changes per day header (the last day may be incomplete while more can be loaded)
    S.events.forEach(e => { const d = dayLabel(e.ts); perDay[d] = (perDay[d] || 0) + 1; });
    const lastDay = dayLabel(S.events[S.events.length - 1].ts);
    for (const item of groupEvents(S.events)) {
      const d = dayLabel((item.group ? item.items[0] : item).ts);
      if (d !== last) {
        const n = F161 && !(S.more && d === lastDay) ? `<span class="day-n">${t('day.count', { n: perDay[d], nf: num(perDay[d]) })}</span>` : '';
        html += `<div class="day">${d}${n}</div>`; last = d;
      }
      html += item.group ? groupHTML(item) : cardHTML(item);
    }
    if (S.more) html += `<button class="btn sm more" id="moreBtn">${t('list.more')}</button>`;
    list.innerHTML = html;
  }
  if (prepended && top > 30) list.scrollTop = top + (list.scrollHeight - before);
}

function setMode(mode) {
  if (S.mode === mode) return;
  S.mode = mode;
  saveView();
  renderFilters(); renderKpis();
  renderList();
  $('#list').scrollTop = 0;
  if (mode === 'files') loadFiles();
  if (mode === 'dups') loadDups();
  if (mode === 'space') loadSpace(true);
  if (mode === 'clean') loadClean();
  renderScope();
}

/* ------------------------------------------------------------------ first-run guide (2.4.0) */
// Three short steps, each can be skipped: what to watch (and why DeskTrace, next to Windows' own tools),
// protection starting, and one real undo with a test file DeskTrace makes and deletes itself.
async function showGuide(step = 1) {
  const s = await get('/api/settings').catch(() => null); if (!s) return;
  const head = n => `<div class="m-head"><h3>${t('gd.title')} <span class="hint">${t('gd.step', { n, of: 3 })}</span></h3><button class="icon-btn" data-close>${svg('x')}</button></div>`;
  const foot = (next, label) => `<div class="m-foot"><button class="btn left" id="gdSkip">${t('gd.skip')}</button><button class="btn primary" id="gdNext" data-next="${next}">${label}</button></div>`;
  if (step === 1) {
    openModal(`${head(1)}<div class="m-body"><p>${t('gd.s1')}</p>
      <div class="gd-roots">${s.roots.map(r => `<div class="root">${svg('folder')}<span class="mono">${esc(r)}</span></div>`).join('')}</div>
      <button class="btn sm" id="gdAdd">${svg('plus')}${t('gd.add')}</button>
      <div class="gd-why"><b>${t('gd.whyTitle')}</b>${['gd.why1', 'gd.why2', 'gd.why3', 'gd.why4'].map(k => `<p>${t(k)}</p>`).join('')}</div></div>
      ${foot(2, t('gd.start'))}`, 'upd');
    $('#gdAdd').onclick = async () => { const p = await post('/api/pick-folder'); if (p.path) { await post('/api/settings', { roots: [...s.roots, p.path] }); showGuide(1); } };
  } else if (step === 2) {
    openModal(`${head(2)}<div class="m-body"><p>${t('gd.s2')}</p><div class="gd-big" id="gdCount"><span class="spin"></span></div><p class="hint">${t('gd.s2b')}</p></div>
      ${foot(3, t('gd.next'))}`, 'upd');
    const tick = async () => { const st = await get('/api/stats').catch(() => null); const el = $('#gdCount'); if (!el) return;
      if (st) el.innerHTML = `${svg('shield')} ${t('gd.watching', { n: num(st.status.files || 0) })}`; setTimeout(tick, 1500); };
    tick();
  } else {
    openModal(`${head(3)}<div class="m-body"><p>${t('gd.s3')}</p><ol class="gd-steps">
      <li id="gd1"><button class="btn sm" id="gdMake">${svg('plus')}${t('gd.make')}</button></li>
      <li id="gd2" class="off"><button class="btn sm" id="gdDel" disabled>${svg('trash')}${t('gd.del')}</button></li>
      <li id="gd3" class="off">${t('gd.restore')}</li></ol><p class="hint">${t('gd.s3b')}</p></div>
      <div class="m-foot"><button class="btn left" id="gdSkip">${t('gd.skip')}</button><button class="btn primary" id="gdDone">${t('gd.done')}</button></div>`, 'upd');
    let demo = null;
    $('#gdMake').onclick = async () => { demo = (await post('/api/onboard/demo', { action: 'create', lang: LANG })).path; $('#gd1').classList.add('ok'); $('#gd2').classList.remove('off'); $('#gdDel').disabled = false; };
    $('#gdDel').onclick = async () => {  // the guide finds the deletion itself and offers Restore right here (2.4.1)
      $('#gdDel').disabled = true;
      $('#gdDel').innerHTML = `<span class="spin"></span> ${t('gd.deleting')}`;
      await new Promise(r => setTimeout(r, 3500));  // first DeskTrace keeps the file's copy
      await post('/api/onboard/demo', { action: 'delete', lang: LANG });
      let ev = null;
      for (let k = 0; k < 40 && !ev && $('#gd3'); k++) {
        await new Promise(r => setTimeout(r, 500));
        const d = await get('/api/events', { limit: 20, kinds: 'deleted' }).catch(() => null);
        ev = d && d.events.find(e => e.path === demo && e.has_prev_blob);
      }
      if (!$('#gd3')) return;
      $('#gd2').classList.add('ok'); $('#gd3').classList.remove('off');
      $('#gdDel').innerHTML = `${svg('check')}${t('gd.deleted')}`;
      if (!ev) { $('#gd3').innerHTML = esc(t('gd.notSeen')); return; }
      $('#gd3').innerHTML = `${esc(t('gd.restoreNow'))} <button class="btn sm primary" id="gdRestore">${svg('restore')}${t('gd.restoreBtn')}</button>`;
      $('#gdRestore').onclick = async () => {
        const r = await post('/api/restore', { id: ev.id, version: 'prev', lang: LANG }).catch(() => ({}));
        $('#gd3').classList.add('ok');
        $('#gd3').innerHTML = r.ok ? `<span class="gd-back">${svg('check')}</span>${esc(t('gd.restored'))}` : esc(t('gd.notSeen'));
        if (r.ok) { $('#gd3').classList.add('pop'); S.flashPath = r.path; }
      };
    };
    $('#gdDone').onclick = async () => { await post('/api/onboard/demo', { action: 'cleanup', lang: LANG }); await post('/api/onboard'); closeModal(); notify(t('gd.finished')); };
  }
  $('#gdSkip').onclick = async () => { await post('/api/onboard'); closeModal(); };
  const nx = $('#gdNext'); if (nx) nx.onclick = () => showGuide(+nx.dataset.next);
}

/* ------------------------------------------------------------------ history backup (2.3.0) */
/* Similar photos (2.6.0 #32): a 64-bit difference hash per picture, computed here with a canvas. */
function dhash(img) {
  const c = document.createElement('canvas'); c.width = 9; c.height = 8;
  const g = c.getContext('2d', { willReadFrequently: true }); g.drawImage(img, 0, 0, 9, 8);
  const d = g.getImageData(0, 0, 9, 8).data, lum = i => d[i] * 0.299 + d[i + 1] * 0.587 + d[i + 2] * 0.114;
  let bits = 0n;
  for (let y = 0; y < 8; y++) for (let x = 0; x < 8; x++) bits = (bits << 1n) | (lum((y * 9 + x) * 4) > lum((y * 9 + x + 1) * 4) ? 1n : 0n);
  return bits;
}
const popcount = v => { let n = 0; while (v) { n += Number(v & 1n); v >>= 1n; } return n; };

async function findSimilar() {
  openModal(`<div class="m-head"><h3>${t('sim.title')}</h3><button class="icon-btn" data-close>${svg('x')}</button></div>
    <div class="m-body" id="simBody">${loadingHTML()}</div><div class="m-foot"><button class="btn primary" data-close>${t('btn.close')}</button></div>`, 'upd');
  let all = [];
  for (let off = 0; off < 3000; off += 500) {  // the list comes in pages of 500
    const r = await get('/api/files', { cats: 'image', limit: 500, offset: off, sort: 'recent' }).catch(() => null);
    const page = (r && r.files) || []; all = all.concat(page); if (page.length < 500) break;
  }
  const files = all.filter(f => /\.(jpe?g|png|webp|bmp|gif)$/i.test(f.path) && f.size > 20000);
  const hashes = [];
  for (let i = 0; i < files.length; i++) {
    if (!$('#simBody')) return;  // closed
    if (i % 20 === 0) $('#simBody').innerHTML = `<span class="spin"></span> ${t('sim.reading', { n: num(i), total: num(files.length) })}`;
    const img = new Image(); img.decoding = 'async'; img.src = fileUrl(files[i].path);
    try { await img.decode(); hashes.push({ f: files[i], h: dhash(img), w: img.naturalWidth * img.naturalHeight }); } catch { /* not readable */ }
  }
  const seen = new Set(), groups = [];
  for (let i = 0; i < hashes.length; i++) {
    if (seen.has(i)) continue;
    const g = [hashes[i]];
    for (let j = i + 1; j < hashes.length; j++) if (!seen.has(j) && popcount(hashes[i].h ^ hashes[j].h) <= 6) { g.push(hashes[j]); seen.add(j); }
    if (g.length > 1) groups.push(g.sort((a, b) => b.w - a.w || b.f.size - a.f.size));
  }
  if (!$('#simBody')) return;
  $('#simBody').innerHTML = groups.length ? `<p class="hint">${t('sim.lead', { n: groups.length })}</p>` + groups.slice(0, 60).map(g => `<div class="sim-group">${g.map((x, k) => `
      <figure class="sim-item${k === 0 ? ' best' : ''}"><img loading="lazy" src="${fileUrl(x.f.path)}" alt=""><figcaption>${k === 0 ? `<b>${t('sim.best')}</b> · ` : ''}${esc(x.f.name)} · ${fmtSize(x.f.size)}</figcaption>
        <div class="sim-acts"><button class="btn sm ghost" data-sim-reveal="${esc(x.f.path)}">${svg('folder')}</button>${k ? `<button class="btn sm danger" data-sim-del="${esc(x.f.path)}">${svg('trash')}</button>` : ''}</div></figure>`).join('')}</div>`).join('')
    : `<div class="empty-state small">${t('sim.none', { n: num(hashes.length) })}</div>`;
  $('#simBody').onclick = async ev => {
    const rv = ev.target.closest('[data-sim-reveal]'), dl = ev.target.closest('[data-sim-del]');
    if (rv) post('/api/reveal', { path: rv.dataset.simReveal });
    if (dl) {
      const res = await post('/api/clean/delete', { path: dl.dataset.simDel }).catch(() => ({}));
      if (res.ok) { dl.closest('.sim-item').remove(); notify(t('cl.undoBar', { n: 1 })); } else notify(esc(errText(res)), true);
    }
  };
}

async function startBackup(raw, exportFile = false) {
  const p = await post('/api/pick-folder'); if (!p.path) return;
  const r = await post(exportFile ? '/api/export' : '/api/backup', { dest: p.path, raw });  // 2.6.0 #44: one file for another PC
  if (!r.ok) { notify(esc(errText(r)), true); return; }
  const tick = async () => {
    const b = await get('/api/backup').catch(() => ({}));
    const el = $('#backupState');
    if (b.state === 'running') {
      if (el) el.innerHTML = `<span class="spin"></span> ${t('bk.running', { n: num(b.done || 0), total: num(b.total || 0) })}`;
      return setTimeout(tick, 800);
    }
    if (el) el.textContent = b.state === 'done' ? t('bk.done', { path: b.path }) : '';
    if (b.state === 'done') notifyAction(t('bk.done', { path: `<span class="mono">${esc(b.path)}</span>` }), t('act.reveal'), () => post('/api/clean/reveal', { path: b.path }));
    else notify(esc(t('bk.failed', { why: b.error || '' })), true);
  };
  tick();
}

/* ------------------------------------------------------------------ history storage (2.1.0) */
async function showStorage() {
  openModal(`<div class="m-head"><h3>${t('st.title')}</h3><button class="icon-btn" data-close>${svg('x')}</button></div>
    <div class="m-body" id="stBody">${loadingHTML()}</div><div class="m-foot"><button class="btn primary" data-close>${t('btn.close')}</button></div>`, 'upd');
  const d = await get('/api/storage').catch(() => null);
  if (!d || !$('#stBody')) return;
  const mx = Math.max(1, ...d.files.map(f => f.size));
  $('#stBody').innerHTML = `<p class="hint" style="margin-top:0">${t('st.lead', { size: fmtSize(d.total) })}</p>` + (d.files.map(f => `
    <div class="st-row">${ficon(f.cat, f.ext)}<div class="cbody"><div class="crow1"><span class="fname" title="${esc(f.path)}">${esc(f.name)}</span>
      ${f.exists ? '' : `<span class="tag">${t('path.gone')}</span>`}<b class="sp-size">${fmtSize(f.size)}</b></div>
      <div class="sp-bar"><i style="width:${f.size / mx * 100}%;background:var(--c-${f.cat})"></i></div>
      <div class="crow3"><span class="sum">${t('st.versions', { n: f.versions })}</span>
      ${f.versions > 1 ? `<button class="btn sm ghost danger" data-forget="${esc(f.path)}">${svg('trash')}${t('st.forget')}</button>` : ''}</div></div></div>`).join('')
    || `<div class="empty-state small">${t('st.none')}</div>`);
  $('#stBody').onclick = async ev => {
    const b = ev.target.closest('[data-forget]'); if (!b) return;
    if (!await confirmBox(t('st.forgetTitle'), `<span class="mono" style="font-size:12px">${esc(b.dataset.forget)}</span><br><br>${esc(t('st.forgetText'))}`, t('st.forget'), true)) return showStorage();
    const r = await post('/api/forget', { path: b.dataset.forget });
    notify(r.ok ? t('st.forgotten', { n: num(r.forgotten), size: fmtSize(r.freed) }) : esc(errText(r)), !r.ok);
    loadStats(); showStorage();
  };
}

/* ------------------------------------------------------------------ drive space cleaner (2.2.0; reviewed 2.3.0) */
// Pick a drive; see what takes up the space (charts), tick what may go, confirm one summary, read the
// result. Risk-free items are ticked by default; the Recycle Bin and your own files never are. Caches and
// temporary files are deleted for good; your files go to the Recycle Bin — and only where it really
// keeps them. Windows, programs, synced cloud files and chat data are never offered for deletion.
const CL_HOW = { delete: 'cl.how.delete', recycle: 'cl.how.recycle', empty: 'cl.how.empty', admin: 'cl.how.admin', inapp: 'cl.how.inapp', switch: 'cl.how.switch', compress: 'cl.how.compress' };
const CL_DEFAULT = new Set(['temp', 'wintemp', 'edge', 'chrome', 'firefox', 'otherbrowsers', 'crash', 'thumbs']);  // risk-free: ticked
let cleanTimer = null;
async function loadClean(again = false) {
  clearTimeout(cleanTimer);
  if (!S.cleanDrives) {
    const d = await get('/api/clean/drives').catch(() => null);
    if (!d) return;
    S.cleanDrives = d.drives;
    S.cleanDrive = S.cleanDrive || d.system;
  }
  if (again) { await post('/api/clean/scan', { drive: S.cleanDrive, mode: again === true ? undefined : again }); S.cleanFolder = null; }
  let d = await get('/api/clean/scan', { drive: S.cleanDrive, ...(S.cleanFolder ? { folder: S.cleanFolder } : {}) }).catch(() => null);
  if (!d || !d.ok) return;
  if (!d.state) {  // never read: start now
    await post('/api/clean/scan', { drive: S.cleanDrive });
    d = { ...d, state: 'scanning', files: 0, bytes: 0, items_state: 'scanning' };
  }
  S.clean = d;
  const sideKey = `${d.drive}|${d.state}|${d.cached_at || ''}|${S.cleanActs || 0}`;  // 2.7.0 O4: not on every poll of a running scan
  if (S.cleanSide !== sideKey) {
    S.cleanSide = sideKey;
    S.lastClean = await get('/api/clean/last').catch(() => null);
    S.growth = await get('/api/clean/growth', { drive: d.drive, days: S.growthDays || 1 }).catch(() => null);
  }
  if (d.state !== 'scanning' && (!S.leftovers || S.leftovers.at !== d.cached_at)) {
    S.leftovers = await get('/api/clean/leftovers').catch(() => null); if (S.leftovers) S.leftovers.at = d.cached_at;
  }
  if (!S.cloud) get('/api/clean/cloud').then(r => { S.cloud = r.items || []; }).catch(() => {});
  if (!S.badNames) get('/api/clean/badnames').then(r => { S.badNames = r.items || []; }).catch(() => {});
  if (!S.locales) get('/api/clean/locales').then(r => { S.locales = r.items || []; }).catch(() => {});
  if (!S.gitRepos && d.state !== 'scanning') get('/api/clean/git').then(g => { S.gitRepos = g; if (S.mode === 'clean' && !S.cleanSel) renderCleanOverview(); }).catch(() => {});
  if (!S.moves) get('/api/relocate').then(m => { S.moves = m.moves || []; }).catch(() => {});
  if (!S.health) get('/api/clean/health').then(h => { S.health = h.disks || []; if (S.mode === 'clean' && !S.cleanSel) renderCleanOverview(); }).catch(() => {});
  if (d.items && S.cleanPickFor !== d.drive) {  // the default ticks, once per drive
    S.cleanPick = new Set(d.items.filter(x => CL_DEFAULT.has(x.id)).map(x => x.id));
    S.cleanPickFor = d.drive;
  }
  const di = S.cleanDrives.findIndex(x => x.drive === d.drive);
  if (di >= 0 && d.usage && d.usage.drive) S.cleanDrives[di] = d.usage;
  $('#cleanFree').textContent = d.usage && d.usage.free != null ? fmtSize(d.usage.free) : '';
  if (S.mode !== 'clean') return;
  renderList();
  if (!S.cleanSel) renderCleanOverview();
  if (d.state === 'scanning' || d.items_state === 'scanning') cleanTimer = setTimeout(() => { if (S.mode === 'clean' && !document.hidden) loadClean(); }, 1500);
}

// what a file really takes (2.4.0 §6): next to its size, and why they differ
const usageTags = f => {
  const tags = [];
  if (f.used != null && Math.abs(f.used - f.size) > Math.max(4096, f.size * 0.02)) tags.push(t('cl.sizeVsUsed', { size: fmtSize(f.size), used: fmtSize(f.used) }));
  if (f.links > 1) tags.push(t('cl.shared', { n: f.links }));
  if (f.sparse) tags.push(t('cl.sparse'));
  if (f.compressed) tags.push(t('cl.compressed'));
  if (f.approx) tags.push(t('cl.approx'));
  return tags.length ? `<div class="cl-usage">${tags.map(x => `<span>${x}</span>`).join('')}</div>` : '';
};
const levelBadge = f => `<span class="cl-level l-${f.level}">${t('cl.level.' + f.level)}</span>`;
const clPicked = () => (S.clean && S.clean.items || []).filter(x => S.cleanPick && S.cleanPick.has(x.id) && ['delete', 'recycle'].includes(x.how));
function clTotals(items) {  // what is freed right away, and what only once the Recycle Bin is emptied
  return { now: items.filter(x => x.how === 'delete').reduce((a, x) => a + x.size, 0),
    later: items.filter(x => x.how === 'recycle').reduce((a, x) => a + x.size, 0) };
}

function renderClean() {
  const list = $('#list'), d = S.clean;
  const drives = (S.cleanDrives || []).map(x => `<button class="cl-drive${x.drive === S.cleanDrive ? ' on' : ''}" data-cl-drive="${esc(x.drive)}">
      <b>${esc(x.drive.slice(0, 2))}</b><span class="nm">${esc(x.label || t(x.removable ? 'cl.removable' : 'cl.localDisk'))}</span>
      <span class="sp-bar"><i style="width:${x.total ? (x.used / x.total * 100).toFixed(1) : 0}%"></i></span>
      <span class="hint">${t('cl.free', { free: fmtSize(x.free), total: fmtSize(x.total) })}</span></button>`).join('');
  if (!d) { list.innerHTML = `<div class="cl-drives">${drives}</div>` + loadingHTML(); return; }
  $('#cleanSum').innerHTML = d.state === 'scanning'
    ? `<span class="spin"></span> ${t('cl.scanning', { n: num(d.files || 0), size: fmtSize(d.bytes || 0) })} <button class="btn sm ghost" data-cl-stop>${svg('pause')}${t('cl.stop')}</button>`
    : d.state ? `${d.cached_at ? t('cl.kept', { ago: fmtTime(d.cached_at) }) + ' · ' : ''}${d.cached_at && Date.now() / 1000 - d.cached_at > 86400 ? `<b class="cl-stale">${t('cl.stale')}</b> · ` : ''}${t(d.state === 'stopped' ? 'cl.stopped' : 'cl.scanned', { n: num(d.files), size: fmtSize(d.bytes), s: d.seconds })}
      ${d.mode === 'quick' ? `<span class="cl-how h-recycle" title="${esc(t('cl.quickWhy'))}">${t('cl.quick')}</span>` : ''}
      ${d.skipped || d.online ? `<span class="hint" title="${esc(t('cl.skippedWhy'))}">${t('cl.skipped', { n: num(d.skipped || 0), m: num(d.online || 0) })}</span>` : ''}
      <button class="btn sm ghost" data-cl-rescan="quick" title="${esc(t('cl.quickWhy'))}">${svg('restore')}${t('cl.scanQuick')}</button>
      <button class="btn sm ghost" data-cl-rescan="full">${svg('restore')}${t('cl.scanFull')}</button>` : '';
  if (d.note === 'invalid') $('#cleanSum').innerHTML = `<span class="spin"></span> ${t('cl.invalid')}`;
  const items = d.items || [];
  const card = x => {
    const pick = !['admin', 'empty', 'inapp', 'switch'].includes(x.how);
    const on = pick && S.cleanPick && S.cleanPick.has(x.id);
    return `<label class="card cl-item${x.how === 'admin' ? ' admin' : ''}${on ? ' on' : ''}">
      ${pick ? `<input type="checkbox" class="cl-chk" data-cl-pick="${x.id}" ${on ? 'checked' : ''}>` : `<span class="cl-ic">${svg(x.icon)}</span>`}
      <div class="cbody">
        <div class="crow1"><span class="fname">${x.how === 'inapp' ? t('cl.app.' + x.app) : t('cl.item.' + x.id)}</span><b class="sp-size">${fmtSize(x.size)}</b></div>
        <div class="cl-why">${x.how === 'inapp' ? t('cl.why.app', { app: t('cl.app.' + x.app) }) : x.how === 'switch' ? t(x.on ? 'cl.why.hiber' : 'cl.why.hiberOff') : t('cl.why.' + x.id)}</div>
        <div class="crow3">${x.how === 'delete' && x.level === 'safe' ? `<span class="cl-how h-gone">${t('cl.how.gone')}</span>` : `<span class="cl-how h-${x.how}">${t(CL_HOW[x.how])}</span>`}<span class="sum">${t('cl.count', { n: x.count, nf: num(x.count) })}</span>
          ${x.how === 'admin' ? `<button type="button" class="btn sm" data-cl-win>${svg('open')}${t('cl.openWin')}</button>` : ''}
          ${x.how === 'empty' ? `<button type="button" class="btn sm danger" data-cl-empty>${svg('trash')}${t('cl.empty')}…</button>` : ''}
          ${x.how === 'inapp' ? `${x.exe ? `<button type="button" class="btn sm" data-cl-app="${x.id}">${svg('open')}${t('cl.openApp')}</button>` : ''}
            <button type="button" class="btn sm" data-chat="${x.app}">${svg('trash')}${t('ch.btn')}…</button>
            <button type="button" class="btn sm ghost" data-cl-reveal="${esc(x.data)}">${svg('folder')}${t('cl.openData')}</button>` : ''}
          ${x.how === 'switch' ? `<button type="button" class="btn sm" data-cl-hiber="${x.on ? 'off' : 'on'}">${svg('power')}${t(x.on ? 'cl.hiberOff' : 'cl.hiberOn')}…</button>
            ${x.on ? `<button type="button" class="btn sm" data-cl-hiber="reduced" title="${esc(t('cl.hiberReducedWhy'))}">${t('cl.hiberReduced')}…</button>` : ''}
            <button type="button" class="btn sm ghost" data-cl-power>${t('cl.powerOpts')}</button>` : ''}</div>
      </div></label>`;
  };
  const itemsHTML = items.length ? items.map(card).join('')
    : `<div class="empty-state small">${d.items_state === 'scanning' ? `<span class="spin"></span> ${t('cl.looking')}` : t('cl.nothing')}</div>`;
  const big = (d.big || []).filter(f => !S.q || f.path.toLowerCase().includes(S.q.toLowerCase()));
  const max = Math.max(1, ...big.map(f => f.used ?? f.size));
  const bigHTML = d.state === 'scanning' ? `<div class="empty-state small"><span class="spin"></span> ${t('cl.readingBig')}</div>`
    : big.slice(0, 120).map(f => `<div class="card cl-file${S.cleanSel === f.path ? ' sel' : ''}" data-cl-file="${esc(f.path)}">
      ${ficon(f.cat, f.ext)}<div class="cbody">
        <div class="crow1"><span class="fname" title="${esc(f.path)}">${hlName(f.name)}</span><b class="sp-size" title="${esc(t('cl.usedWhy'))}">${fmtSize(f.used ?? f.size)}</b></div>
        <div class="crow2">${svg('folder')}<span class="sum" title="${esc(f.dir)}">${esc(f.dir)}</span></div>
        <div class="sp-bar"><i style="width:${Math.max(1, (f.used ?? f.size) / max * 100)}%;background:var(--c-${f.cat || 'other'})"></i></div>
        ${usageTags(f)}
        <div class="crow3">${levelBadge(f)}<span class="sum cl-short">${t('cl.file.' + f.why)}</span></div>
      </div></div>`).join('');
  const picked = clPicked(), tot = clTotals(picked);
  const bar = items.length ? `<div class="cl-bar"><div><b>${t('cl.picked', { n: picked.length })}</b>
      <span class="hint">${t('cl.freeNow', { size: fmtSize(tot.now) })}${tot.later ? ' · ' + t('cl.freeLater', { size: fmtSize(tot.later) }) : ''}</span></div>
      <button type="button" class="btn primary" data-cl-go ${picked.length ? '' : 'disabled'}>${svg('trash')}${t('cl.cleanPicked')}…</button></div>` : '';
  const lc = S.lastClean && S.lastClean.n ? `<div class="cl-last">${svg('restore')}<span>${t('cl.lastBar', { n: num(S.lastClean.n), size: fmtSize(S.lastClean.size || 0), when: fmtTime(S.lastClean.at) })}</span>
      <button type="button" class="btn sm" data-cl-back>${t('cl.lastUndo')}</button></div>` : '';
  list.innerHTML = `<div class="cl-drives">${drives}</div>${lc}
    <div class="day">${t('cl.safe')}</div>${itemsHTML}${bar}
    <div class="day">${t('cl.big')}</div>${bigHTML}`;
}

/* The space grid (2.5.0): every block is a folder, its area is the space it takes; a click jumps to the
   folder's row in the list below. Laid out as a squarified treemap so blocks stay close to square. */
const GRID_COLORS = ['var(--accent)', 'var(--c-media)', 'var(--c-archive)', 'var(--created)', 'var(--renamed)', 'var(--c-ppt)', 'var(--modified)', 'var(--c-image)', 'var(--c-code)', 'var(--c-excel)'];
function squarify(items, x, y, w, h) {
  const out = [], total = items.reduce((s, b) => s + b.v, 0) || 1;
  let rest = items.map(b => ({ ...b, a: b.v / total * w * h }));
  const worst = (row, side) => {
    const s = row.reduce((t, b) => t + b.a, 0), mx = Math.max(...row.map(b => b.a)), mn = Math.min(...row.map(b => b.a));
    return Math.max(side * side * mx / (s * s), s * s / (side * side * mn));
  };
  while (rest.length) {
    const side = Math.min(w, h);
    let row = [rest[0]], i = 1;
    while (i < rest.length && worst([...row, rest[i]], side) <= worst(row, side)) row.push(rest[i++]);
    rest = rest.slice(i);
    const s = row.reduce((t, b) => t + b.a, 0);
    if (w >= h) { const cw = s / h; let cy = y; row.forEach(b => { const ch = b.a / cw; out.push({ ...b, x, y: cy, w: cw, h: ch }); cy += ch; }); x += cw; w -= cw; }
    else { const ch = s / w; let cx = x; row.forEach(b => { const cw = b.a / ch; out.push({ ...b, x: cx, y, w: cw, h: ch }); cx += cw; }); y += ch; h -= ch; }
  }
  return out;
}
/* Space Spikes Radar (2.6.0 #1): what grew between two full scans of this drive. */
function badNamesHTML() {  // names Windows cannot handle (2.6.0 #35)
  const L = S.badNames || []; if (!L.length) return '';
  return `<div class="field"><label>${t('bn.title')} <span class="hint">· ${t('bn.hint')}</span></label>
    ${L.slice(0, 12).map(x => `<div class="sp-frow"><span class="sp-folder">${svg(x.dir ? 'folder' : 'warn')}<span class="nm">${esc(x.name)}<span class="hint gr-path">${t('bn.' + x.why)} · ${esc(x.path)}</span></span></span>
      <button class="btn sm" data-fix-name="${esc(x.path)}">${t('bn.fix')}</button></div>`).join('')}</div>`;
}

function localesHTML() {  // programs' language packs: listed only (2.6.0 #27)
  const L = S.locales || []; if (!L.length) return '';
  const tot = L.reduce((s, x) => s + x.size, 0);
  return `<div class="field"><label>${t('lp.title', { size: fmtSize(tot) })} <span class="hint">· ${t('lp.hint')}</span></label>
    ${L.slice(0, 8).map(x => `<div class="sp-frow"><span class="sp-folder">${svg('folder')}<span class="nm">${esc(x.program)}<span class="hint gr-path">${esc(x.path)}</span></span>
      <b>${fmtSize(x.size)}</b></span><button class="btn sm ghost" data-cl-reveal="${esc(x.path)}" title="${esc(t('act.reveal'))}">${svg('open')}</button></div>`).join('')}</div>`;
}

function gitHTML() {  // large Git repositories (2.6.0 #29)
  const G = S.gitRepos; if (!G || !G.items.length) return '';
  return `<div class="field"><label>${t('git.title')} <span class="hint">· ${t('git.hint')}</span></label>
    ${G.items.slice(0, 10).map(x => `<div class="sp-frow"><span class="sp-folder">${svg('code')}<span class="nm">${esc(x.name)}<span class="hint gr-path">${esc(x.path)}</span></span>
      <b>${fmtSize(x.size)}</b></span><button class="btn sm ghost" data-cl-reveal="${esc(x.path)}" title="${esc(t('act.reveal'))}">${svg('open')}</button>
      ${G.git ? `<button class="btn sm" data-git-gc="${esc(x.path)}" title="${esc(t('git.gcWhy'))}">${t('git.gc')}</button>` : ''}</div>`).join('')}
    ${G.git ? '' : `<div class="hint">${t('git.noGit')}</div>`}</div>`;
}

function drawerHTML(parts) {  // the extra Clean up lists, folded into one drawer with a count (Gemini 2.6.0 Q-5)
  const shown = parts.filter(Boolean); if (!shown.length) return '';
  const more = (S.leftovers?.items || []).reduce((s, x) => s + x.size, 0) + (S.gitRepos?.items || []).reduce((s, x) => s + x.size, 0);
  return `<details class="cl-drawer" ${S.drawerOpen ? 'open' : ''}>
    <summary><b>${t('dw.title')}</b> <span class="dw-badge">${t('dw.count', { n: shown.length })}</span>${more ? ` <span class="hint">${t('dw.more', { size: fmtSize(more) })}</span>` : ''}</summary>
    ${shown.join('')}</details>`;
}

function cloudHTML() {  // synced folders: on this PC vs online-only (2.6.0 #30)
  const L = (S.cloud || []).filter(x => x.local_n || x.online_n); if (!L.length) return '';
  return `<div class="field"><label>${t('cd.title')} <span class="hint">· ${t('cd.hint')}</span></label>
    ${L.map(x => `<div class="sp-frow"><span class="sp-folder">${svg('globe')}<span class="nm">${esc(x.name)}<span class="hint gr-path">${t('cd.counts', { n: num(x.local_n), m: num(x.online_n) })} · ${esc(x.path)}</span></span>
      <b>${fmtSize(x.local)}</b></span>${x.local ? `<button class="btn sm" data-cloud-free="${esc(x.path)}" title="${esc(t('cd.why'))}">${t('cd.free')}…</button>` : ''}</div>`).join('')}</div>`;
}

function movedHTML() {  // folders moved to another drive (2.6.0 #3)
  const m = (S.moves || []); if (!m.length) return '';
  return `<div class="field"><label>${t('mvf.listTitle')}</label>${m.map(x => `<div class="sp-frow"><span class="sp-folder">${svg('folder')}
    <span class="nm">${esc(basename(x.src))}<span class="hint gr-path">${esc(x.src)} → ${esc(x.dest)}</span></span><b>${fmtSize(x.size)}</b></span>
    <button class="btn sm" data-cl-moveback="${esc(x.src)}">${t('mvf.back')}…</button></div>`).join('')}</div>`;
}

async function folderMoveRun(start) {  // start a move (or move back) and follow it (2.6.0 #3)
  const r = await start().catch(() => ({ ok: false }));
  if (!r.ok) { closeModal(); notify(esc(errText(r)), true); return; }
  const tick = async () => {
    const m = await get('/api/relocate').catch(() => ({}));
    if (m.state === 'running') {
      const el = $('#mvfState');
      if (el) el.innerHTML = `<span class="spin"></span> ${t('mvf.step.' + (m.step || 'start'), { n: num(m.done || 0), total: num(m.total || 0) })}`;
      return setTimeout(tick, 600);
    }
    closeModal();
    S.moves = m.moves || [];
    const res = m.result || {};
    if (m.state === 'done') notify(res.leftover ? t('mvf.leftover', { path: `<span class="mono">${esc(res.leftover)}</span>` }) : t('mvf.done'), !!res.leftover);
    else if (res.by && res.by.length) notify(t('mvf.busy', { apps: esc(res.by.join(', ')) }), true);
    else notify(esc(t('mvf.failed', { why: res.why || res.code || '' })), true);
    loadClean(true);
  };
  tick();
}

function folderMoveDialog(path) {
  const f = (S.clean?.folders || []).find(x => x.path === path); if (!f) return;
  const drives = (S.cleanDrives || []).filter(x => x.drive.slice(0, 2) !== path.slice(0, 2) && !x.removable && x.free > f.size * 1.1);
  openModal(`<div class="m-head"><h3>${t('mvf.title', { name: esc(f.name) })}</h3><button class="icon-btn" data-close>${svg('x')}</button></div>
    <div class="m-body"><p>${t('mvf.text', { size: fmtSize(f.size) })}</p>
      ${drives.length ? `<select class="sel-sm" id="mvfDrive">${drives.map(x => `<option value="${esc(x.drive)}">${esc(x.drive.slice(0, 2))} ${esc(x.label || '')} · ${t('cl.free', { free: fmtSize(x.free), total: fmtSize(x.total) })}</option>`).join('')}</select>` : `<p class="hint">${t('mvf.noDrive')}</p>`}
      <label class="chk"><input type="checkbox" id="mvfSure"> ${t('mvf.sure')}</label><div class="hint" id="mvfState"></div></div>
    <div class="m-foot"><button class="btn" data-close>${t('btn.cancel')}</button><button class="btn primary" id="mvfGo" disabled>${t('mvf.go')}</button></div>`, 'sm');
  $('#mvfSure').onchange = e => { $('#mvfGo').disabled = !e.target.checked || !drives.length; };
  $('#mvfGo').onclick = () => { $('#mvfGo').disabled = true; folderMoveRun(() => post('/api/relocate', { path, drive: $('#mvfDrive').value })); };
}

async function chatDialog(app, days = 90) {  // a chat app's old received media, by kind (2.6.0 #7)
  openModal(`<div class="m-head"><h3>${t('ch.title', { app: t('cl.app.' + app) })}</h3><button class="icon-btn" data-close>${svg('x')}</button></div>
    <div class="m-body" id="chBody">${loadingHTML()}</div><div class="m-foot"><button class="btn" data-close>${t('btn.cancel')}</button>
    <button class="btn danger" id="chGo" disabled>${svg('trash')}${t('cl.recycleFile')}</button></div>`, 'sm');
  const r = await get('/api/chat-media', { app, days }).catch(() => null);
  if (!r || !r.ok || !$('#chBody')) return;
  const kinds = ['picture', 'video', 'file', 'cache'];
  $('#chBody').innerHTML = `<p>${t('ch.text')}</p>
    <label>${t('ch.older')} <select class="sel-sm" id="chDays">${[30, 90, 180, 365].map(n => `<option value="${n}" ${n === days ? 'selected' : ''}>${t('ch.days', { n })}</option>`).join('')}</select></label>
    ${kinds.map(k => `<label class="chk"><input type="checkbox" data-kind-pick="${k}" ${k === 'cache' || k === 'video' ? 'checked' : ''} ${r.kinds[k].n ? '' : 'disabled'}>
      ${t('ch.k.' + k)} — ${fmtSize(r.kinds[k].size)} (${num(r.kinds[k].n)})</label>`).join('')}
    <p class="hint">${t('ch.never')}</p>`;
  const upd = () => { $('#chGo').disabled = !$$('[data-kind-pick]:checked').length; };
  $$('[data-kind-pick]').forEach(x => x.onchange = upd); upd();
  $('#chDays').onchange = e => chatDialog(app, +e.target.value);
  $('#chGo').onclick = async () => {
    $('#chGo').disabled = true; $('#chGo').innerHTML = `<span class="spin"></span>`;
    const res = await post('/api/chat-media-clean', { app, days: +$('#chDays').value, kinds: $$('[data-kind-pick]:checked').map(x => x.dataset.kindPick) }).catch(() => ({ ok: false }));
    closeModal();
    if (res.ok) notify(t('ch.done', { n: num(res.moved), size: fmtSize(res.freed) })); else notify(esc(errText(res)), true);
    loadClean();
  };
}

function leftoversHTML() {  // possible leftovers of uninstalled programs (2.6.0 #2)
  const L = S.leftovers; if (!L || !L.ready || !L.items.length) return '';
  return `<div class="field"><label>${t('lo.title')} <span class="hint">· ${t('lo.hint')}</span></label>
    ${L.items.slice(0, 12).map(x => `<div class="sp-frow"><span class="sp-folder">${svg('folder')}<span class="nm">${esc(x.name)}<span class="hint gr-path">${esc(x.where)} · ${esc(x.path)}</span></span>
      <b>${fmtSize(x.size)}</b></span><button class="btn sm" data-cl-reveal="${esc(x.path)}">${svg('open')}${t('lo.open')}</button>
      <button class="btn sm danger" data-lo-del="${esc(x.path)}">${svg('trash')}${t('lo.del')}…</button></div>`).join('')}</div>`;
}

function growthHTML() {
  const g = S.growth; if (!g || !g.ok) return '';
  const seg = `<span class="seg small" id="growthSeg">${[1, 7].map(n => `<button data-growth="${n}" class="${(S.growthDays || 1) === n ? 'on' : ''}">${t('gr.days' + n)}</button>`).join('')}</span>`;
  if (!g.ready) return `<div class="field gr-box"><label>${t('gr.title')}</label><div class="hint">${t('gr.notReady', { n: g.scans || 0 })}</div></div>`;
  const max = Math.max(1, ...g.items.map(x => x.grew));
  const span = `${fmtFull(g.from)} → ${fmtFull(g.to)}`;
  const rows = g.items.map(x => `<div class="sp-frow gr-row"><button class="sp-folder" data-cl-folder="${esc(x.path)}" title="${esc(x.path)}">
      ${svg('folder')}<span class="nm">${esc(x.name)}<span class="hint gr-path">${esc(x.path)}</span></span><span class="bar"><i style="width:${(x.grew / max * 100).toFixed(1)}%"></i></span>
      <b class="gr-plus">+${fmtSize(x.grew)}<span class="pct">${x.new ? t('gr.newFolder') : t('gr.was', { size: fmtSize(x.was) })}</span></b></button></div>`).join('');
  return `<div class="field gr-box"><label>${t('gr.title')} ${seg}</label>
    <div class="hint">${t(g.total >= 0 ? 'gr.lead' : 'gr.leadShrunk', { span, total: fmtSize(Math.abs(g.total)) })}</div>
    ${rows || `<div class="hint">${t('gr.none')}</div>`}</div>`;
}

function spaceGridHTML(d) {
  setTimeout(gridPendingJump, 0);  // after a click on a deeper block: show it once its folder is open
  const folders = (d.folders || []).slice(0, 16).filter(f => f.size > 0);
  if (folders.length < 2 || !d.size) return '';
  const rest = Math.max(0, d.size - folders.reduce((s, f) => s + f.size, 0));
  const items = folders.map((f, i) => ({ v: f.size, f, color: GRID_COLORS[i % GRID_COLORS.length] }));
  if (rest > d.size * 0.01) items.push({ v: rest, f: null, color: 'var(--c-other)' });
  const W = 1000, H = 400, pos = (x, y, w, h) => `left:${(x / W * 100).toFixed(3)}%;top:${(y / H * 100).toFixed(3)}%;width:${(w / W * 100).toFixed(3)}%;height:${(h / H * 100).toFixed(3)}%`;
  const label = (name, v, w, h) => w > 90 && h > 34 ? `<span class="nm">${name}</span><span class="sz">${fmtSize(v)} · ${Math.round(v / d.size * 100)}%</span>` : (w > 60 && h > 18 ? `<span class="nm">${name}</span>` : '');
  let html = '';
  for (const c of squarify(items, 0, 0, W, H)) {
    if (!c.f) { html += `<button type="button" class="cl-cell rest" disabled title="${t('cl.gridRest')} · ${fmtSize(c.v)}" style="${pos(c.x, c.y, c.w, c.h)};--cell:${c.color}">${label(t('cl.gridRest'), c.v, c.w, c.h)}</button>`; continue; }
    const subs = (c.f.sub || []).filter(x => x.size >= c.f.size * 0.03);  // under 3 %: part of the grey rest (no slivers)
    const head = 34;
    if (subs.length >= 2 && c.w > 70 && c.h > 70) {  // the block is split into its subfolders (2.5.0)
      html += `<button type="button" class="cl-cell group" data-cl-jump="${esc(c.f.path)}" title="${esc(c.f.path)} · ${fmtSize(c.v)}
${t('cl.tipTop')}" style="${pos(c.x, c.y, c.w, c.h)};--cell:${c.color}">
        <span class="nm">${esc(c.f.name)} <span class="sz">${fmtSize(c.v)} · ${Math.round(c.v / d.size * 100)}%</span></span></button>`;
      const own = Math.max(0, c.f.size - subs.reduce((s, x) => s + x.size, 0));
      const inner = subs.map((sf, k) => ({ v: sf.size, sf, k }));
      if (own > c.f.size * 0.02) inner.push({ v: own, sf: null, k: inner.length });
      for (const b of squarify(inner, c.x + 3, c.y + head, c.w - 6, c.h - head - 3)) {
        const box = `${pos(b.x, b.y, b.w, b.h)};--cell:${c.color};--shade:${55 + (b.k % 4) * 10}%`;
        html += b.sf
          ? `<button type="button" class="cl-cell sub" data-cl-jump="${esc(b.sf.path)}" data-cl-parent="${esc(c.f.path)}" title="${esc(b.sf.path)} · ${fmtSize(b.v)}
${t('cl.tipSub', { dir: esc(c.f.name) })}" style="${box}">${label(esc(b.sf.name), b.v, b.w, b.h)}</button>`
          : `<button type="button" class="cl-cell sub rest" disabled title="${t('cl.gridFiles')} · ${fmtSize(b.v)}" style="${box}">${label(t('cl.gridFiles'), b.v, b.w, b.h)}</button>`;
      }
    } else {
      html += `<button type="button" class="cl-cell" data-cl-jump="${esc(c.f.path)}" title="${esc(c.f.path)} · ${fmtSize(c.v)}
${t('cl.tipTop')}" style="${pos(c.x, c.y, c.w, c.h)};--cell:${c.color}">${label(esc(c.f.name), c.v, c.w, c.h)}</button>`;
    }
  }
  return `<div class="field"><label>${t('cl.grid')} <span class="hint">· ${t('cl.gridHint')}</span></label><div class="cl-grid">${html}</div></div>`;
}
function gridJump(path) {
  const row = [...$$('#detail [data-cl-folder]')].find(x => x.dataset.clFolder === path)?.closest('.sp-frow');
  if (!row) return false;
  row.scrollIntoView({ block: 'center', behavior: 'smooth' });
  row.classList.remove('flash'); void row.offsetWidth; row.classList.add('flash');
  return true;
}
function gridPendingJump() {
  if (S.gridJump && S.clean && S.clean.state !== 'scanning' && gridJump(S.gridJump)) S.gridJump = null;
}

function donutSVG(parts, size = 168) {  // parts: [{v, color, label}]; a ring chart drawn as dashed circles
  const r = 62, c = 2 * Math.PI * r, sum = parts.reduce((a, p) => a + p.v, 0) || 1;
  let off = 0;
  const arcs = parts.filter(p => p.v > 0).map(p => {
    const len = p.v / sum * c;
    const el = `<circle r="${r}" cx="84" cy="84" fill="none" stroke="${p.color}" stroke-width="20" stroke-dasharray="${len.toFixed(2)} ${(c - len).toFixed(2)}"
      stroke-dashoffset="${(-off).toFixed(2)}" transform="rotate(-90 84 84)"><title>${esc(p.label)}: ${fmtSize(p.v)}</title></circle>`;
    off += len;
    return el;
  }).join('');
  return `<svg class="cl-donut" viewBox="0 0 168 168" width="${size}" height="${size}"><circle r="${r}" cx="84" cy="84" fill="none" stroke="var(--line)" stroke-width="20"/>${arcs}</svg>`;
}

function renderCleanOverview() {
  const d = S.clean; if (!d) return;
  S.cleanSel = null;
  $$('.card.sel').forEach(c => c.classList.remove('sel'));
  const u = d.usage || {}, all = (d.items || []).filter(x => ['delete', 'recycle'].includes(x.how)), tot = clTotals(all);
  const bin = (d.items || []).find(x => x.id === 'recycle');
  const cleanable = tot.now + tot.later + (bin ? bin.size : 0);
  const parts = [{ v: Math.max(0, (u.used || 0) - cleanable), color: 'var(--accent)', label: t('cl.used') },
    { v: cleanable, color: 'var(--c-archive)', label: t('cl.cleanable') }, { v: u.free || 0, color: 'var(--created)', label: t('cl.freeL') }];
  const legend = parts.map(p => `<span class="cl-key"><i style="background:${p.color}"></i>${esc(p.label)} <b>${fmtSize(p.v)}</b></span>`).join('');
  const inRoot = !d.folder || d.folder === d.drive;
  const fMax = Math.max(1, ...(d.folders || []).map(f => f.size));
  const tMax = Math.max(1, ...(d.types || []).map(x => x.size));
  const crumbs = inRoot ? '' : `<div class="sp-crumbs"><button class="btn sm" data-cl-up>‹ ${t('cl.up')}</button><span class="mono">${esc(d.folder)}</span>
      <button class="btn sm ghost" data-cl-reveal="${esc(d.folder)}" title="${esc(t('act.reveal'))}">${svg('open')}</button></div>`;
  const scanned = d.state && d.state !== 'scanning';
  $('#detail').innerHTML = `${crumbs}
    <div class="cl-hero">${inRoot ? donutSVG(parts) : ''}
      <div class="cl-hero-text"><span class="hint">${esc(inRoot ? `${d.drive.slice(0, 2)} ${u.label || ''}` : basename(d.folder))}</span>
        <h2>${inRoot ? t('cl.freeBig', { size: fmtSize(u.free || 0) }) : fmtSize(d.size || 0)}</h2>
        <div class="hint">${inRoot ? t('cl.ofTotal', { total: fmtSize(u.total || 0) }) : t('cl.inFiles', { n: num(d.count || 0) })}</div>
        ${inRoot ? `<div class="cl-legend">${legend}</div>` : ''}
        ${inRoot && cleanable ? `<div class="cl-gain">${svg('check')} ${t('cl.gain2', { now: fmtSize(tot.now), later: fmtSize(tot.later + (bin ? bin.size : 0)) })}</div>` : ''}</div></div>
    <div class="tab-body">
      ${!scanned ? `<div class="empty-state small"><span class="spin"></span> ${t('cl.scanning', { n: num(d.files || 0), size: fmtSize(d.bytes || 0) })}</div>` : `
      ${growthHTML()}
      ${spaceGridHTML(d)}
      <div class="field"><label>${t('cl.folders')} <span class="hint">· ${t('cl.drillHint')}</span></label>
        ${(d.folders || []).slice(0, 16).map(f => `<div class="sp-frow"><button class="sp-folder" data-cl-folder="${esc(f.path)}">
          ${svg('folder')}<span class="nm">${esc(f.name)}${f.shared ? ` <span class="cl-usage inline"><span>${t('cl.sharedFolder', { size: fmtSize(f.shared) })}</span></span>` : ''}</span><span class="bar"><i style="width:${(f.size / fMax * 100).toFixed(1)}%"></i></span>
          <b>${fmtSize(f.size)}<span class="pct">${d.size ? Math.round(f.size / d.size * 100) : 0}%</span></b></button>
          ${f.movable ? `<button class="btn sm ghost" data-cl-move="${esc(f.path)}" title="${esc(t('mvf.why'))}">${t('mvf.btn')}</button>` : ''}
          <button class="btn sm ghost" data-cl-reveal="${esc(f.path)}" title="${esc(t('act.reveal'))}">${svg('open')}</button></div>`).join('') || `<div class="hint">${t('sp.noSub')}</div>`}</div>
      ${!inRoot && (d.here || []).length ? `<div class="field"><label>${t('cl.here')}</label>${d.here.slice(0, 20).map(f => `<div class="sp-row cl-here" data-cl-file="${esc(f.path)}">
          ${ficon(f.cat, f.ext)}<span class="nm">${esc(f.name)}</span>${levelBadge(f)}<b>${fmtSize(f.size)}</b></div>`).join('')}</div>` : ''}
      ${inRoot ? `<div class="field"><label>${t('cl.types')}</label><div class="ins-cats">${(d.types || []).map(x => `<div class="ins-cat"><span class="nm mono" title="${x.ext === '(none)' ? esc(t('cl.noExtWhy')) : ''}">${x.ext === '(none)' ? t('cl.noExt') : esc(x.ext)}</span>
          <span class="bar"><i style="width:${(x.size / tMax * 100).toFixed(1)}%"></i></span><b>${fmtSize(x.size)}</b></div>`).join('')}
          ${d.other_types ? `<div class="ins-cat"><span class="nm">${t('cl.other')}</span><span class="bar"><i style="width:${(d.other_types / tMax * 100).toFixed(1)}%"></i></span><b>${fmtSize(d.other_types)}</b></div>` : ''}</div></div>` : ''}
      ${movedHTML()}
      ${drawerHTML([cloudHTML(), leftoversHTML(), gitHTML(), localesHTML(), badNamesHTML()])}
      <div class="field"><label>${t('wt.title')}</label><div class="wt-row">
        <button type="button" class="btn sm" data-cl-tool="cleanmgr" title="${esc(t('wt.cleanmgrWhy'))}">${svg('shield')}${t('wt.cleanmgr')}</button>
        <button type="button" class="btn sm" data-cl-tool="optimize" title="${esc(t('wt.optimizeWhy'))}">${svg('chart')}${t('wt.optimize')}</button>
        ${(S.health || []).map(x => `<span class="dk-health ${x.health === 'Healthy' ? 'ok' : 'bad'}" title="${esc(t('dk.why'))}">${svg(x.health === 'Healthy' ? 'check' : 'warn')}${esc(x.name)} · ${esc(x.media)} · ${t(x.health === 'Healthy' ? 'dk.ok' : 'dk.bad', { s: esc(x.health) })}</span>`).join('')}
        <button type="button" class="btn sm" data-cl-tool="index" title="${esc(t('wt.indexWhy'))}">${svg('info')}${t('wt.index')}</button></div></div>
      ${d.quick_folders && d.quick_folders.length ? `<div class="hint">${t('cl.quickNote')}</div>` : ''}
      ${d.sharing ? `<div class="hint"><span class="spin"></span> ${t('cl.sharing')}</div>` : ''}
      ${d.tiny ? `<div class="hint">${t('cl.tinyNote', { n: num(d.tiny), size: fmtSize(d.tiny_bytes) })}</div>` : ''}
      <div class="hint">${t('cl.note2')}</div>`}
    </div>`;
}

async function selectCleanFile(path) {
  const d = S.clean; if (!d) return;
  const f = [...(d.big || []), ...(d.here || [])].find(x => x.path === path); if (!f) return;
  S.cleanSel = path;
  $$('.card.sel').forEach(c => c.classList.remove('sel'));
  $(`.card[data-cl-file="${CSS.escape(path)}"]`)?.classList.add('sel');
  $('#detail').innerHTML = `
    <div class="d-head">${ficon(f.cat, f.ext, true)}<div class="d-title"><h2>${esc(f.name)}</h2>
      <div class="d-meta"><b>${t('cl.usedLabel', { used: fmtSize(f.used ?? f.size) })}</b><span class="dot"></span><span>${t('cl.sizeLabel', { size: fmtSize(f.size) })}</span><span class="dot"></span><span>${t('fd.modified', { time: fmtFull(f.mtime) })}</span></div>${usageTags(f)}</div>
      <button class="icon-btn d-close" id="dClose" title="${esc(t('btn.close'))}">${svg('x')}</button></div>
    <div class="d-path">${svg('folder', 'fold')}<span class="p">${esc(f.dir)}</span><button class="copy" data-copy="${esc(f.path)}" title="${esc(t('path.copy'))}">${svg('copy')}</button></div>
    <div class="tab-body">
      <div class="cl-conseq l-${f.level}">${levelBadge(f)}<p><b>${t('cl.ifDelete')}</b> ${t('cl.file.' + f.why)}</p></div>
      <div class="cl-hist" id="clHist">${loadingHTML()}</div>
      <div class="d-actions">${f.can_delete ? `<button class="btn sm danger" data-cl-del="${esc(f.path)}">${svg('trash')}${t('cl.recycleFile')}</button>` : ''}
        ${f.level === 'cloud' ? `<button class="btn sm primary" data-cl-online="${esc(f.path)}">${svg('download')}${t('cl.online')}</button>` : ''}
        <button class="btn sm" data-cl-reveal="${esc(f.path)}">${svg('folder')}${t('act.reveal')}</button>
        ${f.why === 'program' ? `<button class="btn sm" data-cl-apps>${svg('open')}${t('cl.openApps')}</button>` : ''}</div>
    </div>`;
  $('#detail').classList.add('open');
  // what DeskTrace's history means for this file (review P0-5)
  const h = await get('/api/clean/history', { path }).catch(() => null);
  if (!h || S.cleanSel !== path || !$('#clHist')) return;
  const key = !h.watched ? 'cl.hist.none' : h.kept ? 'cl.hist.kept' : h.too_big ? 'cl.hist.big' : 'cl.hist.noCopy';
  $('#clHist').innerHTML = `${svg(h.kept ? 'shield' : 'info')}<span>${t(key, { n: h.versions, days: h.keep_days || '∞' })}</span>`;
  $('#clHist').classList.toggle('ok', !!h.kept);
}

// One summary before anything is deleted, one result after (review P0-3)
function cleanConfirm() {
  const picked = clPicked(); if (!picked.length) return;
  const tot = clTotals(picked);
  openModal(`<div class="m-head"><h3>${t('cl.confirmTitle')}</h3><button class="icon-btn" data-close>${svg('x')}</button></div>
    <div class="m-body"><table class="kv-table cl-sum">${picked.map(x => `<tr><td>${t('cl.item.' + x.id)}</td><td class="num">${fmtSize(x.size)}</td>
      <td>${x.how === 'compress' ? `<span class="cl-how h-recycle">${t('cl.how.compress')}</span>` : x.how === 'delete' ? (x.level === 'safe' ? `<span class="cl-how h-gone">${t('cl.how.gone')}</span>` : `<span class="cl-how h-delete">${t('cl.irreversible')}</span>`) : `<span class="cl-how h-recycle">${t('cl.how.recycle')}</span>`}</td></tr>`).join('')}</table>
      <p class="cl-tot"><b>${t('cl.freeNow', { size: fmtSize(tot.now) })}</b>${tot.later ? ` · ${t('cl.freeLater', { size: fmtSize(tot.later) })}` : ''}</p>
      <p class="hint">${t('cl.confirmHint')}</p></div>
    <div class="m-foot"><button class="btn" data-close>${t('btn.cancel')}</button><button class="btn primary" id="clStart">${svg('trash')}${t('cl.start')}</button></div>`, 'sm');
  $('#clStart').onclick = async () => {
    $('#clStart').disabled = true;
    $('#clStart').innerHTML = `<span class="spin"></span> ${t('cl.cleaning')}`;
    const res = [], since = Date.now() / 1000;
    for (const x of picked) res.push({ x, r: await post('/api/clean/run', { drive: S.cleanDrive, id: x.id }).catch(() => ({ ok: false })) });
    cleanResult(res);
    loadClean();
  };
}

function cleanResult(res) {
  const freed = res.reduce((a, { r }) => a + (r.freed || 0), 0), recycled = res.some(({ x, r }) => x.how === 'recycle' && r.cleaned);
  openModal(`<div class="m-head"><h3>${t('cl.resultTitle', { size: fmtSize(freed) })}</h3><button class="icon-btn" data-close>${svg('x')}</button></div>
    <div class="m-body"><table class="kv-table cl-sum"><tr><th></th><th class="num">${t('cl.r.freed')}</th><th class="num">${t('cl.r.done')}</th><th class="num">${t('cl.r.skipped')}</th></tr>
      ${res.map(({ x, r }) => `<tr><td>${t('cl.item.' + x.id)}</td><td class="num">${fmtSize(r.freed || 0)}</td><td class="num">${num(r.cleaned || 0)}</td>
        <td class="num${r.failed ? ' minus' : ''}">${num(r.failed || 0)}</td></tr>`).join('')}</table>
      ${res.some(({ r }) => r.failed) ? `<p class="hint">${t('cl.skippedHint')}</p>` : ''}
      ${recycled ? `<p class="hint">${t('cl.inBinHint2')}</p>` : ''}</div>
    <div class="m-foot">${recycled ? `<button class="btn left" id="clBack">${svg('restore')}${t('cl.lastUndo')}</button>` : ''}<button class="btn primary" data-close>${t('btn.close')}</button></div>`, 'sm');
  if (recycled) $('#clBack').onclick = () => { closeModal(); lastCleanUndo(); };
}
async function lastCleanUndo() {  // put back the last cleanup, any time later (2.4.2: was a 10-second offer)
  const r = await post('/api/clean/last-undo').catch(() => ({ restored: [], failed: [] }));
  if (!r.failed || !r.failed.length) notify(t('cl.lastDone', { n: num((r.restored || []).length) }));
  else notifyAction(t('cl.undoPartly', { n: r.restored.length, m: r.failed.length, first: esc(basename(r.failed[0].path)), why: t('cl.undoWhy.' + (r.failed[0].code || 'notInBin')) }),
    t('cl.openBin'), () => post('/api/clean/bin'));
  S.lastClean = null;
  loadClean();
}
function emptyBinConfirm() {
  const bin = (S.clean.items || []).find(x => x.id === 'recycle'); if (!bin) return;
  openModal(`<div class="m-head"><h3>${t('cl.emptyTitle')}</h3><button class="icon-btn" data-close>${svg('x')}</button></div>
    <div class="m-body"><p>${t('cl.emptyText', { n: num(bin.count), size: fmtSize(bin.size) })}</p>
      <label class="chk"><input type="checkbox" id="clSure"> ${t('cl.sure')}</label></div>
    <div class="m-foot"><button class="btn left" id="clBin">${svg('open')}${t('cl.openBin')}</button><button class="btn" data-close>${t('btn.cancel')}</button>
      <button class="btn danger" id="clEmpty" disabled>${svg('trash')}${t('cl.empty')}</button></div>`, 'sm');
  $('#clBin').onclick = () => post('/api/clean/bin');
  $('#clSure').onchange = ev => { $('#clEmpty').disabled = !ev.target.checked; };
  $('#clEmpty').onclick = async () => {
    const r = await post('/api/clean/run', { drive: S.cleanDrive, id: 'recycle' }).catch(() => ({}));
    closeModal();
    notify(r.ok ? t('cl.cleaned', { size: fmtSize(r.freed || 0) }) : esc(errText(r)), !r.ok);
    loadClean();
  };
}
function hiberConfirm(on) {  // Windows asks for permission itself (UAC); nothing changes silently (2.4.0 §5)
  const h = (S.clean.items || []).find(x => x.id === 'hiber') || {};
  openModal(`<div class="m-head"><h3>${t(on ? 'cl.hiberOnTitle' : 'cl.hiberOffTitle')}</h3><button class="icon-btn" data-close>${svg('x')}</button></div>
    <div class="m-body"><p>${t(on ? 'cl.hiberOnText' : 'cl.hiberOffText', { size: fmtSize(h.size || 0) })}</p><p class="hint">${t('cl.hiberUac')}</p></div>
    <div class="m-foot"><button class="btn left" id="hbPower">${t('cl.powerOpts')}</button><button class="btn" data-close>${t('btn.cancel')}</button>
      <button class="btn primary" id="hbGo">${svg('power')}${t(on ? 'cl.hiberOn' : 'cl.hiberOff')}</button></div>`, 'sm');
  $('#hbPower').onclick = () => post('/api/clean/power');
  $('#hbGo').onclick = async () => { closeModal(); await post('/api/clean/hibernate', { on }); notify(t('cl.hiberAsked')); setTimeout(() => loadClean(), 15000); };
}

function deleteConfirm(f) {  // any file can go, but the user decides knowing what happens (2.5.0)
  const risky = !['personal', 'safe'].includes(f.level), recent = Date.now() / 1000 - (f.mtime || 0) < 86400;
  const uninstall = f.why === 'program' ? `<button type="button" class="btn left" id="clUninst">${svg('open')}${t('cl.openApps')}</button>` : '';
  openModal(`<div class="m-head"><h3>${t('cl.askTitle', { name: esc(f.name) })}</h3><button class="icon-btn" data-close>${svg('x')}</button></div>
    <div class="m-body"><div class="cl-conseq l-${f.level}">${levelBadge(f)}<p><b>${t('cl.ifDelete')}</b> ${t('cl.file.' + f.why)}</p></div>
      ${t('cl.better.' + f.why) !== 'cl.better.' + f.why ? `<p class="hint">${t('cl.better.' + f.why)}</p>` : ''}
      ${recent ? `<p class="hint warn-text">${t('cl.recent')}</p>` : ''}
      ${risky || recent ? `<label class="chk"><input type="checkbox" id="clSure2"> ${t('cl.iKnow')}</label>` : `<p class="hint">${t('cl.toBin')}</p>`}</div>
    <div class="m-foot">${uninstall}<button class="btn primary" data-close>${t('btn.cancel')}</button><button class="btn danger" id="clGo2" ${risky || recent ? 'disabled' : ''}>${svg('trash')}${t('cl.recycleFile')}</button></div>`, 'sm');
  if ($('#clSure2')) $('#clSure2').onchange = ev => { $('#clGo2').disabled = !ev.target.checked; };
  if ($('#clUninst')) $('#clUninst').onclick = () => post('/api/clean/apps').catch(() => {});
  $('#clGo2').onclick = () => { closeModal(); deleteBigFile(f.path); };
}

async function deleteBigFile(path, permanent = false) {
  const since = Date.now() / 1000;
  const r = await post('/api/clean/delete', { path, permanent }).catch(() => ({}));
  if (!r.ok && (r.code === 'noBin' || r.code === 'tooBigForBin')) {  // never silently "for good" (review P0-2)
    openModal(`<div class="m-head"><h3>${t('cl.permTitle')}</h3><button class="icon-btn" data-close>${svg('x')}</button></div>
      <div class="m-body"><p>${t(r.code === 'noBin' ? 'cl.noBinText' : 'cl.tooBigText', { name: esc(basename(path)), size: fmtSize(r.size || 0) })}</p>
        <label class="chk"><input type="checkbox" id="clSure"> ${t('cl.sure')}</label></div>
      <div class="m-foot"><button class="btn" data-close>${t('btn.cancel')}</button><button class="btn danger" id="clPerm" disabled>${svg('trash')}${t('cl.deletePerm')}</button></div>`, 'sm');
    $('#clSure').onchange = ev => { $('#clPerm').disabled = !ev.target.checked; };
    $('#clPerm').onclick = () => { closeModal(); deleteBigFile(path, true); };
    return;
  }
  if (!r.ok) { notify(esc(errText(r)), true); return; }
  S.clean.big = (S.clean.big || []).filter(x => x.path !== path);
  S.clean.here = (S.clean.here || []).filter(x => x.path !== path);
  if (r.recycled) notify(t('cl.undoBar', { n: 1 }) + ' ' + t('cl.inBinHint2'));
  else notify(t('cl.deletedPerm', { name: esc(basename(path)), size: fmtSize(r.size) }));
  S.cleanSel = null; renderList(); renderCleanOverview(); loadClean();
}

async function cleanAct(ev) {
  const b = ev.target.closest('[data-cl-app],[data-cl-hiber],[data-cl-power],[data-cl-drive],[data-cl-pick],[data-cl-go],[data-cl-empty],[data-cl-win],[data-cl-rescan],[data-cl-stop],[data-cl-folder],[data-cl-up],[data-cl-reveal],[data-cl-del],[data-cl-online],[data-cl-apps],[data-cl-file],[data-cl-back],[data-cl-jump],[data-growth],[data-cl-tool],[data-lo-del],[data-git-gc],[data-cl-move],[data-cl-moveback],[data-chat],[data-fix-name],[data-cloud-free]');
  if (!b) return false;
  const ds = b.dataset;
  if (ds.clPick) {  // a checkbox: keep the browser's own toggle, just remember it
    ds.clPick && (b.checked ? S.cleanPick.add(ds.clPick) : S.cleanPick.delete(ds.clPick));
    renderList(); renderCleanOverview();
    return true;
  }
  ev.preventDefault();
  ev.stopPropagation();
  if (ds.clDrive) { S.cleanDrive = ds.clDrive; S.clean = null; S.cleanFolder = null; S.cleanSel = null; renderList(); loadClean(); }
  else if (ds.clGo != null) cleanConfirm();
  else if (ds.clJump) {  // a block of the space grid: show its folder in the list below (2.5.0)
    if (!gridJump(ds.clJump) && ds.clParent) { S.gridJump = ds.clJump; S.cleanFolder = ds.clParent; loadClean(); }  // a deeper block: open its folder first
  }
  else if (ds.clBack != null) lastCleanUndo();
  else if (ds.gitGc) {
    b.disabled = true; b.innerHTML = `<span class="spin"></span> ${t('git.running')}`;
    const r = await post('/api/clean/git-gc', { path: ds.gitGc }).catch(() => ({ ok: false }));
    notify(r.ok ? t('git.done', { size: fmtSize(r.freed || 0) }) : t('git.failed'), !r.ok);
    S.gitRepos = null; loadClean();
  }
  else if (ds.clMove) folderMoveDialog(ds.clMove);
  else if (ds.clMoveback) {
    if (await confirmBox(t('mvf.backTitle'), esc(t('mvf.backText')), t('mvf.back'), false)) {
      openModal(`<div class="m-head"><h3>${t('mvf.back')}</h3></div><div class="m-body"><div class="hint" id="mvfState"></div></div>`, 'sm');
      folderMoveRun(() => post('/api/relocate-back', { path: ds.clMoveback }));
    }
  }
  else if (ds.chat) chatDialog(ds.chat);
  else if (ds.cloudFree) {
    if (!await confirmBox(t('cd.askTitle'), esc(t('cd.askText')), t('cd.free'), false)) return true;
    const r = await post('/api/clean/cloud-free', { path: ds.cloudFree }).catch(() => ({ ok: false }));
    notify(r.ok ? t('cd.done') : esc(errText(r)), !r.ok); S.cloud = null; loadClean();
  }
  else if (ds.fixName) {
    const r = await post('/api/clean/fix-name', { path: ds.fixName }).catch(() => ({ ok: false }));
    if (!r.ok) { notify(esc(errText(r)), true); return true; }
    S.badNames = (S.badNames || []).filter(x => x.path !== ds.fixName);
    notify(t('bn.done', { path: `<span class="mono">${esc(r.path)}</span>` })); renderCleanOverview();
  }
  else if (ds.loDel) {
    const x = (S.leftovers?.items || []).find(i => i.path === ds.loDel); if (!x) return true;
    openModal(`<div class="m-head"><h3>${t('lo.askTitle', { name: esc(x.name) })}</h3><button class="icon-btn" data-close>${svg('x')}</button></div>
      <div class="m-body"><p>${t('lo.askText', { path: `<span class="mono">${esc(x.path)}</span>`, size: fmtSize(x.size) })}</p>
        <label class="chk"><input type="checkbox" id="loSure"> ${t('cl.iKnow')}</label></div>
      <div class="m-foot"><button class="btn primary" data-close>${t('btn.cancel')}</button><button class="btn danger" id="loGo" disabled>${svg('trash')}${t('cl.recycleFile')}</button></div>`, 'sm');
    $('#loSure').onchange = e => { $('#loGo').disabled = !e.target.checked; };
    $('#loGo').onclick = async () => {
      closeModal();
      const r = await post('/api/clean/leftover-delete', { path: x.path }).catch(() => ({}));
      if (!r.ok) { notify(esc(errText(r)), true); return; }
      S.leftovers.items = S.leftovers.items.filter(i => i.path !== x.path);
      notify(t('lo.done', { name: esc(x.name), size: fmtSize(x.size) })); loadClean();
    };
  }
  else if (ds.growth) { S.growthDays = +ds.growth; S.growth = await get('/api/clean/growth', { drive: S.cleanDrive, days: S.growthDays }).catch(() => null); renderCleanOverview(); }
  else if (ds.clApp) post('/api/clean/app', { id: ds.clApp });
  else if (ds.clPower != null) post('/api/clean/power');
  else if (ds.clTool) post('/api/clean/wintool', { tool: ds.clTool });
  else if (ds.clHiber) (ds.clHiber === 'reduced' ? post('/api/clean/hibernate', { reduced: true }).then(() => notify(t('cl.hiberAsked'))) : hiberConfirm(ds.clHiber === 'on'));
  else if (ds.clEmpty != null) emptyBinConfirm();
  else if (ds.clRescan != null) loadClean(ds.clRescan || true);
  else if (ds.clStop != null) { await post('/api/clean/stop', { drive: S.cleanDrive }); setTimeout(loadClean, 600); }
  else if (ds.clFolder) { S.cleanFolder = ds.clFolder; loadClean(); }
  else if (ds.clUp != null) { const up = dirname(S.clean.folder); S.cleanFolder = up && up.length > 3 ? up : null; loadClean(); }
  else if (ds.clReveal) post('/api/clean/reveal', { path: ds.clReveal });
  else if (ds.clApps != null) post('/api/clean/apps').catch(() => {});
  else if (ds.clWin != null) post('/api/clean/windows', { drive: S.cleanDrive });
  else if (ds.clOnline) {
    const r = await post('/api/clean/online', { path: ds.clOnline }).catch(() => ({}));
    notify(r.ok ? t('cl.onlineDone', { size: fmtSize(r.size || 0) }) : esc(errText(r)), !r.ok);
  } else if (ds.clDel) {
    const f = [...(S.clean?.big || []), ...(S.clean?.here || [])].find(x => x.path === ds.clDel);
    if (f) { deleteConfirm(f); return true; }  // always one look at what it means first (2.5.0, Gemini P0-1)
    b.disabled = true; await deleteBigFile(ds.clDel); b.disabled = false;
  }
  else if (ds.clFile) selectCleanFile(ds.clFile);
  return true;
}

/* ------------------------------------------------------------------ space (1.8.0) */
async function loadSpace(overview = false) {
  const d = await get('/api/space', S.spaceFolder ? { folder: S.spaceFolder } : {}).catch(() => null);
  if (!d) return;
  S.space = d;
  if (!d.folder) $('#spaceTotal').textContent = fmtSize(d.total);
  if (S.mode !== 'space') return;
  renderList();
  if (overview || !S.fileSel) renderSpaceOverview();
}
let spaceTimer = null;
function scheduleSpace() { if (S.mode !== 'space') return; clearTimeout(spaceTimer); spaceTimer = setTimeout(() => loadSpace(false), 3000); }

function renderSpace() {
  const list = $('#list'), d = S.space;
  if (!d) { list.innerHTML = loadingHTML(); return; }
  const q = (S.q || '').toLowerCase();
  const pool = S.spaceStale ? d.stale || [] : S.spaceCat ? (d.big_by_cat || {})[S.spaceCat] || [] : d.big;  // a type (1.8.1) or "old" (2.0.1)
  const big = pool.filter(f => !q || f.path.toLowerCase().includes(q));
  $('#spaceSum').innerHTML = t('sp.sum', { size: fmtSize(d.total), n: num(d.files) });
  const max = Math.max(1, ...big.map(f => f.size));
  const head = (S.spaceFolder ? `<button class="chip" data-sp-folder-clear title="${esc(S.spaceFolder)}">${svg('folder')}${esc(basename(S.spaceFolder))}${svg('x')}</button>` : '')
    + (S.spaceCat ? `<button class="chip" data-sp-cat-clear>${t('cat.' + S.spaceCat)}${svg('x')}</button>` : '')
    + (S.spaceStale ? `<button class="chip" data-sp-stale>${svg('clock')}${t('sp.staleChip')}${svg('x')}</button>` : '');
  list.innerHTML = `<div class="day">${t('sp.biggest')}${head}</div>` + (big.map(f => `<div class="card k-space${S.fileSel === f.path ? ' sel' : ''}" data-space="${esc(f.path)}">
      ${ficon(f.cat, f.ext)}<div class="cbody">
        <div class="crow1"><span class="fname" title="${esc(f.path)}">${hlName(f.name)}</span><b class="sp-size">${fmtSize(f.size)}</b></div>
        <div class="crow2">${svg('folder')}<span class="sum">${esc(crumb(f))}</span></div>
        <div class="sp-bar"><i style="width:${Math.max(1, f.size / max * 100)}%;background:var(--c-${f.cat})"></i></div>
      </div></div>`).join('') || `<div class="empty-state">${ART}<h3>${t('list.noMatchTitle')}</h3></div>`);
}

function renderSpaceOverview() {
  const d = S.space; if (!d) return;
  S.fileSel = null;
  $$('.card.sel').forEach(c => c.classList.remove('sel'));
  const catMax = Math.max(1, ...d.cats.map(c => c[1])), fMax = Math.max(1, ...d.folders.map(f => f.size));
  const grow = d.growth;
  const crumbs = d.folder ? `<div class="sp-crumbs"><button class="btn sm" data-sp-up>‹ ${t('sp.all')}</button>
      <span class="mono">${esc(d.folder)}</span>
      <button class="btn sm ghost" data-sp-open="${esc(d.folder)}" title="${esc(t('act.reveal'))}">${svg('open')}</button></div>` : '';
  $('#detail').innerHTML = `${crumbs}
    <div class="d-head"><div class="sp-ring chart">${donutSVG(d.cats.map(([c, s]) => ({ v: s, color: `var(--c-${c})`, label: t('cat.' + c) })), 64)}</div>
      <div class="d-title"><h2>${fmtSize(d.total)}</h2><div class="d-meta"><span>${t('sp.inFiles', { n: num(d.files) })}</span><span class="dot"></span>
        <span class="${grow > 0 ? 'sp-up' : 'sp-down'}">${t(grow >= 0 ? 'sp.grew' : 'sp.shrank', { size: fmtSize(Math.abs(grow)) })}</span></div></div></div>
    <div class="tab-body">
      ${d.roots.length > 1 ? `<div class="field"><label>${t('sp.roots')}</label>${d.roots.map(r => `<div class="sp-row"><span class="nm">${esc(r.path)}</span><b>${fmtSize(r.size)}</b></div>`).join('')}</div>` : ''}
      ${d.stale_files ? `<button class="sp-stale${S.spaceStale ? ' on' : ''}" data-sp-stale>${svg('clock')}<span><b>${t('sp.staleTitle', { size: fmtSize(d.stale_total) })}</b>
        <span class="hint">${t('sp.staleText', { n: num(d.stale_files) })}</span></span></button>` : ''}
      <div class="field"><label>${t('sp.byType')} <span class="hint">· ${t('sp.typeHint')}</span></label><div class="ins-cats">${d.cats.map(([c, s]) => `<button class="ins-cat${S.spaceCat === c ? ' on' : ''}" data-sp-cat="${c}"><span class="nm">${t('cat.' + c)}</span>
        <span class="bar"><i style="width:${s / catMax * 100}%;background:var(--c-${c})"></i></span><b>${fmtSize(s)}</b></button>`).join('')}</div></div>
      <div class="field"><label>${t('sp.foldersIn')}</label>${d.folders.map(f => `<div class="sp-frow"><button class="sp-folder" data-sp-folder="${esc(f.path)}" title="${esc(t('sp.drill'))}">
        ${svg('folder')}<span class="nm">${esc(relTo(d.folder || f.root, f.path))}</span><span class="bar"><i style="width:${f.size / fMax * 100}%"></i></span>
        <b>${fmtSize(f.size)}<span class="pct">${d.total ? Math.round(f.size / d.total * 100) : 0}%</span></b></button>
        <button class="btn sm ghost" data-sp-open="${esc(f.path)}" title="${esc(t('act.reveal'))}">${svg('open')}</button></div>`).join('') || `<div class="hint">${t('sp.noSub')}</div>`}</div>
    </div>`;
}

async function selectSpaceFile(path, tab) {
  const f = await get('/api/file-info', { path }).catch(() => null);
  if (!f || !f.ok) { notify(esc(t('err.gone')), true); return; }
  S.fileSel = path; S.fileItem = { ...f, kind: 'file' }; S.sel = null; S.selGroup = null;
  $$('.card.sel').forEach(c => c.classList.remove('sel'));
  $$('.card[data-space]').find(c => c.dataset.space === path)?.classList.add('sel');
  pickTab(S.fileItem, false);
  if (tab && tabsFor(S.fileItem).some(x => x[0] === tab)) S.tab = tab;
  renderDetail(S.fileItem);
  $('#detail').classList.add('open');
}

/* ------------------------------------------------------------------ duplicates (1.7.0) */
async function hideItem(list, item, on, quiet) {  // "Not duplicates" (2.1.0)
  const r = await post('/api/hide', item ? { list, item, on } : { list, item: '-', clear: true }).catch(() => ({}));
  if (!r.ok) { notify(esc(errText(r)), true); return; }
  await loadDups();
  if (quiet) return;
  if (!item) { notify(t('hide.dupShown')); return; }
  if (on) notifyAction(esc(t('hide.dupDone')), t('hide.undo'), () => hideItem(list, item, false, true));
  else notify(t('hide.dupBack'));
}

async function loadDups() {
  const d = await get('/api/duplicates').catch(() => null);
  if (!d) return;
  S.dups = d;
  $('#dupCount').textContent = d.groups.length ? num(d.groups.length) : '';
  if (S.mode !== 'dups') return;
  if (d.checking) setTimeout(() => { if (S.mode === 'dups') loadDups(); }, 4000);  // large files are being compared (2.0.1)
  renderList();
  const g = S.dupSel && d.groups.find(x => x.hash === S.dupSel);
  if (g) renderDupDetail(g);
  else if (S.dupSel) { S.dupSel = null; renderWelcome(); }
}
let dupTimer = null;
function scheduleDups() { if (S.mode !== 'dups') return; clearTimeout(dupTimer); dupTimer = setTimeout(loadDups, 1500); }  // only while open (2.0.1)

function dupGroups() {
  const q = (S.q || '').toLowerCase();
  const gs = (S.dups ? S.dups.groups : []).filter(g => !q || g.files.some(f => f.path.toLowerCase().includes(q)));
  const by = { wasted: (a, b) => b.wasted - a.wasted, count: (a, b) => b.count - a.count || b.wasted - a.wasted,
    name: (a, b) => a.name.localeCompare(b.name, loc()) }[S.dupSort || 'wasted'];
  return gs.sort(by);
}

function renderDups() {
  const list = $('#list'), d = S.dups;
  if (!d) { list.innerHTML = loadingHTML(); return; }
  const gs = dupGroups();
  $('#dupsSum').innerHTML = (gs.length ? t('dup.sum', { n: gs.length, nf: num(gs.length), size: fmtSize(gs.reduce((a, g) => a + g.wasted, 0)) }) : '')
    + (d.checking ? ` <span class="spin"></span> ${t('dup.checking', { n: num(d.checking) })}` : '');
  if (!gs.length) {
    list.innerHTML = `<div class="empty-state">${ART}<h3>${t(S.q ? 'list.noMatchTitle' : 'dup.emptyTitle')}</h3><p>${t('dup.emptyText', { n: num(d.checked), mb: num(d.limit_mb) })}</p>${hiddenDupsHTML(d)}</div>`;
    return;
  }
  list.innerHTML = gs.map(g => `<div class="card k-dup${S.dupSel === g.hash ? ' sel' : ''}" data-dup="${g.hash}">
      <div class="gicon">${ficon(g.cat, g.ext)}<span class="gcount">${g.count}</span></div>
      <div class="cbody">
        <div class="crow1"><span class="fname" title="${esc(g.name)}">${hlName(g.name)}</span><span class="tag dup-w">${t('dup.wasted', { size: fmtSize(g.wasted) })}</span></div>
        <div class="crow2">${svg('folder')}<span class="sum">${esc([...new Set(g.files.map(f => crumb(f)))].slice(0, 2).join('  ·  '))}${g.files.length > 2 ? ' …' : ''}</span></div>
        <div class="crow3"><span class="sum">${t('dup.copies', { n: g.count })} · ${t('dup.each', { size: fmtSize(g.size) })}</span></div>
      </div></div>`).join('') + `<div class="excl" style="text-align:center;padding:12px">${t('dup.limit', { mb: num(d.limit_mb) })}${hiddenDupsHTML(d)}</div>`;
}
const hiddenDupsHTML = d => d.hidden ? `<div style="margin-top:6px">${t('hide.dupCount', { n: d.hidden, nf: num(d.hidden) })}
  <button class="btn sm ghost" data-unhide="dup_hidden">${t('hide.showAgain')}</button></div>` : '';

function selectDup(hash) {
  const g = dupGroups().find(x => x.hash === hash); if (!g) return;
  S.dupSel = hash; S.sel = null; S.fileSel = null; S.selGroup = null;
  $$('.card.sel').forEach(c => c.classList.remove('sel'));
  $(`.card[data-dup="${hash}"]`)?.classList.add('sel');
  renderDupDetail(g);
  $('#detail').classList.add('open');
}

function renderDupDetail(g) {
  $('#detail').innerHTML = `
    <div class="d-head"><div class="gicon">${ficon(g.cat, g.ext, true)}<span class="gcount">${g.count}</span></div>
      <div class="d-title"><h2>${esc(g.name)}</h2>
        <div class="d-meta"><span>${t('dup.title', { n: g.count })}</span><span class="dot"></span><span>${t('dup.each', { size: fmtSize(g.size) })}</span><span class="dot"></span><b class="dup-free">${t('dup.free', { size: fmtSize(g.wasted) })}</b></div></div>
      <button class="icon-btn d-close" id="dClose" title="${esc(t('btn.close'))}">${svg('x')}</button></div>
    <div class="d-actions"><button class="btn sm primary" data-dup-act="keep-newest">${svg('trash')}${t('dup.keepNewest', { n: g.count - 1 })}</button>
      <button class="btn sm" data-dup-act="link" title="${esc(t('hl.why'))}">${svg('copy')}${t('hl.btn')}</button>
      <button class="btn sm" data-dup-act="not-dup" title="${esc(t('hide.dupHint'))}">${svg('eyeoff')}${t('hide.dup')}</button></div>
    <div class="tab-body">${noteHTML(t('dup.how'))}
      ${g.files.map((f, i) => `<div class="dup-row">${ficon(g.cat, g.ext)}
        <div class="cbody"><div class="crow1"><span class="fname">${esc(f.name)}</span>${i === 0 ? `<span class="tag latest">${t('dup.newest')}</span>` : ''}</div>
          <div class="crow2">${svg('folder')}<span class="sum" title="${esc(f.dir)}">${esc(f.dir)}</span></div>
          <div class="crow3"><span class="time">${t('fd.modified', { time: fmtFull(f.mtime) })}</span></div></div>
        <div class="dup-acts"><button class="btn sm" data-dup-act="open" data-path="${esc(f.path)}" title="${esc(t('act.open'))}">${svg('open')}</button>
          <button class="btn sm" data-dup-act="reveal" data-path="${esc(f.path)}" title="${esc(t('act.reveal'))}">${svg('folder')}</button>
          <button class="btn sm danger" data-dup-act="recycle" data-path="${esc(f.path)}" title="${esc(t('dup.recycle'))}">${svg('trash')}</button></div>
      </div>`).join('')}</div>`;
}

async function dupAct(name, path) {
  if (name === 'open' || name === 'reveal') {
    const r = await post('/api/' + name, { path });
    if (!r.ok) notify(esc(errText(r)), true);
    return;
  }
  if (name === 'not-dup') {  // these files only look alike to a hash check, or are copies on purpose (2.1.0)
    const hash = S.dupSel; if (!hash) return;
    S.dupSel = null; renderWelcome();
    return hideItem('dup_hidden', hash, true);
  }
  if (name === 'link') {  // keep every copy where it is, but store the content once (2.6.0 #13)
    const g = dupGroups().find(x => x.hash === S.dupSel); if (!g) return;
    if (!await confirmBox(t('hl.title', { n: g.files.length }), esc(t('hl.text')), t('hl.go'), false)) return;
    const r = await post('/api/dup-link', { paths: g.files.map(f => f.path) }).catch(() => ({ ok: false }));
    if (!r.ok) { notify(esc(errText(r)), true); return; }
    notify(t('hl.done', { n: r.linked, size: fmtSize(r.freed || 0), m: (r.skipped || []).length }), !!(r.skipped || []).length);
    setTimeout(loadDups, 800);
    return;
  }
  if (name === 'keep-newest') {  // keep the newest copy, recycle the rest (1.7.1)
    const g = dupGroups().find(x => x.hash === S.dupSel); if (!g) return;
    const rest = g.files.slice(1);
    if (!await confirmBox(t('dup.keepTitle', { n: rest.length }), `${esc(t('dup.keepText'))}<br><br><span class="mono" style="font-size:12px">${esc(g.files[0].path)}</span>`, t('dup.recycle'), true)) return;
    let done = 0;
    for (const f of rest) { const r = await post('/api/recycle', { path: f.path }).catch(() => ({})); if (r.ok) done++; }
    notify(t('dup.keptDone', { n: done }), done !== rest.length);
    setTimeout(loadDups, 800);
    return;
  }
  if (!await confirmBox(t('dup.recycleTitle'), `<span class="mono" style="font-size:12px">${esc(path)}</span><br><br>${esc(t('dup.recycleText'))}`, t('dup.recycle'), true)) return;
  const r = await post('/api/recycle', { path });
  if (!r.ok) { notify(esc(errText(r)), true); return; }
  notify(t('dup.recycled'));
  setTimeout(loadDups, 800);
}

function renderFilters() {
  const chips = [];
  if (S.mode === 'changes') S.kinds.forEach(k => chips.push(`<button class="chip" data-rm-kind="${k}">${t('kind.' + k)}${svg('x')}</button>`));
  S.cats.forEach(c => chips.push(`<button class="chip" data-rm-cat="${c}">${t('cat.' + c)}${svg('x')}</button>`));
  if (S.q) chips.push(`<button class="chip" data-rm-q>“${esc(S.q)}”${svg('x')}</button>`);
  if (S.starOnly) chips.push(`<button class="chip" data-rm-star>★ ${t('star.chip')}${svg('x')}</button>`);
  if (S.mode === 'changes' && S.day) chips.push(`<button class="chip" data-rm-day>${svg('clock')}${esc(S.day.label)}${svg('x')}</button>`);
  if (S.mode === 'changes' && S.notedOnly) chips.push(`<button class="chip" data-rm-noted>${svg('note')}${t('notes.chip')}${svg('x')}</button>`);
  if (S.mode === 'changes' && S.goneOnly) chips.push(`<button class="chip" data-rm-gone>${svg('restore')}${t('del.chip')}${svg('x')}</button>`);
  if (S.mode === 'changes' && S.folder) chips.push(`<button class="chip" data-rm-folder title="${esc(S.folder)}">${svg('folder')}${esc(basename(S.folder) || S.folder)}${svg('x')}</button>`);
  if (chips.length > 1) chips.push(`<button class="chip clear" data-rm-all>${t('filter.clearAll')}</button>`);
  $('#activeFilters').innerHTML = chips.join('');
}

function applyFilters() {
  renderFilters(); renderKpis(); renderCats();
  $('#notedBtn').classList.toggle('on', !!S.notedOnly);
  $('#notedBtn').setAttribute('aria-pressed', !!S.notedOnly);
  $('#goneBtn').classList.toggle('on', !!S.goneOnly);
  $('#goneBtn').setAttribute('aria-pressed', !!S.goneOnly);
  $$('#rangeSeg button').forEach(b => b.classList.toggle('on', !S.day && b.dataset.range === S.range));
  if (['dups', 'space', 'clean'].includes(S.mode)) renderList();
  loadEvents();
  loadFiles();
}

/* ------------------------------------------------------------------ sidebar */
function renderKpis() {
  const st = S.stats; if (!st) return;
  $('#kpis').innerHTML = Object.keys(KIND_ICON).map(k => `
    <button class="kpi k-${k}${S.kinds.has(k) ? ' on' : ''}" data-kind="${k}">
      <div class="k-label">${svg(KIND_ICON[k])}${t('kind.' + k)}</div>
      <div class="k-num">${num(st.today[k])}</div>
      <div class="k-all">${t('kpi.allTime', { n: num(st.all[k]) })}</div>
    </button>`).join('');
}

function renderChart() {
  const st = S.stats; if (!st || !$('#chart')) return;  // the sidebar chart was removed in 2.0.1
  const a = st.activity, W = 242, H = 64, n = a.length, gap = 2;
  const bw = (W - gap * (n - 1)) / n, max = Math.max(1, ...a.map(x => x.n));
  let bars = '';
  a.forEach((x, i) => {
    const bx = i * (bw + gap), h = x.n ? Math.max(4, (x.n / max) * H) : 2, y = H - h, r = Math.min(3, bw / 2, h);
    const d = `M${bx},${H}V${y + r}Q${bx},${y} ${bx + r},${y}H${bx + bw - r}Q${bx + bw},${y} ${bx + bw},${y + r}V${H}Z`;
    bars += `<g data-i="${i}"><rect class="hit" x="${bx - gap / 2}" y="0" width="${bw + gap}" height="${H}"/><path class="bar${x.n ? '' : ' zero'}" d="${d}"/></g>`;
  });
  const total = a.reduce((s, x) => s + x.n, 0), peak = a.some(x => x.n) ? max : 0;
  $('#chart').innerHTML = `<svg viewBox="0 0 ${W} ${H + 16}" role="img" aria-label="${esc(t('chart.aria'))}">
      ${bars}<line class="base" x1="0" x2="${W}" y1="${H + .5}" y2="${H + .5}"/>
      <text class="axis" x="0" y="${H + 13}">${t('chart.m2h')}</text><text class="axis" x="${W / 2}" y="${H + 13}" text-anchor="middle">${t('chart.m1h')}</text>
      <text class="axis" x="${W}" y="${H + 13}" text-anchor="end">${t('chart.now')}</text></svg>
    <div class="chart-total">${t('chart.total', { n: total })}${t('chart.peak', { p: peak })}</div>`;
  const tip = $('#tooltip');
  $$('#chart g[data-i]').forEach(g => {
    g.addEventListener('mousemove', ev => {
      const x = a[+g.dataset.i];
      const f = s => new Date(s * 1000).toLocaleTimeString(loc(), { hour: '2-digit', minute: '2-digit', hour12: false });
      tip.innerHTML = `<div class="tt-h">${t('chart.tip', { a: f(x.t), b: f(x.t + st.bucket), n: x.n })}</div>` +
        [['created', x.c], ['modified', x.m], ['deleted', x.d], ['renamed', x.r]].filter(([, v]) => v)
          .map(([k, v]) => `<div class="tt-r"><span>${t('kind.' + k)}</span><b>${v}</b></div>`).join('');
      tip.style.left = Math.min(ev.clientX + 14, innerWidth - tip.offsetWidth - 8) + 'px';
      tip.style.top = (ev.clientY - tip.offsetHeight - 10) + 'px';
      tip.classList.add('on');
    });
    g.addEventListener('mouseleave', () => tip.classList.remove('on'));
  });
}

function renderCats() {
  const st = S.stats; if (!st) return;
  const rows = Object.keys(CAT_TAG).map(c => ({ c, n: st.cats[c] || 0, tr: st.tracked_cats[c] || 0 }))
    .filter(r => r.n || r.tr || S.cats.has(r.c))
    .sort((x, y) => (y.n - x.n) || (y.tr - x.tr));
  $('#cats').innerHTML = rows.map(r => `
    <button class="cat${S.cats.has(r.c) ? ' on' : ''}${r.n ? '' : ' empty'}" data-cat="${r.c}">
      ${ficon(r.c, '')}<span class="c-name">${t('cat.' + r.c)}</span><span class="c-n">${num(r.n)}</span>
      <span class="c-t" title="${esc(t('cats.trackedTitle'))}">${num(r.tr)}</span>
    </button>`).join('') || `<div class="excl">${t('cats.empty')}</div>`;
}

function renderScope() {
  const s = S.status; if (!s) return;
  const st = S.stats;
  const roots = s.roots.map(r => `<div class="root">${svg('folder')}<span>${esc(r)}</span></div>`).join('');
  const base = s.baseline_total
    ? `<div><div class="kv"><span>${t('scope.indexing')}</span><b>${num(s.baseline_done)} / ${num(s.baseline_total)}</b></div>
       <div class="progress"><i style="width:${(100 * s.baseline_done / s.baseline_total).toFixed(1)}%"></i></div></div>` : '';
  $('#scope').innerHTML = `${roots}
    <div class="kv"><span>${t('scope.files')}</span><b>${num(s.files)}</b></div>
    <div class="kv"><span>${t('scope.detection')}</span><b>${s.instant ? t('scope.instant') : t('scope.polling', { s: s.interval })}</b></div>
    <div class="kv"><span>${t('scope.rescan')}</span><b>${s.interval}s · ${s.scan_ms} ms</b></div>
    <div class="kv"><span>${t('scope.storage')}</span><b>${st ? fmtSize(st.storage) + (st.storage_cap_gb ? ` / ${num(st.storage_cap_gb)} GB` : '') : '—'}</b></div>
    ${base}
    <div class="excl">${t('scope.ignoring', { lnk: '<code>.lnk</code> <code>.url</code>', lock: '<code>~$*</code>' })} <a href="#" id="editScope" style="color:var(--accent-ink)">${t('scope.change')}</a></div>`;
  $('#scopeLabel').textContent = S.mode === 'clean' ? t('cl.sub') : s.roots.length === 1 ? s.roots[0] : t('scope.folders', { n: s.roots.length });
}

function renderWarnings() {  // history may be incomplete: never silent (2.3.0, review P0-1)
  const w = (S.status && S.status.warn) || [];
  const away = (S.status && S.status.offline_roots) || [];
  const act = { lowdisk: `<button class="btn sm" data-warn-go="clean">${t('warn.goClean')}</button>`,
    integrity: `<button class="btn sm" data-warn-go="backup">${t('warn.goBackup')}</button>`,
    mass: `<button class="btn sm danger" data-mass="restore">${t('mass.restore')}…</button><button class="btn sm ghost" data-mass="dismiss">${t('mass.dismiss')}</button>`,
    rootgone: away.map(r => `<button class="btn sm ghost" data-root-gone="${esc(r)}">${t('warn.rootgoneBtn')}</button>`).join('') };
  const vars = { dirs: away.map(r => `<span class="mono">${esc(r)}</span>`).join('、') };
  $('#warnBar').hidden = !w.length;
  $('#warnBar').innerHTML = w.map(k => `<div class="warn-row">${svg('warn')}<span><b>${t('warn.' + k)}</b> ${t('warn.' + k + 'Why', vars)}</span>${act[k] || ''}</div>`).join('');
  $$('#warnBar [data-root-gone]').forEach(b => b.onclick = () => rootGoneConfirm(b.dataset.rootGone));
  $('#warnBar').classList.toggle('danger', w.includes('mass'));
  $$('#warnBar [data-mass]').forEach(b => b.onclick = () => b.dataset.mass === 'dismiss' ? post('/api/mass-dismiss').then(refreshStatus) : massConfirm());
}

function refreshStatus() { return get('/api/stats').then(st => { S.stats = st; S.status = st.status; renderStatus(); }).catch(() => {}); }

function massConfirm() {  // many files changed at once: put them all back as they were before (2.6.0 #6)
  const m = S.status && S.status.mass; if (!m) return;
  openModal(`<div class="m-head"><h3>${t('mass.title', { n: num(m.n) })}</h3><button class="icon-btn" data-close>${svg('x')}</button></div>
    <div class="m-body"><p>${t('mass.text', { from: esc(fmtFull(m.since)), to: esc(fmtTime(m.until)) })}</p></div>
    <div class="m-foot"><button class="btn" data-close>${t('btn.cancel')}</button><button class="btn danger" id="massGo">${svg('restore')}${t('mass.go')}</button></div>`, 'sm');
  $('#massGo').onclick = async () => {
    $('#massGo').disabled = true;
    const r = await post('/api/mass-restore', { since: m.since, until: m.until, lang: LANG }).catch(() => ({ restored: 0, failed: 0 }));
    closeModal();
    notify(t('mass.done', { n: num(r.restored || 0), m: num(r.failed || 0) }), !!r.failed);
    refreshStatus(); loadEvents();
  };
}

function draftsHTML() {  // unsaved drafts of Office / WPS (2.6.0 #24)
  const d = S.drafts || []; if (!d.length) return '';
  return `<div class="gone-lead drafts"><div style="flex:1"><b>${t('dr.title')}</b><div class="hint">${t('dr.lead')}</div>
    ${d.slice(0, 8).map(x => `<div class="dr-row"><span class="mono">${esc(x.name)}</span><span class="hint">${esc(fmtFull(x.mtime))} · ${fmtSize(x.size)}</span>
      <button class="btn sm" data-draft-save="${esc(x.path)}">${t('dr.save')}</button></div>`).join('')}</div></div>`;
}

function folderAtDialog() {  // the folder as it was at a time, written as a copy (2.6.0 #31)
  const pad = n => String(n).padStart(2, '0'), d = new Date(Date.now() - 3600 * 1000);
  const v = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  openModal(`<div class="m-head"><h3>${t('fa.title', { name: esc(basename(S.folder)) })}</h3><button class="icon-btn" data-close>${svg('x')}</button></div>
    <div class="m-body"><p>${t('fa.text')}</p><input type="datetime-local" id="faWhen" value="${v}"></div>
    <div class="m-foot"><button class="btn" data-close>${t('btn.cancel')}</button><button class="btn primary" id="faGo">${svg('restore')}${t('fa.go')}</button></div>`, 'sm');
  $('#faGo').onclick = async () => {
    const ts = new Date($('#faWhen').value).getTime() / 1000; if (!ts) return;
    $('#faGo').disabled = true;
    const r = await post('/api/folder-at', { folder: S.folder, ts, lang: LANG }).catch(() => ({ ok: false }));
    closeModal();
    if (!r.ok) { notify(esc(errText(r)), true); return; }
    notifyAction(t('fa.done', { n: num(r.files), m: num(r.missing), path: `<span class="mono">${esc(r.path)}</span>` }), t('act.reveal'), () => post('/api/clean/reveal', { path: r.path }), 15000);
  };
}

function rootGoneConfirm(root) {  // only the user can tell "deleted" from "unplugged" (2.4.2)
  openModal(`<div class="m-head"><h3>${t('rg.title')}</h3><button class="icon-btn" data-close>${svg('x')}</button></div>
    <div class="m-body"><p>${t('rg.text', { dir: `<span class="mono">${esc(root)}</span>` })}</p></div>
    <div class="m-foot"><button class="btn primary" data-close>${t('btn.cancel')}</button><button class="btn danger" id="rgGo">${t('rg.confirm')}</button></div>`, 'sm');
  $('#rgGo').onclick = async () => {
    const r = await post('/api/root-gone', { root }).catch(() => ({}));
    closeModal();
    if (r.ok) notify(t('rg.done', { n: num(r.deleted || 0) }));
    loadEvents();
  };
}

function renderStatus() {
  renderWarnings();
  const el = $('#status'), s = S.status;
  el.classList.remove('paused', 'offline');
  let text;
  if (!S.connected) { el.classList.add('offline'); text = t('status.reconnecting'); }
  else if (!s) text = t('status.starting');
  else if (s.paused) {
    el.classList.add('paused');
    text = s.pause_until ? t('status.pausedUntil', { t: new Date(s.pause_until * 1000).toLocaleTimeString(loc(), { hour: '2-digit', minute: '2-digit', hour12: false }) }) : t('status.paused');
  }
  else text = t(s.instant ? 'status.liveInstant' : 'status.live', { files: num(s.files), s: s.interval });
  $('#statusText').textContent = text;
  el.title = s ? t('status.lastScan', { ms: s.scan_ms }) : '';
  const paused = s && s.paused;
  $('#pauseBtn').innerHTML = paused ? `${svg('play')}${t('btn.resume')}` : `${svg('pause')}${t('btn.pause')}`;
  $('#pauseBtn').classList.toggle('warn', !!paused);
}

/* ------------------------------------------------------------------ bulk changes */
// Runs of the same kind of change, close together in time, are shown as one expandable card.
const GROUP_MIN = 4, GROUP_GAP = 20;

function groupEvents(events) {
  const out = [];
  for (let i = 0; i < events.length;) {
    let j = i + 1;
    while (j < events.length && events[j].kind === events[i].kind && events[j].root === events[i].root
      && events[j - 1].ts - events[j].ts <= GROUP_GAP && dayLabel(events[j].ts) === dayLabel(events[i].ts)) j++;
    if (j - i >= GROUP_MIN) {
      const items = events.slice(i, j);
      out.push({ group: true, key: 'g' + items[items.length - 1].id, kind: items[0].kind, items });
    } else {
      for (let k = i; k < j; k++) out.push(events[k]);
    }
    i = j;
  }
  return out;
}
const findGroup = key => groupEvents(S.events).find(g => g.group && g.key === key);

function commonDir(items) {
  let parts = items[0].dir.split(/[\\/]/);
  for (const e of items) {
    const p = e.dir.split(/[\\/]/);
    let k = 0;
    while (k < parts.length && k < p.length && parts[k].toLowerCase() === p[k].toLowerCase()) k++;
    parts = parts.slice(0, k);
  }
  return parts.join('\\');
}

function groupHTML(g) {
  const e0 = g.items[0], open = S.openGroups.has(g.key);
  const names = g.items.slice(0, 3).map(e => e.name).join(t('g.sep')) + (g.items.length > 3 ? '…' : '');
  const fresh = g.items.some(e => S.fresh.has(e.id));
  return `<div class="group${open ? ' open' : ''}">
    <div class="card gcard k-${g.kind}${S.selGroup === g.key ? ' sel' : ''}${fresh ? ' fresh' : ''}" data-gkey="${g.key}">
      <span class="rail"></span><div class="gicon">${ficon(e0.cat, e0.ext)}<span class="gcount">${g.items.length}</span></div>
      <div class="cbody">
        <div class="crow1"><span class="fname">${t('g.' + g.kind, { n: g.items.length })}</span>${kbadge(g.kind)}</div>
        <div class="crow2">${svg('folder')}<span class="sum">${esc(relTo(e0.root, commonDir(g.items)))}</span></div>
        <div class="crow3"><span class="sum">${esc(names)}</span><span class="time">${fmtTime(g.items[g.items.length - 1].ts)}–${fmtTime(e0.ts)}</span></div>
      </div>
      <button class="gtoggle" data-gtoggle="${g.key}" title="${esc(t(open ? 'g.collapse' : 'g.expand'))}">${svg('chev')}</button>
    </div>
    ${open ? `<div class="gitems">${g.items.map(cardHTML).join('')}</div>` : ''}
  </div>`;
}

function selectGroup(key) {
  const g = findGroup(key); if (!g) return;
  S.selGroup = key; S.sel = null; S.fileSel = null;
  highlight();
  renderGroupDetail(g);
  $('#detail').classList.add('open');
}

function renderGroupDetail(g) {
  if (!g) return renderWelcome();
  const e0 = g.items[0], dir = commonDir(g.items);
  const restorable = g.items.filter(e => e.kind === 'deleted' && e.has_prev_blob);
  $('#detail').innerHTML = `
    <div class="d-head"><div class="gicon">${ficon(e0.cat, e0.ext, true)}<span class="gcount">${g.items.length}</span></div>
      <div class="d-title"><h2>${t('g.' + g.kind, { n: g.items.length })}</h2>
        <div class="d-meta">${kbadge(g.kind)}<span>${esc(fmtFull(g.items[g.items.length - 1].ts))} – ${esc(fmtTime(e0.ts))}</span></div></div>
      <button class="icon-btn d-close" id="dClose" title="${esc(t('btn.close'))}">${svg('x')}</button></div>
    <div class="d-path">${svg('folder', 'fold')}<span class="p">${esc(dir)}</span><button class="copy" data-copy="${esc(dir)}" title="${esc(t('path.copy'))}">${svg('copy')}</button></div>
    <div class="d-actions">
      ${restorable.length ? `<button class="btn sm primary" data-gact="restore-all">${svg('restore')}${t('g.restoreAll', { n: restorable.length })}</button>` : ''}
      ${g.items.some(e => e.kind === 'deleted' ? e.has_prev_blob : e.has_blob) ? `<button class="btn sm" data-gact="restore-to">${svg('restore')}${t('g.restoreTo')}</button>` : ''}
      ${g.items.filter(e => e.kind === 'renamed').length > 1 ? `<button class="btn sm" data-gact="rename-back">${svg('restore')}${t('rb.btn', { n: g.items.filter(e => e.kind === 'renamed').length })}</button>` : ''}
      <button class="btn sm" data-gact="reveal">${svg('folder')}${t('act.reveal')}</button>
    </div>
    <div class="tabs"><button class="tab on">${t('g.files')} <span class="n">${g.items.length}</span></button></div>
    <div class="tab-body">${g.items.map(e => `
      <div class="grow" data-hid="${e.id}">${ficon(e.cat, e.ext)}
        <div class="cbody"><div class="crow1"><span class="fname">${esc(e.name)}</span><span class="time">${fmtTime(e.ts)}</span></div>
        <div class="crow3">${svg('folder')}<span class="sum">${esc(crumb(e))}</span><span class="sum" style="margin-left:auto;display:flex;gap:6px">${summaryHTML(e)}</span></div></div>
      </div>`).join('')}</div>`;
}

async function groupAct(name) {
  const g = findGroup(S.selGroup); if (!g) return;
  if (name === 'rename-back') {  // a batch rename gone wrong: every file back to its old name (2.6.0 #40)
    const ids = g.items.filter(e => e.kind === 'renamed').map(e => e.id);
    openModal(`<div class="m-head"><h3>${t('rb.title', { n: ids.length })}</h3><button class="icon-btn" data-close>${svg('x')}</button></div>
      <div class="m-body"><p>${t('rb.text')}</p></div>
      <div class="m-foot"><button class="btn" data-close>${t('btn.cancel')}</button><button class="btn primary" id="rbGo">${svg('restore')}${t('rb.go')}</button></div>`, 'sm');
    $('#rbGo').onclick = async () => {
      closeModal();
      const r = await post('/api/rename-back', { ids }).catch(() => ({ done: 0, skipped: [] }));
      notify(t(r.skipped && r.skipped.length ? 'rb.partly' : 'rb.done', { n: r.done || 0, m: (r.skipped || []).length }), !!(r.skipped && r.skipped.length));
    };
    return;
  }
  if (name === 'reveal') {
    const r = await post('/api/reveal', { path: commonDir(g.items) });
    if (!r.ok) notify(esc(errText(r)), true);
    return;
  }
  if (name === 'restore-to') {  // copies of these versions in a folder of your choice (2.1.0)
    const to = (await post('/api/pick-folder')).path; if (!to) return;
    const r = await post('/api/restore-many', { ids: g.items.filter(e => e.kind === 'deleted' ? e.has_prev_blob : e.has_blob).map(e => e.id), to });
    if (!r.ok) { notify(esc(errText(r)), true); return; }
    const msg = t('g.restoredTo', { n: r.restored || 0 }) + (r.failed ? ' ' + t('g.failed', { n: r.failed }) : '');
    notifyAction(esc(msg), t('act.reveal'), () => post('/api/reveal', { path: r.path }));
    return;
  }
  const ids = g.items.filter(e => e.kind === 'deleted' && e.has_prev_blob).map(e => e.id);
  if (!await confirmBox(t('g.restoreTitle', { n: ids.length }), esc(t('g.restoreText')), t('restore.ok'))) return;
  const r = await post('/api/restore-many', { ids, lang: LANG });
  notify(t('g.restored', { n: r.restored || 0 }) + (r.failed ? ' ' + t('g.failed', { n: r.failed }) : ''), !!r.failed);
}

/* ------------------------------------------------------------------ detail */
// A detail item is either a change event, or a tracked file ({kind: 'file', ...}).
function currentItem() {
  if (S.mode === 'dups') return null;
  if (S.fileSel) return S.fileItem || null;
  return S.sel != null ? S.byId.get(S.sel) : null;
}

function tabsFor(e) { return baseTabs(e); }
function baseTabs(e) {
  switch (e.kind) {
    case 'file': return [['current', 'tab.content'], ['history', 'tab.history'], ['details', 'tab.details']];
    case 'modified': return [['changes', 'tab.changes'], ['this', 'tab.this'], ['before', 'tab.before'], ['current', 'tab.current'], ['history', 'tab.history'], ['details', 'tab.details']];
    case 'created': return [['this', 'tab.content'], ['current', 'tab.current'], ['history', 'tab.history'], ['details', 'tab.details']];
    case 'deleted': return [['before', 'tab.last'], ['history', 'tab.history'], ['details', 'tab.details']];
    default: return [['current', 'tab.content'], ['history', 'tab.history'], ['details', 'tab.details']];
  }
}

function pickTab(e, keepTab) {
  const tabs = tabsFor(e).map(x => x[0]);
  S.tab = keepTab && tabs.includes(S.tab) ? S.tab : tabs[0];
}

function highlight() {
  $$('.card.sel').forEach(c => c.classList.remove('sel'));
  const card = S.fileSel ? $$('.card[data-path]').find(c => c.dataset.path === S.fileSel)
    : S.selGroup ? $(`.gcard[data-gkey="${S.selGroup}"]`) : $(`.card[data-id="${S.sel}"]`);
  if (card) card.classList.add('sel');
  return card;
}

function select(id, { scroll = true, keepTab = false } = {}) {
  const e = S.byId.get(id); if (!e) return;
  S.sel = id; S.fileSel = null; S.selGroup = null;
  const card = highlight();
  if (card && scroll) card.scrollIntoView({ block: 'nearest' });
  pickTab(e, keepTab);
  renderDetail(e);
  $('#detail').classList.add('open');
}

function selectFile(path, { scroll = true, keepTab = false } = {}) {
  const f = S.files.find(x => x.path === path); if (!f) return;
  S.fileSel = path; S.fileItem = { ...f, kind: 'file' }; S.selGroup = null;
  const card = highlight();
  if (card && scroll) card.scrollIntoView({ block: 'nearest' });
  pickTab(S.fileItem, keepTab);
  renderDetail(S.fileItem);
  $('#detail').classList.add('open');
}

function pathRow(path, mode) {
  const dir = dirname(path), name = basename(path);
  return `<div class="d-path">${svg('folder', 'fold')}${mode === 'from' ? `<span class="lbl">${t('path.from')}</span>` : ''}
    <span class="p">${esc(dir)}\\<b>${esc(name)}</b></span>${mode === 'gone' ? `<span class="gone">${t('path.gone')}</span>` : ''}
    <button class="copy" data-copy="${esc(path)}" title="${esc(t('path.copy'))}">${svg('copy')}</button></div>`;
}

function renderWelcome() {
  $('#detail').innerHTML = `<div class="welcome">${ART}<h2>${t('welcome.title')}</h2><p>${t('welcome.text')}</p>
    <div class="keys"><span><kbd>↑</kbd> <kbd>↓</kbd> ${t('keys.move')}</span><span><kbd>/</kbd> ${t('keys.search')}</span>
      <span><kbd>Enter</kbd> ${t('keys.open')}</span><span><kbd>?</kbd> ${t('keys.help')}</span></div></div>`;
}

const starBtnHTML = e => `<button class="btn sm star-btn${e.starred ? ' on' : ''}" data-act="star" aria-pressed="${!!e.starred}"
  title="${esc(t('star.title'))}">${svg('star')}${t(e.starred ? 'star.remove' : 'star.add')}</button>`
  + `<button class="btn sm pin-btn${e.pinned ? ' on' : ''}" data-act="pin" aria-pressed="${!!e.pinned}" title="${esc(t('pin.why'))}">${svg('shield')}${t(e.pinned ? 'pin.remove' : 'pin.add')}</button>`;  // 2.6.0 #20

const protHTML = p => `<span class="prot p-${p}" title="${esc(t('prot.' + p + 'Why'))}">${svg(p === 'kept' ? 'shield' : 'info')}${t('prot.' + p)}</span>`;

function renderDetail(e) {
  if (!e) return renderWelcome();
  if (!tabsFor(e).some(x => x[0] === S.tab)) pickTab(e, false);
  let meta, actions;
  if (e.kind === 'file') {
    const f = e;
    meta = `<span>${fmtSize(f.size)}</span><span class="dot"></span><span title="${esc(fmtFull(f.mtime))}">${t('fd.modified', { time: fmtFull(f.mtime) })}</span><span class="dot"></span>
      <span>${f.changes ? t('files.changes', { n: f.changes }) : t('fd.noChanges')}</span>${f.protect ? protHTML(f.protect) : ''}`;
    actions = `<button class="btn sm" data-act="open">${svg('open')}${t('act.open')}</button>
      <button class="btn sm" data-act="reveal">${svg('folder')}${t('act.reveal')}</button>
      <a class="btn sm" href="${fileUrl(f.path)}" download="${esc(f.name)}">${svg('download')}${t('act.downloadFile')}</a>
      ${starBtnHTML(f)}`;
  } else {
    const restoreVer = e.kind === 'deleted' ? (e.has_prev_blob && 'prev') : (e.has_blob && 'this');
    const dlHash = e.kind === 'deleted' ? (e.has_prev_blob ? e.prev_hash : null) : (e.has_blob ? e.hash : null);
    const sizeInfo = e.kind === 'modified' && e.old_size != null && e.old_size !== e.size
      ? `${fmtSize(e.old_size)} → ${fmtSize(e.size)}` : fmtSize(e.kind === 'deleted' ? e.old_size : e.size);
    meta = `${kbadge(e.kind)}<span title="${esc(fmtFull(e.ts))}">${esc(fmtFull(e.ts))}</span><span class="dot"></span><span>${sizeInfo}</span><span class="dot"></span>
      <span id="dSummary" style="display:flex;gap:6px;align-items:center">${summaryHTML(e)}</span>`;
    actions = `<button class="btn sm" data-act="open" ${e.exists ? '' : `disabled title="${esc(t('act.openGone'))}"`}>${svg('open')}${t('act.open')}</button>
      <button class="btn sm" data-act="reveal">${svg('folder')}${t('act.reveal')}</button>
      ${restoreVer ? `<button class="btn sm${e.kind === 'deleted' ? ' primary' : ''}" data-act="restore" data-version="${restoreVer}">${svg('restore')}${t(e.kind === 'deleted' ? 'act.restoreFile' : 'act.restoreThis')}</button>` : ''}
      ${e.kind === 'modified' && e.has_blob && e.has_prev_blob ? `<button class="btn sm" data-act="report" title="${esc(t('rep.why'))}">${svg('download')}${t('rep.btn')}</button>` : ''}
      ${e.kind !== 'deleted' ? starBtnHTML(e) : ''}
      ${F161 ? `<button class="btn sm" data-note-edit id="noteAddBtn" ${e.note ? 'hidden' : ''}>${svg('note')}${t('note.add')}</button>` : ''}
      ${moreMenuHTML([
        dlHash && `<a href="${blobUrl(dlHash, e.name)}" download="${esc(e.name)}">${svg('download')}<span>${t('act.download')}</span></a>`,
        F161 && dlHash && `<button data-act="open-version" title="${esc(t('ver.openTitle'))}">${svg('open')}<span>${t('ver.open')}</span></button>`,
        F161 && dlHash && `<button data-act="restore-as" title="${esc(t('ver.saveTitle'))}">${svg('copy')}<span>${t('ver.save')}</span></button>`,
        `<button data-act="copy-path">${svg('copy')}<span>${t('path.copy')}</span></button>`,
        F161 && `<button data-act="ignore" title="${esc(t('ign.title'))}">${svg('eyeoff')}<span>${t('ign.btn')}</span></button>`])}`;
  }
  $('#detail').innerHTML = `
    <div class="d-head">${ficon(e.cat, e.ext, true)}
      <div class="d-title"><h2>${esc(e.name)}</h2><div class="d-meta">${meta}</div></div>
      <button class="icon-btn d-close" id="dClose" title="${esc(t('btn.close'))}">${svg('x')}</button>
    </div>
    ${pathRow(e.path, e.exists ? '' : 'gone')}
    ${e.old_path ? pathRow(e.old_path, 'from') : ''}
    <div class="d-actions">${actions}</div>
    ${F161 && e.kind !== 'file' ? `<div id="dNote">${noteViewHTML(e)}</div>` : ''}
    <div class="tabs">${tabsFor(e).map(([id, key]) => `<button class="tab${id === S.tab ? ' on' : ''}" data-tab="${id}">${t(key)}</button>`).join('')}</div>
    <div class="tab-body" id="tabBody"></div>`;
  loadTab(e);
}

// Less common actions live in a "More" menu so the main ones stay clear (2.0.1).
function moreMenuHTML(items) {
  items = items.filter(Boolean);
  if (!items.length) return '';
  return `<div class="lang-wrap more-wrap"><button class="btn sm" data-more aria-haspopup="menu">${svg('menu')}${t('act.more')}</button>
    <div class="menu act-menu" role="menu" hidden>${items.join('')}</div></div>`;
}

/* A note on a version ("sent to the client") — shown on its card and kept forever. */
const noteViewHTML = e => e.note ? `<div class="d-note">${svg('note')}<span class="txt">${esc(e.note)}</span>
  <button class="btn sm ghost" data-note-edit>${t('note.edit')}</button></div>` : '';

function editNote(e) {
  const box = $('#dNote'); if (!box) return;
  box.innerHTML = `<div class="d-note editing"><textarea id="noteText" maxlength="500" rows="2" placeholder="${esc(t('note.ph'))}">${esc(e.note || '')}</textarea>
    <div class="row"><span class="hint">${t('note.keep')}</span><span class="spacer"></span>
    ${e.note ? `<button class="btn sm danger" id="noteDel">${t('note.remove')}</button>` : ''}
    <button class="btn sm" id="noteCancel">${t('btn.cancel')}</button><button class="btn sm primary" id="noteSave">${t('note.save')}</button></div></div>`;
  const ta = $('#noteText');
  ta.focus(); ta.setSelectionRange(ta.value.length, ta.value.length);
  const done = () => { box.innerHTML = noteViewHTML(e); const b = $('#noteAddBtn'); if (b) b.hidden = !!e.note; };
  const save = async text => {
    const r = await post('/api/note', { id: e.id, text });
    if (!r.ok) { notify(esc(errText(r)), true); return; }
    e.note = r.note || null;
    done();
    loadStats();  // the Notes count in the sidebar
    notify(t(e.note ? 'note.saved' : 'note.removed'));
  };
  $('#noteSave').onclick = () => save(ta.value.trim());
  $('#noteCancel').onclick = done;
  if ($('#noteDel')) $('#noteDel').onclick = () => save('');
  ta.onkeydown = ev => {
    if (ev.key === 'Enter' && (ev.ctrlKey || !ev.shiftKey)) { ev.preventDefault(); save(ta.value.trim()); }
    if (ev.key === 'Escape') { ev.stopPropagation(); done(); }
  };
}

function loadTab(e) {
  const body = $('#tabBody');
  const req = ++S.req;
  body.className = 'tab-body';
  body.innerHTML = loadingHTML();
  body.onclick = body.onchange = null;  // handlers belong to the previous tab's contents
  const live = () => req === S.req;
  switch (S.tab) {
    case 'changes': return renderDiffTab(e, body, live);
    case 'this': return renderVersion(e, e.hash, e.has_blob, body, live, 'this');
    case 'before': return renderVersion(e, e.prev_hash, e.has_prev_blob, body, live, 'before');
    case 'current': return renderCurrent(e, body, live);
    case 'history': return renderHistory(e, body, live);
    case 'details': return renderDetails(e, body, live);
  }
}

function switchTab(id) {
  const e = currentItem(); if (!e) return;
  S.tab = id;
  $$('#detail .tab').forEach(x => x.classList.toggle('on', x.dataset.tab === id));
  loadTab(e);
}

const mediaFromHash = hash => part => `/api/media?${qs({ hash, part })}`;
const mediaFromPath = path => part => `/api/media?${qs({ path, part })}`;

async function renderVersion(e, hash, hasBlob, body, live, which) {
  if (!hash) {
    const s = parseSum(e);
    const why = which === 'this'
      ? (s && (s.t === 'big' || s.t === 'locked' || s.t === 'lowdisk') ? esc(summaryText(e)) : t('v.notCaptured'))
      : t('v.prevNotCaptured');
    body.innerHTML = noteHTML(why + (e.exists ? `<br><button class="btn sm" data-goto="current">${t('v.viewCurrent')}</button>` : ''), true);
    return;
  }
  const r = await get('/api/content', { hash, ext: e.ext });
  if (!live()) return;
  if (!r.ok) { body.innerHTML = noteHTML(t('v.blobGone'), true); return; }
  let pre = '';
  if (!hasBlob && ['pdf', 'image', 'docx', 'pptx', 'xlsx'].includes(r.content.type)) pre = noteHTML(t('v.textOnly'));
  const cmp = e.exists ? `<button class="btn sm" data-cmp-current="${hash}" data-cmp-label="${esc(which === 'before' ? t('tab.before') : fmtFull(e.ts))}">${svg('compare')}${t('cmp.withCurrent')}</button>` : '';
  if (which === 'before' && e.kind === 'modified' && hasBlob)
    pre += `<div class="subbar"><span class="meta">${t('v.beforeHint')}</span><span class="spacer"></span>${cmp}<button class="btn sm" data-act="restore" data-version="prev">${svg('restore')}${t('v.restoreEarlier')}</button></div>`;
  else if (cmp)
    pre += `<div class="subbar"><span class="spacer"></span>${cmp}</div>`;
  renderContent(body, r.content, hasBlob ? blobUrl(hash, e.name) : null, pre, hasBlob ? mediaFromHash(hash) : null);
}

async function renderCurrent(e, body, live) {
  const r = await get('/api/current', { path: e.path });
  if (!live()) return;
  if (!r.ok) { body.innerHTML = noteHTML(esc(errText(r)), true); return; }
  const pre = `<div class="subbar"><span class="meta">${t('cur.live', { size: fmtSize(r.size), time: esc(fmtFull(r.mtime)) })}</span></div>`;
  const find = e.kind === 'file' && contentSearch() && S.q ? S.q : '';
  renderContent(body, r.content, fileUrl(e.path), pre, mediaFromPath(e.path), { preferText: !!find });
  if (find) showHits(body, find);
}

/* Centre ``el`` by scrolling only the panels between it and ``stop`` — never the page itself
   (scrollIntoView would also move the whole app layout). */
function scrollToEl(el, stop) {
  if (!el) return;
  for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
    const st = getComputedStyle(p);
    if (/(auto|scroll)/.test(st.overflowY + st.overflowX)) {
      const c = el.getBoundingClientRect(), b = p.getBoundingClientRect();
      p.scrollTop += c.top - b.top - (b.height - c.height) / 2;
      p.scrollLeft += c.left - b.left - (b.width - c.width) / 2;
    }
    if (p === stop) break;
  }
}

/* Highlight every occurrence of ``q`` in a rendered preview, with previous/next buttons. */
function showHits(body, q) {
  const needle = q.toLowerCase(), nodes = [];
  const walker = document.createTreeWalker(body, NodeFilter.SHOW_TEXT,
    { acceptNode: n => n.parentElement.closest('mark, .subbar, .note, script, style') ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT });
  for (let n; (n = walker.nextNode());) if (n.nodeValue.toLowerCase().includes(needle)) nodes.push(n);
  const hits = [];
  for (const node of nodes) {
    if (hits.length >= 500) break;
    const text = node.nodeValue, low = text.toLowerCase(), frag = document.createDocumentFragment();
    let i = 0;
    for (let j; (j = low.indexOf(needle, i)) !== -1; i = j + q.length) {
      frag.append(text.slice(i, j));
      const m = document.createElement('mark');
      m.className = 'hit';
      m.textContent = text.slice(j, j + q.length);
      frag.append(m);
      hits.push(m);
    }
    frag.append(text.slice(i));
    node.replaceWith(frag);
  }
  const bar = document.createElement('div');
  bar.className = 'hitbar';
  bar.innerHTML = hits.length
    ? `<span>${t('hits.count', { n: hits.length, q: esc(q) })}</span><span class="spacer"></span>
       <button class="btn sm" data-hit="-1" title="${esc(t('hits.prev'))}">‹</button><span class="pos">1 / ${hits.length}</span><button class="btn sm" data-hit="1" title="${esc(t('hits.next'))}">›</button>`
    : `<span>${t('hits.none', { q: esc(q) })}</span>`;
  body.prepend(bar);
  let cur = 0;
  const go = i => {
    if (!hits.length) return;
    hits[cur].classList.remove('on');
    cur = (i + hits.length) % hits.length;
    hits[cur].classList.add('on');
    scrollToEl(hits[cur], body);
    $('.pos', bar).textContent = `${cur + 1} / ${hits.length}`;
  };
  bar.onclick = ev => { const b = ev.target.closest('[data-hit]'); if (b) go(cur + +b.dataset.hit); };
  go(0);
}

async function scrubTo(e, kept, i) {  // show version i of the time slider (2.6.0 #11)
  const k = kept[i], box = $('#scrubView'); if (!k || !box) return;
  $('#scrubLabel').textContent = `${i + 1} / ${kept.length} · ${fmtFull(k.x.ts)}`;
  if (e.cat === 'image') { box.innerHTML = `<div class="img-view"><img src="${blobUrl(k.v, e.name)}" alt=""></div>`; return; }
  const r = await get('/api/content', { hash: k.v, ext: e.ext }).catch(() => null);
  if (!$('#scrubView') || +$('#scrubRange').value !== i) return;  // moved on meanwhile
  const lines = (r && r.ok && r.content && r.content.lines) || [];
  box.innerHTML = lines.length ? `<pre class="scrub-text">${esc(lines.slice(0, 400).join('\n'))}</pre>` : `<div class="meta">${t('sc.noText')}</div>`;
}

async function renderHistory(e, body, live) {
  const list = await get('/api/history', { path: e.path });
  if (!live()) return;
  list.forEach(x => { if (!S.byId.has(x.id)) S.byId.set(x.id, x); });
  const pick = (v, ts, label) => `<label class="vpick" title="${esc(t('cmp.pickTitle'))}"><input type="checkbox" data-v="${v || ''}" data-ts="${ts}"
    data-label="${esc(label)}" ${v ? '' : 'disabled'}></label>`;
  const onDisk = e.kind === 'file' || e.exists;
  const kept = list.map(x => ({ x, v: x.kind === 'deleted' ? x.prev_hash : x.hash, has: x.kind === 'deleted' ? x.has_prev_blob : x.has_blob }))
    .filter(k => k.v && k.has).reverse();  // oldest first, for the time slider (2.6.0 #11)
  body.innerHTML = `<div class="subbar"><span class="meta">${t('hist.count', { n: list.length })}</span><span class="spacer"></span>
      ${kept.length > 1 ? `<button class="btn sm" id="scrubBtn">${svg('clock')}${t('sc.btn')}</button>` : ''}
      <button class="btn sm" id="treeBtn">${svg('copy')}${t('lt.btn')}</button>
      <span class="meta" id="cmpHint">${t('cmp.pick')}</span><button class="btn sm" id="cmpBtn" disabled>${svg('compare')}${t('cmp.btn')}</button></div>
    <div id="scrub" hidden></div>
    <div class="hist">
      ${onDisk ? `<div class="h-item k-current">${pick('current', 9e12, t('cmp.current'))}<div class="h-top"><b>${t('cmp.current')}</b></div></div>` : ''}
      ${list.map(x => {
        const v = x.kind === 'deleted' ? x.prev_hash : x.hash;  // the version this change left behind
        const has = x.kind === 'deleted' ? x.has_prev_blob : x.has_blob;
        const open = F161 && v && has ? `<button class="btn sm ghost h-open" data-act="open-version" data-hash="${v}" data-ts="${x.ts}" title="${esc(t('ver.openTitle'))}">${svg('open')}${t('ver.open')}</button>` : '';
        return `<div class="h-item k-${x.kind}${x.id === e.id ? ' on' : ''}" data-hid="${x.id}">${pick(v, x.ts, fmtFull(x.ts))}
          <div class="h-top">${kbadge(x.kind)}<span class="h-time" title="${esc(fmtFull(x.ts))}">${esc(fmtFull(x.ts))}</span>${open}</div>
          <div class="h-sum" style="display:flex;gap:6px;align-items:center">${summaryHTML(x)}${x.has_blob ? `<span class="tag">${t('hist.snapshot')}</span>` : ''}</div>
          ${F161 && x.note ? `<div class="cnote">${svg('note')}<span>${esc(x.note)}</span></div>` : ''}
        </div>`;
      }).join('')}</div>`;
  const picked = () => $$('.vpick input:checked', body);
  body.onchange = ev => {
    if (!ev.target.matches('.vpick input')) return;
    const on = picked();
    if (on.length > 2) on.filter(x => x !== ev.target)[0].checked = false;  // keep the two most recent picks
    $('#cmpBtn').disabled = picked().length !== 2;
  };
  $('#treeBtn', body).onclick = async () => {  // evolution tree (2.6.0 #38)
    const sc = $('#scrub', body); sc.hidden = false;
    const L = await get('/api/lineage', { path: e.path }).catch(() => null); if (!L) return;
    const vs = L.versions, W = 640, gap = vs.length > 1 ? Math.min(90, (W - 60) / (vs.length - 1)) : 0, y0 = 30;
    const xOf = h => { const i = vs.findIndex(v => v.hash === h); return 30 + Math.max(0, i) * gap; };
    const dots = vs.map((v, i) => `<circle cx="${30 + i * gap}" cy="${y0}" r="6" class="lt-dot"><title>${esc(fmtFull(v.ts))}</title></circle>`).join('');
    const br = L.branches.map((b, j) => { const x = xOf(b.from), y = y0 + 36 + j * 26;
      return `<path d="M${x},${y0} C${x},${y} ${x},${y} ${x + 24},${y}" class="lt-br"/><text x="${x + 30}" y="${y + 4}" class="lt-tx">${esc(b.name)} · ${esc(fmtTime(b.ts))}</text>`; }).join('');
    const h = y0 + 30 + L.branches.length * 26;
    sc.innerHTML = `<div class="hint">${t('lt.lead', { n: vs.length, m: L.branches.length })}</div>
      <svg class="lt" viewBox="0 0 ${W} ${h}" width="100%" height="${h}"><line x1="30" y1="${y0}" x2="${30 + Math.max(0, vs.length - 1) * gap}" y2="${y0}" class="lt-main"/>${br}${dots}</svg>`;
  };
  if ($('#scrubBtn', body)) $('#scrubBtn', body).onclick = () => {  // time slider (2.6.0 #11)
    const sc = $('#scrub', body); sc.hidden = !sc.hidden; if (sc.hidden) return;
    sc.innerHTML = `<div class="scrub-bar"><input type="range" id="scrubRange" min="0" max="${kept.length - 1}" value="${kept.length - 1}"><span class="meta" id="scrubLabel"></span></div><div id="scrubView" class="scrub-view"></div>`;
    $('#scrubRange').oninput = ev => scrubTo(e, kept, +ev.target.value);
    scrubTo(e, kept, kept.length - 1);
  };
  $('#cmpBtn').onclick = () => {
    const [a, b] = picked().map(x => ({ v: x.dataset.v, ts: +x.dataset.ts, label: x.dataset.label }));
    showCompare(e, body, a, b);
  };
}

/* Diff two chosen versions of a file (older on the left of the arrow). */
async function showCompare(e, body, a, b) {
  if (a.ts > b.ts) [a, b] = [b, a];
  body.innerHTML = loadingHTML();
  const req = ++S.req;
  const fetchCmp = full => get('/api/compare', { a: a.v, b: b.v, ext: e.ext, path: e.path, context: full ? 100000 : 3 });
  const d = await fetchCmp(false);
  if (req !== S.req) return;
  const head = `<div class="subbar"><button class="btn sm" data-goto="history">‹ ${t('cmp.back')}</button>
    <span class="meta cmp-title">${esc(a.label)} <b>→</b> ${esc(b.label)}</span></div>`;
  if (!d.ok) { body.innerHTML = head + noteHTML(t('cmp.unavailable'), true); return; }
  if (!d.hunks.length) { body.innerHTML = head + noteHTML(t('cmp.same')); return; }
  drawDiff(body, d, { e, top: head, full: false, refetch: fetchCmp,
    headText: t('diff.headMod', { a: num(d.a_len), b: num(d.b_len), unit: unitWord(UNIT[d.type] || 'line', d.b_len) }),
    sheetHash: b.v !== 'current' ? b.v : null });
}

async function renderDetails(e, body, live) {
  let rows, meta = [];
  if (e.kind === 'file') {
    const r = await get('/api/current', { path: e.path });
    if (!live()) return;
    meta = r.ok ? Object.entries(r.content.meta || {}) : [];
    rows = [
      [t('p.path'), e.path],
      [t('p.type'), `${t('cat.' + e.cat)} · ${e.ext || t('p.noExt')}`],
      [t('p.size'), fmtSize(e.size)],
      [t('p.modified'), fmtFull(e.mtime)],
      [t('p.indexed'), t(e.indexed ? 'fd.indexedYes' : 'fd.indexedNo')],
      [t('tab.history'), e.changes ? t('files.changes', { n: e.changes }) : t('fd.noChanges')],
    ];
  } else {
    const h = e.kind === 'deleted' ? e.prev_hash : e.hash || e.prev_hash;
    const r = h ? await get('/api/content', { hash: h, ext: e.ext }) : null;
    if (!live()) return;
    meta = r && r.ok ? Object.entries(r.content.meta || {}) : [];
    const snap = (hash, full) => hash ? `${t(full ? 'snap.full' : 'snap.text')} · ${hash.slice(0, 12)}` : t('snap.none');
    rows = [
      [t('p.event'), t('kind.' + e.kind) + ((e.flags || []).includes('offline') ? t('p.startup') : '')],
      [t('p.recorded'), fmtFull(e.ts)],
      [t('p.path'), e.path],
      e.old_path ? [t('p.prevPath'), e.old_path] : null,
      [t('p.type'), `${t('cat.' + e.cat)} · ${e.ext || t('p.noExt')}`],
      e.old_size != null ? [t('p.sizeBefore'), fmtSize(e.old_size)] : null,
      e.kind !== 'deleted' ? [t('p.sizeAfter'), fmtSize(e.size)] : null,
      e.mtime ? [t('p.timestamp'), fmtFull(e.mtime / 1e9)] : null,
      e.kind !== 'deleted' ? [t('p.thisVer'), snap(e.hash, e.has_blob)] : null,
      e.kind !== 'created' ? [t('p.prevVer'), snap(e.prev_hash, e.has_prev_blob)] : null,
      [t('p.onDisk'), t(e.exists ? 'p.yes' : 'p.no')],
    ].filter(Boolean);
  }
  body.innerHTML = `<div class="props-h">${t(e.kind === 'file' ? 'tab.details' : 'p.change')}</div>
    <table class="props">${rows.map(([k, v]) => `<tr><th>${k}</th><td>${esc(v)}</td></tr>`).join('')}</table>
    ${meta.length ? `<div class="props-h">${t('p.docProps')}</div><table class="props">${meta.map(([k, v]) => `<tr><th>${esc(t('meta.' + k))}</th><td>${esc(v)}</td></tr>`).join('')}</table>` : ''}`;
}

/* ------------------------------------------------------------------ diff */
async function renderDiffTab(e, body, live) {
  const d = await get('/api/diff', { id: e.id });
  if (!live()) return;
  if (d.type === 'image' && (e.has_blob || e.has_prev_blob)) {
    const both = e.has_blob && e.has_prev_blob;
    const draw = mode => {
      const side = (label, ok, hash) => `<figure><figcaption>${label}</figcaption><div class="img-view">${ok ? `<img src="${blobUrl(hash, e.name)}" alt="">` : `<span class="meta">${t('diff.notCaptured')}</span>`}</div></figure>`;
      const seg = both ? `<div class="subbar"><span class="seg">${['side', 'swipe'].map(m => `<button data-imode="${m}" class="${m === mode ? 'on' : ''}">${t('diff.' + m)}</button>`).join('')}</span></div>` : '';
      body.innerHTML = seg + (mode === 'swipe'
        ? `<div class="swipe"><img src="${blobUrl(e.prev_hash, e.name)}" alt=""><img class="after" src="${blobUrl(e.hash, e.name)}" alt="" style="clip-path: inset(0 0 0 50%)">
             <span class="swipe-line" style="left:50%"></span><span class="swipe-tag l">${t('diff.before')}</span><span class="swipe-tag r">${t('diff.after')}</span></div>
           <input type="range" class="swipe-range" min="0" max="100" value="50" aria-label="${esc(t('diff.swipe'))}">`
        : `<div class="img-compare">${side(t('diff.before'), e.has_prev_blob, e.prev_hash)}${side(t('diff.after'), e.has_blob, e.hash)}</div>`);
      const range = $('.swipe-range', body);
      if (range) range.oninput = () => {  // drag to reveal the new version over the old one
        $('.swipe .after', body).style.clipPath = `inset(0 0 0 ${range.value}%)`;
        $('.swipe-line', body).style.left = range.value + '%';
      };
      body.onclick = ev => { const b = ev.target.closest('[data-imode]'); if (b) { store('dw-imode', b.dataset.imode); draw(b.dataset.imode); } };
    };
    draw(both && store('dw-imode') === 'swipe' ? 'swipe' : 'side');
    return;
  }
  if (d.note === 'missing') {
    body.innerHTML = noteHTML(`${t('diff.missing')}<br><button class="btn sm" data-goto="this">${t('diff.viewThis')}</button>`, true);
    return;
  }
  if (!d.hunks || !d.hunks.length) {
    const msg = (e.flags || []).includes('same') ? t('diff.same')
      : ['image', 'binary', 'archive'].includes(d.type) ? t('diff.binary', { a: fmtSize(e.old_size), b: fmtSize(e.size) })
        : t('diff.noText');
    body.innerHTML = noteHTML(msg) + (e.kind !== 'deleted' ? `<button class="btn sm" data-goto="this">${t('diff.viewThis')}</button>` : '');
    return;
  }
  const unit = UNIT[d.type] || 'line';
  const headText = e.kind === 'created' ? t('sum.newN', { n: num(d.b_len), unit: unitWord(unit, d.b_len) })
    : e.kind === 'deleted' ? t('diff.headDel', { n: num(d.a_len), unit: unitWord(unit, d.a_len) })
      : t('diff.headMod', { a: num(d.a_len), b: num(d.b_len), unit: unitWord(unit, d.b_len) });
  drawDiff(body, d, { e, full: false, headText, refetch: full => get('/api/diff', { id: e.id, context: full ? 100000 : 3 }),
    sheetHash: e.kind === 'modified' && e.hash ? e.hash : null });
}

/* Shared diff viewer: one column or side by side; for Excel also the sheet with changed cells marked. */
async function drawDiff(body, d, ctx) {
  const views = ['unified', 'side'].concat(d.type === 'xlsx' && ctx.sheetHash ? ['sheet'] : [],
    ['docx', 'pptx', 'markdown'].includes(d.type) && ctx.refetch ? ['doc'] : []);
  const view = views.includes(S.diffView) ? S.diffView : 'unified';
  const wrap = store('dw-wrap') !== '0';
  const tot = d.added + d.removed, blocks = 5;
  const na = tot ? Math.round(blocks * d.added / tot) : 0, nd = tot ? Math.min(blocks - na, Math.round(blocks * d.removed / tot)) : 0;
  const bar = '<span class="diffbar">' + Array.from({ length: blocks }, (_, i) => `<i class="${i < na ? 'a' : i < na + nd ? 'd' : ''}"></i>`).join('') + '</span>';
  const toolbar = `<div class="diff-stats"><span class="big"><span class="plus">+${num(d.added)}</span><span class="minus">−${num(d.removed)}</span></span>${bar}
      <span class="meta" style="color:var(--muted);font-size:12.5px">${esc(ctx.headText || '')}</span><span class="spacer" style="flex:1"></span>
      <span class="seg">${views.map(v => `<button data-view="${v}" class="${v === view ? 'on' : ''}">${t('diff.' + v)}</button>`).join('')}</span>
      ${ctx.refetch && view !== 'sheet' ? `<button class="btn sm toggle${ctx.full ? ' on' : ''}" data-full aria-pressed="${!!ctx.full}">${t('diff.full')}</button>` : ''}
      ${view !== 'sheet' ? `<span class="seg"><button data-wrap="1" class="${wrap ? 'on' : ''}">${t('diff.wrap')}</button><button data-wrap="0" class="${wrap ? '' : 'on'}">${t('diff.nowrap')}</button></span>` : ''}</div>`;
  body.onclick = async ev => {
    const v = ev.target.closest('[data-view]');
    if (v) { S.diffView = v.dataset.view; store('dw-diffview', S.diffView); return drawDiff(body, d, ctx); }
    if (ev.target.closest('[data-full]')) {
      const nd = await ctx.refetch(!ctx.full);
      ctx.full = !ctx.full;
      return drawDiff(body, nd, ctx);
    }
    const w = ev.target.closest('[data-wrap]');
    if (w) {
      store('dw-wrap', w.dataset.wrap);
      $$('[data-wrap]', body).forEach(x => x.classList.toggle('on', x === w));
      $('#diffBox', body)?.classList.toggle('nowrap', w.dataset.wrap === '0');
    }
  };
  if (view === 'doc') {  // the whole document, with insertions and deletions marked like tracked changes
    if (!ctx.full) {
      const req = S.req;
      const nd = await ctx.refetch(true);
      if (req !== S.req) return;
      ctx.full = true;
      return drawDiff(body, nd, ctx);
    }
    body.className = 'tab-body';
    body.innerHTML = (ctx.top || '') + toolbar + `<div class="subbar"><span class="meta">${t('diff.docHint')}</span></div>`
      + `<div class="paper redline">${redlineHTML(d)}</div>`;
    scrollToEl($('.rl-ins, .rl-del', body), body);
    return;
  }
  if (view === 'sheet') {
    const req = S.req;
    body.innerHTML = (ctx.top || '') + toolbar + loadingHTML();
    const r = await get('/api/content', { hash: ctx.sheetHash, ext: ctx.e.ext });
    if (req !== S.req) return;
    if (!r.ok) { body.innerHTML = (ctx.top || '') + toolbar + noteHTML(t('v.blobGone'), true); return; }
    renderSheets(body, r.content, (ctx.top || '') + toolbar + `<div class="subbar"><span class="meta">${t('diff.sheetHint')}</span></div>`, sheetMarks(d));
    return;
  }
  body.className = 'tab-body';
  body.innerHTML = (ctx.top || '') + toolbar + (d.truncated ? noteHTML(t('diff.truncated'), true) : '')
    + (view === 'side' ? `<div class="sdiff${wrap ? '' : ' nowrap'}" id="diffBox">${sideHTML(d)}</div>`
      : `<div class="diff${wrap ? '' : ' nowrap'}" id="diffBox">${diffHTML(d)}</div>`);
}

// A whole-document diff laid out as a page: unchanged text plain, insertions green, deletions struck through.
function redlineHTML(d) {
  const block = (r, cls) => {
    let text = localizeMarkers(r.t);
    const tx = r.s ? r.s.map(([c, x]) => c ? `<mark>${esc(x)}</mark>` : esc(x)).join('') : null;
    const h = /^(#{1,6}) /.exec(text);
    if (h) { text = text.slice(h[0].length); return `<h${h[1].length + 1} class="${cls}">${tx ?? esc(text)}</h${h[1].length + 1}>`; }
    if (/^\[[^\]]+\]/.test(text) && d.type === 'pptx' && !text.startsWith('  ')) return `<h4 class="${cls} rl-slide">${tx ?? esc(text)}</h4>`;
    if (text.startsWith('| ')) return `<p class="${cls} rl-row">${tx ?? esc(text)}</p>`;
    return `<p class="${cls}${/^\s*• /.test(text) ? ' li' : ''}">${tx ?? esc(text.replace(/^\s*• /, ''))}</p>`;
  };
  return d.hunks.map(h => h.rows.map(r => block(r, r.k === '+' ? 'rl-ins' : r.k === '-' ? 'rl-del' : '')).join('')).join('<hr class="rl-gap">');
}

// Excel diff lines look like "Sheet1!B3: value"; turn them into per-sheet cell marks.
function sheetMarks(d) {
  const plus = new Set(), minus = new Set(), re = /^(.*)!([A-Z]+\d+):/;
  for (const h of d.hunks) {
    for (const r of h.rows) {
      const m = r.k !== ' ' && re.exec(r.t);
      if (m) (r.k === '+' ? plus : minus).add(m[1] + '\u0000' + m[2]);
    }
  }
  const marks = {};
  const put = (key, cls) => { const [sheet, ref] = key.split('\u0000'); (marks[sheet] = marks[sheet] || {})[ref] = cls; };
  plus.forEach(k => put(k, minus.has(k) ? 'chg' : 'add'));
  minus.forEach(k => { if (!plus.has(k)) put(k, 'del'); });
  return marks;
}

// Side by side: removed lines on the left, added on the right, unchanged lines on both.
function sideHTML(d) {
  const unit = UNIT[d.type] || 'line';
  const cell = (r, side) => {
    if (!r) return '<span class="ln"></span><span class="tx empty"></span>';
    const cls = r.k === ' ' ? '' : r.k === '-' ? 'del' : 'add';
    const tx = r.s ? r.s.map(([c, x]) => c ? `<mark>${esc(x)}</mark>` : esc(x)).join('') : decorate(r.t, d.type);
    return `<span class="ln ${cls}">${r[side] ?? ''}</span><span class="tx ${cls}">${tx || ' '}</span>`;
  };
  return d.hunks.map(h => {
    const pairs = [];
    for (let i = 0; i < h.rows.length;) {
      if (h.rows[i].k === ' ') { pairs.push([h.rows[i], h.rows[i]]); i++; continue; }
      const dels = [], adds = [];
      while (i < h.rows.length && h.rows[i].k === '-') dels.push(h.rows[i++]);
      while (i < h.rows.length && h.rows[i].k === '+') adds.push(h.rows[i++]);
      for (let j = 0; j < Math.max(dels.length, adds.length); j++) pairs.push([dels[j], adds[j]]);
    }
    return `<div class="hunk-h"><span>${t('diff.hunk', { U: unitCap(unit), a: h.a, b: h.b })}</span><span>${t('diff.changedN', { n: h.rows.filter(r => r.k !== ' ').length })}</span></div>`
      + pairs.map(([l, r]) => `<div class="srow">${cell(l, 'a')}${cell(r, 'b')}</div>`).join('');
  }).join('');
}

// Extracted lines carry English markers ("[Slide 3]", "──── Page 2 ────"); show them in the UI language.
function localizeMarkers(s, anywhere = false) {
  if (anywhere) {
    return s.replace(/\[Slide (\d+)\]/g, (_, n) => t('mark.slide', { n }))
      .replace(/\[Notes\]/g, t('mark.notes'))
      .replace(/──── Page (\d+) ────/g, (_, n) => t('mark.page', { n }));
  }
  return s.replace(/^\[Slide (\d+)\]/, (_, n) => t('mark.slide', { n }))
    .replace(/^\[Notes\]/, t('mark.notes'))
    .replace(/^──── Page (\d+) ────$/, (_, n) => t('mark.page', { n }));
}
function decorate(raw, type) {
  const s = esc(localizeMarkers(raw));
  if (type === 'xlsx') return s.replace(/^([^!]{1,80}![A-Z]+\d+):/, '<span class="ref">$1</span>:');
  if (type === 'pptx' || type === 'pdf') return s.replace(/^(\[[^\]]+\]|──── .* ────$)/, '<span class="slide">$1</span>');
  if (type === 'docx') return s.replace(/^(#{1,6} )/, '<span class="ref">$1</span>');
  return s;
}

function diffHTML(d) {
  const unit = UNIT[d.type] || 'line';
  return d.hunks.map(h => {
    const rows = h.rows.map(r => {
      const cls = r.k === '+' ? 'add' : r.k === '-' ? 'del' : '';
      const tx = r.s ? r.s.map(([c, x]) => c ? `<mark>${esc(x)}</mark>` : esc(x)).join('') : decorate(r.t, d.type);
      return `<div class="drow ${cls}"><span class="ln">${r.a ?? ''}</span><span class="ln">${r.b ?? ''}</span><span class="sg">${r.k === '+' ? '+' : r.k === '-' ? '−' : ''}</span><span class="tx">${tx || ' '}</span></div>`;
    }).join('');
    return `<div class="hunk-h"><span>${t('diff.hunk', { U: unitCap(unit), a: h.a, b: h.b })}</span><span>${t('diff.changedN', { n: h.rows.filter(r => r.k !== ' ').length })}</span></div>${rows}`;
  }).join('');
}

/* ------------------------------------------------------------------ content renderers */
function renderContent(body, c, raw, pre = '', media = null, opts = {}) {
  const legacy = c.legacy ? noteHTML(t('c.legacy', { fmt: esc(c.meta?.Format || 'Office') })) : '';
  switch (c.type) {
    case 'docx':
      body.innerHTML = pre + legacy + `<div class="paper">${docxHTML(c.blocks, media)}</div>`;
      return;
    case 'pptx': body.innerHTML = pre + slidesHTML(c, media); return;
    case 'xlsx': return renderSheets(body, c, pre);
    case 'pdf': return renderPdf(body, c, raw, pre, opts.preferText);
    case 'markdown': return renderMarkdown(body, c, pre);
    case 'text': case 'code':
      body.innerHTML = pre + legacy + codeHTML(c.text || '', c.type === 'text');
      return;
    case 'image':
      body.innerHTML = pre + (raw ? `<div class="img-view"><img src="${raw}" alt=""></div>` : noteHTML(t('c.imgNotCaptured'), true)) +
        (c.meta?.Dimensions ? `<div class="subbar" style="margin-top:10px"><span class="meta">${esc(c.meta.Dimensions)} · ${esc(c.meta.Format || '')}</span></div>` : '');
      return;
    case 'archive':
      body.innerHTML = pre + `<div class="subbar"><span class="meta">${t('c.entries', { n: num(c.meta.Entries) })}</span></div><table class="entries">${c.entries.map(([n, s]) => `<tr><td>${esc(n)}</td><td>${fmtSize(s)}</td></tr>`).join('')}</table>`;
      return;
    case 'error':
      body.innerHTML = pre + noteHTML(`${t('c.error')} <span class="mono">${esc(c.error)}</span>`, true);
      return;
    default:
      body.innerHTML = pre + `<div class="binary">${ficon('other', '', true)}<div>${t('c.noPreview')}</div><div style="font-size:12.5px;margin-top:4px">${t('c.useOpen')}</div></div>`;
  }
}

function imgHTML(part, media, cls) {
  if (typeof part === 'string' && media && WEB_IMG.test(part))
    return `<img class="${cls}" src="${media(part)}" alt="${esc(t('c.imgAlt'))}" loading="lazy" onerror="this.outerHTML='<span class=&quot;img&quot;>🖼 ${esc(t('c.image'))}</span>'">`;
  return `<span class="img">🖼 ${t('c.image')}</span>`;
}

function runsHTML(runs, media) {
  return runs.map(r => {
    if (r.img) return imgHTML(r.img, media, 'doc-img');
    let s = esc(r.t);
    if (r.b) s = `<b>${s}</b>`;
    if (r.i) s = `<i>${s}</i>`;
    if (r.u) s = `<u>${s}</u>`;
    return s;
  }).join('');
}
function docxHTML(blocks, media) {
  if (!blocks.length) return `<p style="color:#9aa2b3">${t('c.docEmpty')}</p>`;
  return blocks.map(b => {
    if (b.t === 'table') return `<table>${b.rows.map(r => `<tr>${r.map(c => `<td>${esc(c)}</td>`).join('')}</tr>`).join('')}</table>`;
    const al = b.align === 'center' ? 'ctr' : b.align === 'right' ? 'rgt' : '';
    if (b.t === 'h') return `<h${b.lv} class="${al}">${runsHTML(b.runs, media)}</h${b.lv}>`;
    return `<p class="${b.list ? 'li' : ''} ${al}">${runsHTML(b.runs, media)}</p>`;
  }).join('');
}

function slidesHTML(c, media) {
  if (!c.slides.length) return noteHTML(t('c.noSlides'));
  return `<div class="slides">${c.slides.map(s => {
    const imgs = media && s.imgs && s.imgs.length ? `<div class="s-imgs">${s.imgs.slice(0, 4).map(p => imgHTML(p, media, '')).join('')}</div>` : '';
    return `<div class="slide"><div class="face${!s.paras.length && !s.title ? ' pic-only' : ''}">
      ${s.title ? `<div class="s-title">${esc(s.title)}</div>` : ''}
      ${s.paras.slice(0, 14).map(p => `<div class="s-p" style="margin-left:${p.lv * 14}px">${esc(p.t)}</div>`).join('')}
      ${s.tables.map(tb => `<table>${tb.slice(0, 8).map(r => `<tr>${r.map(x => `<td>${esc(x)}</td>`).join('')}</tr>`).join('')}</table>`).join('')}
      ${!s.paras.length && !s.title ? imgs : ''}
      ${s.paras.length > 6 ? '<div class="fade"></div>' : ''}
    </div>
    ${s.paras.length || s.title ? imgs : ''}
    <div class="foot"><span class="num">${s.n}</span><span>${t('c.textBlocks', { n: s.paras.length })}${s.pics ? ` · ${t('c.images', { n: s.pics })}` : ''}</span></div>
    ${s.notes ? `<details><summary>${t('c.notes')}</summary><div style="white-space:pre-wrap;margin-top:4px">${esc(s.notes)}</div></details>` : ''}
    </div>`;
  }).join('')}</div>`;
}

// ``marks`` (optional): {sheetName: {'B3': 'add' | 'chg' | 'del'}} — cells to colour as changed.
function renderSheets(body, c, pre, marks = null) {
  if (!c.sheets.length) { body.innerHTML = pre + noteHTML(t('c.noSheets')); return; }
  body.className = 'tab-body flush';
  const changed = s => (marks && marks[s.name]) || {};
  let cur = marks ? Math.max(0, c.sheets.findIndex(s => Object.keys(changed(s)).length)) : 0;
  const draw = () => {
    const s = c.sheets[cur], mk = changed(s);
    let grid;
    if (!s.rows.length) grid = `<div style="padding:20px">${noteHTML(t('c.sheetEmpty'))}</div>`;
    else {
      const ncol = Math.max(...s.rows.map(r => r.length));
      const head = `<tr><th></th>${Array.from({ length: ncol }, (_, i) => `<th>${colName(s.c0 + i)}</th>`).join('')}</tr>`;
      const rows = s.rows.map((r, ri) => `<tr><th>${s.r0 + ri}</th>${Array.from({ length: ncol }, (_, ci) => {
        const v = r[ci] ?? '', fx = s.formulas && s.formulas[`${ri},${ci}`];
        const isNum = v !== '' && !isNaN(+v), m = mk[colName(s.c0 + ci) + (s.r0 + ri)];
        return `<td class="${isNum ? 'num' : ''}${fx ? ' fx' : ''}${m ? ' m-' + m : ''}" data-r="${ri}" data-c="${ci}" title="${esc(v)}">${esc(v)}</td>`;
      }).join('')}</tr>`).join('');
      grid = `<table class="grid"><thead>${head}</thead><tbody>${rows}</tbody></table>`;
    }
    body.innerHTML = (pre ? `<div style="padding:12px 16px 0">${pre}</div>` : '') +
      `<div class="fbar"><span class="addr" id="fAddr">—</span><span class="val" id="fVal">${t('c.clickCell')}</span><span class="meta" style="color:var(--muted);font-family:var(--sans)">${s.cells != null ? t('c.cells', { n: num(s.cells) }) : ''}</span></div>
      <div class="grid-wrap">${grid}</div>
      <div class="sheet-tabs">${c.sheets.map((x, i) => {
        const n = Object.keys(changed(x)).length;
        return `<button class="${i === cur ? 'on' : ''}" data-sheet="${i}">${esc(x.name)}${n ? ` <span class="tabn">${n}</span>` : ''}</button>`;
      }).join('')}</div>`;
    $$('.sheet-tabs button', body).forEach(b => b.onclick = () => { cur = +b.dataset.sheet; draw(); });
    scrollToEl($('td[class*="m-"]', body), body);
    const table = $('table.grid', body);
    if (table) table.onclick = ev => {
      const td = ev.target.closest('td'); if (!td) return;
      $$('td.on', table).forEach(x => x.classList.remove('on'));
      td.classList.add('on');
      const ri = +td.dataset.r, ci = +td.dataset.c, fx = s.formulas && s.formulas[`${ri},${ci}`];
      $('#fAddr').textContent = colName(s.c0 + ci) + (s.r0 + ri);
      $('#fVal').textContent = fx ? `=${fx}   →   ${s.rows[ri][ci] ?? ''}` : (s.rows[ri][ci] ?? '');
    };
  };
  draw();
}

function renderPdf(body, c, raw, pre, preferText = false) {
  let mode = raw && !preferText ? 'doc' : 'text';
  const draw = () => {
    const bar = `<div class="subbar" style="${mode === 'doc' ? 'padding:12px 16px 0;margin-bottom:10px' : ''}">
      ${raw ? `<span class="seg"><button data-m="doc" class="${mode === 'doc' ? 'on' : ''}">${t('c.pdfDoc')}</button><button data-m="text" class="${mode === 'text' ? 'on' : ''}">${t('c.pdfText')}</button></span>` : ''}
      <span class="spacer"></span><span class="meta">${t('c.pages', { n: num(c.meta?.Pages ?? c.pages.length) })}</span></div>`;
    if (mode === 'doc') {
      body.className = 'tab-body flush';
      body.innerHTML = (pre ? `<div style="padding:12px 16px 0">${pre}</div>` : '') + bar + `<iframe class="pdf-frame" src="${raw}#view=FitH" title="PDF"></iframe>`;
    } else {
      body.className = 'tab-body';
      body.innerHTML = pre + bar + (c.pages.length ? c.pages.map((p, i) => `<div class="page"><span class="pn">${t('c.page', { n: i + 1 })}</span>${esc(p.trim()) || `<i style="color:#9aa2b3">${t('c.noPageText')}</i>`}</div>`).join('') : noteHTML(t('c.noPdfText')));
    }
    $$('.seg button', body).forEach(b => b.onclick = () => { mode = b.dataset.m; draw(); });
  };
  draw();
}

function renderMarkdown(body, c, pre) {
  let mode = 'rendered';
  const draw = () => {
    body.innerHTML = pre + `<div class="subbar"><span class="seg"><button data-m="rendered" class="${mode === 'rendered' ? 'on' : ''}">${t('c.rendered')}</button><button data-m="source" class="${mode === 'source' ? 'on' : ''}">${t('c.source')}</button></span><span class="spacer"></span><span class="meta">${t('c.lines', { n: num(c.meta?.Lines) })}</span></div>` +
      (mode === 'rendered' ? `<div class="md">${markdown(c.text || '')}</div>` : codeHTML(c.text || '', true));
    $$('.seg button', body).forEach(b => b.onclick = () => { mode = b.dataset.m; draw(); });
  };
  draw();
}

function codeHTML(text, wrap) {
  const MAX = 5000;
  if (!text.trim()) return noteHTML(t('c.empty'));
  let lines = text.replace(/\r\n?/g, '\n').split('\n');
  const total = lines.length, cut = total > MAX;
  if (cut) lines = lines.slice(0, MAX);
  const tail = cut ? noteHTML(t('c.firstN', { a: num(MAX), b: num(total) })) : '';
  // One row per line keeps the gutter aligned even when long lines wrap.
  if (wrap) {
    return `<div class="diff">${lines.map((l, i) => `<div class="drow" style="grid-template-columns:52px minmax(0,1fr)"><span class="ln">${i + 1}</span><span class="tx">${esc(l) || ' '}</span></div>`).join('')}</div>` + tail;
  }
  return `<div class="code-view"><pre class="g">${lines.map((_, i) => i + 1).join('\n')}</pre><pre class="c">${esc(lines.join('\n'))}</pre></div>` + tail;
}

/* Small, safe Markdown renderer (all text is escaped before formatting). */
function markdown(src) {
  const lines = src.replace(/\r\n?/g, '\n').split('\n');
  const out = [];
  const inline = s => {
    const codes = [];
    s = s.replace(/`([^`]+)`/g, (_, c) => { codes.push(c); return `\u0000${codes.length - 1}\u0000`; });
    s = esc(s)
      .replace(/!\[([^\]]*)\]\(([^)\s]+)[^)]*\)/g, (_, a) => `<span class="tag">🖼 ${a || t('c.image')}</span>`)
      .replace(/\[([^\]]+)\]\(([^)\s]+)[^)]*\)/g, (_, x, u) => /^(https?:|mailto:)/i.test(u) ? `<a href="${u}" target="_blank" rel="noopener noreferrer">${x}</a>` : `<u>${x}</u>`)
      .replace(/\*\*([^*]+)\*\*|__([^_]+)__/g, (_, a, b) => `<strong>${a || b}</strong>`)
      .replace(/(^|[^*\w])\*([^*\s][^*]*?)\*(?!\*)/g, '$1<em>$2</em>')
      .replace(/~~([^~]+)~~/g, '<del>$1</del>');
    return s.replace(/\u0000(\d+)\u0000/g, (_, i) => `<code>${esc(codes[+i])}</code>`);
  };
  const isBlockStart = l => /^\s*(```|~~~|#{1,6}\s|>|([-*+]|\d+[.)])\s|\|)/.test(l) || /^\s*([-*_])(\s*\1){2,}\s*$/.test(l);
  let i = 0;
  while (i < lines.length) {
    const l = lines[i];
    let m;
    if (!l.trim()) { i++; continue; }
    if ((m = /^\s*(```|~~~)\s*([\w+-]*)/.exec(l))) {
      const fence = m[1], buf = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith(fence)) buf.push(lines[i++]);
      i++;
      out.push(`<pre><code>${esc(buf.join('\n'))}</code></pre>`);
      continue;
    }
    if ((m = /^(#{1,6})\s+(.*?)\s*#*\s*$/.exec(l))) { out.push(`<h${m[1].length}>${inline(m[2])}</h${m[1].length}>`); i++; continue; }
    if (/^\s*([-*_])(\s*\1){2,}\s*$/.test(l)) { out.push('<hr>'); i++; continue; }
    if (/^\s*>/.test(l)) {
      const buf = [];
      while (i < lines.length && /^\s*>/.test(lines[i])) buf.push(lines[i++].replace(/^\s*>\s?/, ''));
      out.push(`<blockquote>${markdown(buf.join('\n'))}</blockquote>`);
      continue;
    }
    if (l.includes('|') && i + 1 < lines.length && /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/.test(lines[i + 1])) {
      const cells = r => r.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(x => x.trim());
      const head = cells(l);
      i += 2;
      const rows = [];
      while (i < lines.length && lines[i].includes('|') && lines[i].trim()) rows.push(cells(lines[i++]));
      out.push(`<table><thead><tr>${head.map(h => `<th>${inline(h)}</th>`).join('')}</tr></thead><tbody>${rows.map(r => `<tr>${r.map(c => `<td>${inline(c)}</td>`).join('')}</tr>`).join('')}</tbody></table>`);
      continue;
    }
    if (/^\s*([-*+]|\d+[.)])\s+/.test(l)) {
      const stack = [];
      let html = '';
      while (i < lines.length && (m = /^(\s*)([-*+]|\d+[.)])\s+(.*)$/.exec(lines[i]))) {
        const depth = Math.floor(m[1].replace(/\t/g, '    ').length / 2);
        const tag = /\d/.test(m[2]) ? 'ol' : 'ul';
        while (stack.length > depth + 1 || (stack.length === depth + 1 && stack[stack.length - 1] !== tag)) html += `</${stack.pop()}>`;
        while (stack.length < depth + 1) { stack.push(tag); html += `<${tag}>`; }
        const task = /^\[([ xX])\]\s+(.*)$/.exec(m[3]);
        html += `<li>${task ? `<input type="checkbox" disabled ${task[1] !== ' ' ? 'checked' : ''}>${inline(task[2])}` : inline(m[3])}</li>`;
        i++;
      }
      while (stack.length) html += `</${stack.pop()}>`;
      out.push(html);
      continue;
    }
    const buf = [l];
    i++;
    while (i < lines.length && lines[i].trim() && !isBlockStart(lines[i])) buf.push(lines[i++]);
    out.push(`<p>${buf.map(inline).join('<br>')}</p>`);
  }
  return out.join('\n');
}

/* ------------------------------------------------------------------ toasts / modal */
function toast(e) {
  const box = $('#toasts');
  const active = $$('.toast:not(.out):not(.plain)', box);
  if (active.length >= 4) {
    let agg = $('.toast.plain.agg', box);
    if (!agg) {
      agg = document.createElement('div');
      agg.className = 'toast plain agg';
      agg.dataset.n = '0';
      box.appendChild(agg);
    }
    agg.dataset.n = +agg.dataset.n + 1;
    agg.innerHTML = `<div class="t-body"><div class="t-name">${t('toast.more', { n: +agg.dataset.n })}</div><div class="t-sub">${t('toast.seeAll')}</div></div>`;
    clearTimeout(agg._t);
    agg._t = setTimeout(() => dismiss(agg), 5000);
    return;
  }
  const el = document.createElement('div');
  el.className = `toast k-${e.kind}`;
  const undo = e.kind === 'deleted' && e.has_prev_blob;  // a deleted file can be brought back right here
  el.innerHTML = `${ficon(e.cat, e.ext)}<div class="t-body"><div class="t-name">${esc(e.name)}</div><div class="t-sub">${t('kind.' + e.kind)} · ${esc(crumb(e))}</div></div>`
    + (undo ? `<button class="btn sm" data-undo>${svg('restore')}${t('toast.restore')}</button>` : kbadge(e.kind)) + '<span class="bar"></span>';
  el.onclick = async ev => {
    if (ev.target.closest('[data-undo]')) {
      dismiss(el);
      const r = await post('/api/restore', { id: e.id, version: 'prev', lang: LANG });
      notify(r.ok ? t('restore.done', { path: `<span class="mono" style="font-size:12px">${esc(r.path)}</span>` }) : esc(errText(r)), !r.ok);
      return;
    }
    if (S.mode !== 'changes') setMode('changes');
    select(e.id);
    dismiss(el);
  };
  box.prepend(el);
  setTimeout(() => dismiss(el), undo ? 9000 : 5000);
}
function notify(html, warn = false) {
  const el = document.createElement('div');
  el.className = 'toast plain';
  el.innerHTML = `<div class="note${warn ? ' warn' : ''}" style="margin:0;border:0;padding:0;background:none">${svg(warn ? 'warn' : 'check')}<div>${html}</div></div>`;
  $('#toasts').prepend(el);
  setTimeout(() => dismiss(el), 6000);
}
function dismiss(el) {
  if (!el.isConnected || el.classList.contains('out')) return;
  el.classList.add('out');
  setTimeout(() => el.remove(), 300);
}

function openModal(html, cls = '') {
  $('#modal').className = 'modal ' + cls;
  $('#modal').innerHTML = html;
  $('#modalBack').hidden = false;
}
function closeModal() { $('#modalBack').hidden = true; $('#modal').innerHTML = ''; }
function confirmBox(title, text, ok, danger = false) {
  return new Promise(res => {
    openModal(`<div class="m-head"><h3>${title}</h3></div><div class="m-body" style="color:var(--text-2)">${text}</div>
      <div class="m-foot"><button class="btn" id="cNo">${t('btn.cancel')}</button><button class="btn ${danger ? 'danger' : 'primary'}" id="cYes">${ok}</button></div>`, 'sm');
    $('#cNo').onclick = () => { closeModal(); res(false); };
    $('#cYes').onclick = () => { closeModal(); res(true); };
  });
}

async function openSettings() {
  const [s, auto, shell] = await Promise.all([get('/api/settings'), get('/api/autostart'), get('/api/shell-menu')]);
  let roots = [...s.roots], lang = LANG, exPaths = [...(s.exclude_paths || [])];
  const hhmm = ts => new Date(ts * 1000).toLocaleTimeString(loc(), { hour: '2-digit', minute: '2-digit', hour12: false });
  const muted = (s.mute_until || 0) * 1000 > Date.now();
  const list = a => esc(a.join(', '));
  openModal(`<div class="m-head"><h3>${t('set.title')}</h3><button class="icon-btn" data-close>${svg('x')}</button></div>
    <div class="m-body">
      <div class="field"><label>${t('set.lang')}</label>
        <span class="seg" id="langSeg">${Object.entries(LANGS).map(([code, l]) => `<button data-lang="${code}" class="${code === lang ? 'on' : ''}">${l.name}</button>`).join('')}</span></div>
      <div class="field"><label>${t('set.bg')}</label>
        <label class="switch-row"><input type="checkbox" id="autoStart" ${auto.enabled ? 'checked' : ''} ${auto.supported ? '' : 'disabled'}><span class="switch"></span>
          <span><b>${t('set.autostart')}</b><span class="hint">${t('set.autostartHint')}</span></span></label>
        <div class="quit-row"><span><b>${t('set.notify')}</b><span class="hint">${t('set.notifyHint')}</span></span>
          <span class="seg" id="notifySeg">${['off', 'deleted', 'all'].map(v => `<button data-notify="${v}" class="${(s.notify || 'off') === v ? 'on' : ''}">${t('notify.' + v)}</button>`).join('')}</span></div>
        <div class="quit-row" ${F161 ? '' : 'hidden'}><span><b>${t('set.mute')}</b><span class="hint" id="muteHint">${muted ? t('mute.until', { t: hhmm(s.mute_until) }) : t('set.muteHint')}</span></span>
          <span class="seg" id="muteSeg">${[['off', 0], ['60', 60], ['tomorrow', -1]].map(([k, m]) => `<button data-mute="${m}" class="${(k === 'off') !== muted ? 'on' : ''}">${t('mute.' + k)}</button>`).join('')}</span></div>
        <label class="switch-row" ${F161 ? '' : 'hidden'}><input type="checkbox" id="shellMenu" ${shell.enabled ? 'checked' : ''} ${shell.supported ? '' : 'disabled'}><span class="switch"></span>
          <span><b>${t('set.shell')}</b><span class="hint">${t('set.shellHint')}</span></span></label>
        <div class="quit-row"><span class="hint">${t('set.quitHint')}</span><button class="btn sm" id="quitBtn">${svg('power')}${t('set.quit')}</button></div></div>
      <div class="field"><label>${t('set.folders')}</label><div class="hint">${t('set.foldersHint')}</div>
        <div class="roots-edit" id="rootsEdit"></div>
        <div class="row"><input type="text" id="rootIn" placeholder="${esc(t('set.pastePh'))}"><button class="btn sm" id="rootAdd">${t('set.add')}</button><button class="btn sm" id="rootPick">${svg('folder')}${t('set.browse')}</button></div>
        ${(s.suggested || []).length ? `<div class="quick-add" id="quickAdd"><span class="hint">${t('set.quickAdd')}</span>${s.suggested.map(f =>
          `<button class="chip" data-add-root="${esc(f.path)}" title="${esc(f.path)}">+ ${t('folder.' + f.key)}</button>`).join('')}</div>` : ''}</div>
      <div class="field"><label>${t('set.interval')}</label><div class="hint">${t('set.intervalHint')}</div>
        <div class="range"><input type="range" id="interval" min="1" max="300" step="1" value="${s.interval}"><output id="intervalOut">${s.interval}s</output></div></div>
      <details class="diag adv"><summary>${t('set.advanced')}</summary><div class="grid3">
        <div class="field"><label>${t('set.snap')}</label><div class="hint">${t('set.snapHint')}</div><input type="number" id="snapMax" min="0" step="1" value="${s.snapshot_max_mb}"></div>
        <div class="field"><label>${t('set.baseText')}</label><div class="hint">${t('set.baseTextHint')}</div><input type="number" id="baseText" min="0" step="1" value="${s.baseline_text_max_mb}"></div>
        <div class="field"><label>${t('set.baseCopy')}</label><div class="hint">${t('set.baseCopyHint')}</div><input type="number" id="baseCopy" min="0" step="0.5" value="${s.baseline_copy_mb}"></div>
      </div></details>
      <div class="grid3">
        <div class="field"><label>${t('set.keepDays')}</label><div class="hint">${t('set.keepDaysHint')}</div><input type="number" id="keepDays" min="0" step="1" value="${s.keep_days ?? 90}"></div>
        <div class="field" style="grid-column: span 2"><label>${t('set.maxStorage')}</label><div class="hint">${t('set.maxStorageHint')}</div><div class="row"><input type="number" id="maxStorage" min="0" step="0.5" value="${s.max_storage_gb ?? 5}"><button class="btn sm" id="storageBtn">${svg('chart')}${t('st.btn')}</button></div></div>
        <div class="field" style="grid-column: span 2"><label>${t('bk.title')}</label><div class="hint">${t('bk.hint')}</div>
          <div class="row"><button class="btn sm" id="backupBtn">${svg('download')}${t('bk.btn')}</button>
            <button class="btn sm ghost" id="backupRawBtn" title="${esc(t('bk.rawWhy'))}">${t('bk.raw')}</button>
            <button class="btn sm ghost" id="exportBtn2" title="${esc(t('mv.exportWhy'))}">${t('mv.export')}</button>
            <button class="btn sm ghost" id="importBtn" title="${esc(t('mv.importWhy'))}">${t('mv.import')}</button><span class="hint" id="backupState"></span></div></div>
        <div class="field" style="grid-column: span 2"><label>${t('gd.why')}</label><div class="hint">${t('gd.whyShort')}</div>
          <div class="row"><button class="btn sm" id="guideBtn">${svg('info')}${t('gd.reopen')}</button></div></div>
        <div class="field" style="grid-column: span 2"><label class="switch-row"><input type="checkbox" id="prescan" ${s.prescan !== false ? 'checked' : ''}><span class="switch"></span>
          <span><b>${t('set.prescan')}</b><span class="hint">${t('set.prescanHint')}</span></span></label></div>
        <div class="field" style="grid-column: span 2"><label class="switch-row"><input type="checkbox" id="milestones" ${s.milestones !== false ? 'checked' : ''}><span class="switch"></span>
          <span><b>${t('set.milestones')}</b><span class="hint">${t('set.milestonesHint')}</span></span></label></div>
      </div>
      <div class="field"><label>${t('set.exExt')}</label><div class="hint">${t('set.exExtHint')}</div><textarea id="exExt">${list(s.exclude_exts)}</textarea></div>
      <div class="field"><label>${t('set.exNames')}</label><div class="hint">${t('set.exNamesHint', { lock: '<span class="mono">~$*</span>' })}</div><textarea id="exNames">${list(s.exclude_names)}</textarea></div>
      <div class="field"><label>${t('set.exDirs')}</label><textarea id="exDirs">${list(s.exclude_dirs)}</textarea></div>
      <div class="field" ${F161 ? '' : 'hidden'}><label>${t('set.exPaths')}</label><div class="hint">${t('set.exPathsHint')}</div><div class="roots-edit" id="exPathsEdit"></div></div>
      <div class="quit-row" ${F161 ? '' : 'hidden'}><span><b>${t('clean.title')}</b><span class="hint">${t('clean.hint')}</span></span>
        <button class="btn sm" id="cleanBtn">${svg('restore')}${t('clean.btn')}</button></div>
      <div class="danger-zone"><div><b>${t('set.clearTitle')}</b>${t('set.clearText', { dir: `<span class="mono">${esc(s.data_dir)}</span>` })}</div><button class="btn sm danger" id="clearBtn">${svg('trash')}${t('set.clearBtn')}</button></div>
      <div class="field"><label>${t('upd.section')}</label><div id="updInfo"></div></div>
      <details class="diag" id="diagBox" ${F161 ? '' : 'hidden'}><summary>${t('diag.title')}</summary><div id="diagBody">${loadingHTML()}</div></details>
      <div class="about-row"><span><b>${t('app.name')} ${esc(s.version || '')}</b></span><span class="spacer"></span>
        <button class="btn sm" data-open="data">${svg('folder')}${t('set.openData')}</button><button class="btn sm" data-open="log">${svg('open')}${t('set.openLog')}</button></div>
    </div>
    <div class="m-foot"><button class="btn left" id="resetBtn">${t('set.reset')}</button><button class="btn" data-close>${t('btn.cancel')}</button><button class="btn primary" id="saveBtn">${t('set.save')}</button></div>`);
  const drawRoots = () => {
    const sizes = (S.space && !S.space.folder ? S.space.roots : []) || [];  // each folder's size and file count (2.0.1)
    $('#rootsEdit').innerHTML = roots.map((r, i) => {
      const sz = sizes.find(x => x.path.toLowerCase() === r.toLowerCase());
      return `<div class="root">${svg('folder')}<span>${esc(r)}${sz ? `<em class="root-size">${fmtSize(sz.size)} · ${t('sp.inFiles', { n: num(sz.files) })}</em>` : ''}</span>
        <button class="copy" data-rm-root="${i}" title="${esc(t('set.stop'))}">${svg('x')}</button></div>`;
    }).join('');
  };
  drawRoots();
  const drawEx = () => {
    $('#exPathsEdit').innerHTML = exPaths.length ? exPaths.map((p, i) => `<div class="root">${svg('eyeoff')}<span>${esc(p)}</span><button class="copy" data-rm-ex="${i}" title="${esc(t('note.remove'))}">${svg('x')}</button></div>`).join('')
      : `<div class="hint">${t('set.exPathsNone')}</div>`;
  };
  drawEx();
  $('#exPathsEdit').onclick = ev => { const b = ev.target.closest('[data-rm-ex]'); if (b) { exPaths.splice(+b.dataset.rmEx, 1); drawEx(); } };
  $('#muteSeg').onclick = async ev => {
    const b = ev.target.closest('[data-mute]'); if (!b) return;
    const m = +b.dataset.mute;
    const r = await post('/api/mute', m < 0 ? { until: 'tomorrow' } : { minutes: m });
    if (!r.ok) { notify(esc(errText(r)), true); return; }
    $$('#muteSeg button').forEach(x => x.classList.toggle('on', x === b));
    $('#muteHint').textContent = r.mute_until * 1000 > Date.now() ? t('mute.until', { t: hhmm(r.mute_until) }) : t('set.muteHint');
  };
  $('#shellMenu').onchange = async ev => {
    const box = ev.target;
    const r = await post('/api/shell-menu', { enabled: box.checked }).catch(() => ({ ok: false }));
    if (!r.ok) { box.checked = !box.checked; notify(esc(errText(r)), true); return; }
    box.checked = r.enabled;
    notify(t(r.enabled ? 'shell.on' : 'shell.off'));
  };
  $('#diagBox').ontoggle = async () => {
    if (!$('#diagBox').open) return;
    const d = await get('/api/diagnostics').catch(() => null);
    if (!d) return;
    const dur = s => s >= 86400 ? `${(s / 86400).toFixed(1)} d` : s >= 3600 ? `${(s / 3600).toFixed(1)} h` : `${Math.round(s / 60)} min`;
    const rows = [['diag.version', d.version + ` · Python ${d.python}`], ['diag.uptime', dur(d.uptime)],
      ['diag.detect', d.instant ? t('diag.yes') : t('diag.no')], ['diag.files', num(d.files)], ['diag.scans', num(d.scans)],
      ['diag.scanMs', `${num(d.full_ms)} ms / ${d.partial_ms != null ? num(d.partial_ms) + ' ms' : '—'}`], ['diag.events', num(d.events)],
      ['diag.indexed', d.indexed == null ? '—' : num(d.indexed)], ['diag.db', fmtSize(d.db_bytes)], ['diag.snapshots', num(d.snapshots)]];
    if (d.cpu_s != null) {  // 2.1.0: what DeskTrace itself costs, and when the next full safety rescan runs
      const cpu = d.cpu_s >= 60 ? dur(d.cpu_s) : `${d.cpu_s} s`;
      rows.push(['diag.use', t('diag.useV', { cpu, mem: num(d.memory_mb), io: num(d.io_mb) })]);
      if (d.next_full_s != null) rows.push(['diag.nextFull', d.next_full_s < 60 ? `${d.next_full_s} s` : dur(d.next_full_s)]);
      rows.push(['diag.saver', t(d.on_battery ? 'diag.saverBattery' : d.busy ? 'diag.saverBusy' : 'diag.saverOff')]);
      if (d.snap_format) rows.push(['diag.snapFormat', d.snap_format]);
      rows.push(['diag.integrity', d.integrity === 'ok' ? t('diag.dbOk') : d.integrity ? t('diag.dbBad', { why: d.integrity }) : '—']);
      rows.push(['diag.warn', (d.warn || []).length ? d.warn.map(k => t('warn.' + k)).join(' · ') : t('diag.noWarn')]);
      if (d.disk_free != null) rows.push(['diag.disk', fmtSize(d.disk_free) + (d.disk_low ? ' — ' + t('diag.diskLow') : '')]);
    }
    const report = rows.map(([k, v]) => `${t(k)}: ${v}`).join('\n') + '\n' + d.errors.join('\n');
    $('#diagBody').innerHTML = `<table class="kv-table">${rows.map(([k, v]) => `<tr><td>${t(k)}</td><td>${esc(v)}</td></tr>`).join('')}</table>
      <div class="hint" style="margin-top:8px">${t('diag.errors')}</div>
      ${d.errors.length ? `<pre class="diag-log">${esc(d.errors.join('\n'))}</pre>` : `<div class="hint">${t('diag.noErrors')}</div>`}
      <button class="btn sm" id="diagCopy" style="margin-top:8px">${svg('copy')}${t('diag.copy')}</button>`;
    $('#diagCopy').onclick = () => navigator.clipboard.writeText(report).then(() => notify(t('diag.copied')));
  };
  const drawUpd = u => {
    const why = r => t('upd.rejected', { path: `<span class="mono">${esc(r.path)}</span>`, why: t('upd.why.' + r.reason) });
    $('#updInfo').innerHTML = (u && u.available
      ? `<div class="quit-row"><span>${t('upd.title', { v: esc(u.version) })}</span><button class="btn sm primary" id="updShow">${svg('download')}${t('upd.now')}</button></div>`
      : `<div class="hint">${t('upd.none')}</div>`)
      + (u ? u.rejected.map(r => noteHTML(why(r), true)).join('') : '')
      + `<div class="row" style="margin-top:6px"><button class="btn sm" id="updPick">${svg('folder')}${t('upd.check')}</button></div>`;
    const sh = $('#updShow'); if (sh) sh.onclick = showUpdate;
    $('#updPick').onclick = async () => {
      const r = await post('/api/update/check', { pick: true, lang: LANG });
      S.update = r.update; renderUpdateBadge();
      if (r.ok) return showUpdate();
      drawUpd(r.update);
      if (r.picked && r.reason) notify(esc(why({ path: r.picked, reason: r.reason })), true);
    };
  };
  get('/api/update', { lang: LANG }).then(drawUpd).catch(() => null);
  $('#langSeg').onclick = ev => {
    const b = ev.target.closest('[data-lang]'); if (!b) return;
    lang = b.dataset.lang;
    $$('#langSeg button').forEach(x => x.classList.toggle('on', x === b));
  };
  const addRoot = p => { p = (p || '').trim().replace(/^"|"$/g, ''); if (p && !roots.includes(p)) { roots.push(p); drawRoots(); } };
  $('#rootsEdit').onclick = ev => { const b = ev.target.closest('[data-rm-root]'); if (b) { roots.splice(+b.dataset.rmRoot, 1); drawRoots(); } };
  $('#rootAdd').onclick = () => { addRoot($('#rootIn').value); $('#rootIn').value = ''; };
  $('#rootIn').onkeydown = ev => { if (ev.key === 'Enter') $('#rootAdd').click(); };
  const qa = $('#quickAdd');
  if (qa) qa.onclick = ev => { const b = ev.target.closest('[data-add-root]'); if (b) { addRoot(b.dataset.addRoot); b.remove(); } };
  $$('[data-open]', $('#modal')).forEach(b => b.onclick = async () => {
    const r = await post(b.dataset.open === 'data' ? '/api/open-data' : '/api/open-log');
    if (!r.ok) notify(esc(errText(r)), true);
  });
  $('#rootPick').onclick = async () => { const r = await post('/api/pick-folder'); if (r.path) addRoot(r.path); };
  $('#interval').oninput = ev => { $('#intervalOut').textContent = ev.target.value + 's'; };
  const split = v => v.split(/[,\n]+/).map(x => x.trim()).filter(Boolean);
  $('#resetBtn').onclick = () => {
    const d = s.defaults;
    roots = [...d.roots]; drawRoots();
    $('#interval').value = d.interval; $('#intervalOut').textContent = d.interval + 's';
    $('#snapMax').value = d.snapshot_max_mb; $('#baseText').value = d.baseline_text_max_mb; $('#baseCopy').value = d.baseline_copy_mb;
    $('#keepDays').value = d.keep_days; $('#maxStorage').value = d.max_storage_gb;
    $('#exExt').value = d.exclude_exts.join(', '); $('#exNames').value = d.exclude_names.join(', '); $('#exDirs').value = d.exclude_dirs.join(', ');
    exPaths = [...(d.exclude_paths || [])]; drawEx();
  };
  $('#saveBtn').onclick = async () => {
    const r = await post('/api/settings', {
      roots, lang, interval: +$('#interval').value, snapshot_max_mb: +$('#snapMax').value,
      baseline_text_max_mb: +$('#baseText').value, baseline_copy_mb: +$('#baseCopy').value,
      keep_days: +$('#keepDays').value, max_storage_gb: +$('#maxStorage').value,
      exclude_exts: split($('#exExt').value), exclude_names: split($('#exNames').value), exclude_dirs: split($('#exDirs').value),
      exclude_paths: exPaths,
    });
    if (!r.ok) { notify(esc(errText(r)), true); return; }
    closeModal();
    if (lang !== LANG) setLang(lang, false);
    notify(t('set.saved'));
    loadStats(); loadFiles();
  };
  $('#storageBtn').onclick = showStorage;
  $('#backupBtn').onclick = () => startBackup(false);
  $('#backupRawBtn').onclick = () => startBackup(true);
  $('#exportBtn2').onclick = () => startBackup(false, true);
  $('#importBtn').onclick = async () => {
    const r = await post('/api/import').catch(() => ({ ok: false }));
    if (r.code === 'cancelled') return;
    if (r.ok) notify(t('mv.staged')); else notify(esc(errText(r)), true);
  };
  $('#guideBtn').onclick = () => { closeModal(); showGuide(1); };
  $('#milestones').onchange = ev => post('/api/settings', { milestones: ev.target.checked });
  $('#prescan').onchange = ev => post('/api/settings', { prescan: ev.target.checked }).then(() => notify(t(ev.target.checked ? 'set.prescanOn' : 'set.prescanOff')));
  $('#cleanBtn').onclick = async () => {
    const b = $('#cleanBtn'); b.disabled = true;
    const r = await post('/api/cleanup').catch(() => ({ ok: false }));
    b.disabled = false;
    if (!r.ok) { notify(esc(errText(r)), true); return; }
    notify(t('clean.done', { n: num(r.events), size: fmtSize(r.freed) }));
    loadStats();
  };
  $('#clearBtn').onclick = async () => {
    if (!await confirmBox(t('clear.title'), t('clear.text'), t('clear.ok'), true)) { openSettings(); return; }
    await post('/api/clear');
    notify(t('clear.done'));
  };
  $('#autoStart').onchange = async ev => {
    const box = ev.target;
    box.disabled = true;
    const r = await post('/api/autostart', { enabled: box.checked }).catch(() => ({ ok: false }));
    box.disabled = false;
    if (!r.ok) { box.checked = !box.checked; notify(esc(errText(r)), true); return; }
    box.checked = r.enabled;
    notify(t(r.enabled ? 'autostart.on' : 'autostart.off'));
  };
  $('#notifySeg').onclick = async ev => {
    const b = ev.target.closest('[data-notify]'); if (!b) return;
    const r = await post('/api/settings', { notify: b.dataset.notify });
    if (!r.ok) { notify(esc(errText(r)), true); return; }
    $$('#notifySeg button').forEach(x => x.classList.toggle('on', x === b));
    notify(t('notify.saved'));
  };
  $('#quitBtn').onclick = async () => {
    if (!await confirmBox(t('quit.title'), t('quit.text'), t('quit.ok'), true)) { openSettings(); return; }
    S.stopped = true;
    if (S.es) S.es.close();
    await post('/api/quit').catch(() => null);
    openModal(`<div class="welcome" style="padding:36px 28px">${ART}<h2>${t('stopped.title')}</h2><p>${t('stopped.text')}</p></div>`, 'sm');
  };
}

/* ------------------------------------------------------------------ actions & wiring */
function filterFolder(dir) {  // the Changes list shows only this folder and what is in it (2.1.0)
  S.folder = dir;
  if (S.mode !== 'changes') setMode('changes');
  applyFilters();
}

async function showRestore(e, version, preferReplace) {
  const p = await get('/api/restore-plan', { id: e.id, version, lang: LANG }).catch(() => null);
  if (!p || !p.ok) { notify(esc(t('err.noSnapshot')), true); return; }
  const which = version === 'prev' ? t('rp.before', { time: fmtFull(e.ts) }) : t('rp.saved', { time: fmtFull(p.ts) });
  const mono = x => `<span class="mono">${esc(x)}</span>`;
  openModal(`<div class="m-head"><h3>${t('rp.title')}</h3><button class="icon-btn" data-close>${svg('x')}</button></div>
    <div class="m-body"><table class="kv-table rp-table">
      <tr><td>${t('rp.version')}</td><td>${esc(which)}${p.note ? `<div class="rp-note">${svg('note')}${esc(p.note)}</div>` : ''}</td></tr>
      <tr><td>${t('rp.to')}</td><td>${mono(p.target)}</td></tr>
      <tr><td>${t('rp.exists')}</td><td>${p.exists ? `
        <label class="rp-opt"><input type="radio" name="rpMode" value="copy" ${preferReplace && p.can_replace ? '' : 'checked'}> <span><b>${t('rp.copy')}</b><br>${mono(basename(p.copy))}<br><span class="hint">${t('rp.copyWhy')}</span></span></label>
        <label class="rp-opt${p.can_replace ? '' : ' off'}"><input type="radio" name="rpMode" value="replace" ${p.can_replace ? '' : 'disabled'} ${preferReplace && p.can_replace ? 'checked' : ''}>
          <span><b>${t('rp.replace')}</b><br><span class="hint">${t(p.can_replace ? 'rp.replaceWhy' : 'rp.replaceNo')}</span></span></label>`
        : t('rp.free')}</td></tr></table></div>
    <div class="m-foot"><button class="btn" data-close>${t('btn.cancel')}</button><button class="btn primary" id="rpGo">${svg('restore')}${t('restore.ok')}</button></div>`, 'sm');
  $('#rpGo').onclick = async () => {
    const replace = !!$('input[name=rpMode][value=replace]:checked');
    closeModal();
    const r = await post('/api/restore', { id: e.id, version, replace, lang: LANG });
    if (!r.ok) { notify(esc(errText(r)), true); return; }
    notify(r.replaced ? t('rp.doneReplaced', { path: mono(r.path) }) : r.path !== p.target ? t('rp.doneCopy', { path: mono(r.path) }) : t('restore.done', { path: mono(r.path) }));
  };
}

async function act(name, e, btn) {
  if (name === 'report') {  // the change as an HTML report (2.6.0 #26)
    const r = await post('/api/diff-report', { id: e.id, lang: LANG }).catch(() => ({}));
    if (r.code === 'cancelled') return;
    if (!r.ok) { notify(esc(errText(r)), true); return; }
    notifyAction(t('rep.done', { path: `<span class="mono">${esc(r.path)}</span>` }), t('act.open'), () => post('/api/open', { path: r.path }), 12000);
    return;
  }
  if (name === 'pin') {  // keep forever (2.6.0 #20)
    const r = await post('/api/pin', { path: e.path, on: !e.pinned }).catch(() => ({}));
    if (!r.ok) { notify(esc(errText(r)), true); return; }
    e.pinned = r.pinned; [...S.events, ...S.files].forEach(x => { if (x.path === e.path) x.pinned = r.pinned; });
    notify(t(r.pinned ? 'pin.done' : 'pin.undone', { name: esc(e.name) }));
    if (S.fileSel) selectFile(S.fileSel); else if (S.sel != null) select(S.sel);
    return;
  }
  if (name === 'open' || name === 'reveal') {
    const r = await post('/api/' + name, { path: e.path });
    if (!r.ok) notify(esc(errText(r)), true);
  } else if (name === 'restore' || name === 'replace') {
    showRestore(e, btn?.dataset.version || 'this', name === 'replace');
  } else if (name === 'star') {
    toggleStar(e);
  } else if (name === 'folder-filter') {
    filterFolder(dirname(e.path));
  } else if (name === 'copy-path') {
    navigator.clipboard.writeText(e.path).then(() => notify(t('key.copied', { path: `<span class="mono" style="font-size:12px">${esc(e.path)}</span>` })));
  } else if (name === 'ignore') {
    ignoreFolder(dirname(e.path));
  } else if (name === 'open-version' || name === 'restore-as') {
    const hash = btn?.dataset.hash || (e.kind === 'deleted' ? e.prev_hash : e.hash);
    const ts = +(btn?.dataset.ts || e.ts);
    const r = await post('/api/' + name, { hash, name: e.name, ts, dir: dirname(e.path) });
    if (r.cancelled) return;
    if (!r.ok) notify(esc(errText(r)), true);
    else if (name === 'restore-as') notify(t('restore.done', { path: `<span class="mono" style="font-size:12px">${esc(r.path)}</span>` }));
    else notify(t('ver.opened'));
  }
}

// Stop recording changes inside a folder (Settings → Ignored folders undoes it).
async function ignoreFolder(dir) {
  if (!await confirmBox(t('ign.title'), t('ign.text', { dir: `<span class="mono" style="font-size:12px">${esc(dir)}</span>` }), t('ign.ok'))) return false;
  const r = await post('/api/ignore-folder', { path: dir });
  if (!r.ok) { notify(esc(errText(r)), true); return false; }
  notifyAction(t('ign.done'), t('btn.undo'), async () => {
    const s = await get('/api/settings');
    const back = await post('/api/settings', { exclude_paths: (s.exclude_paths || []).filter(p => p.toLowerCase() !== dir.toLowerCase()) });
    notify(back.ok ? t('ign.undone') : esc(errText(back)), !back.ok);
    loadStats(); loadFiles();
  });
  loadStats(); loadFiles();
  return true;
}

// A toast with one action button (e.g. Undo).
function notifyAction(html, label, fn, ms = 9000) {
  const el = document.createElement('div');
  el.className = 'toast plain';
  el.innerHTML = `<div class="note" style="margin:0;border:0;padding:0;background:none;flex:1">${svg('check')}<div>${html}</div></div><button class="btn sm">${label}</button>`;
  el.querySelector('button').onclick = () => { dismiss(el); fn(); };
  $('#toasts').prepend(el);
  setTimeout(() => dismiss(el), ms);
}

// Show a tracked file in the Files view even if it isn't in the loaded part of the list.
async function openFileByPath(path) {
  if (!S.files.some(f => f.path === path)) {
    const f = await get('/api/file-info', { path }).catch(() => null);
    if (!f || !f.ok) { notify(esc(t('err.gone')), true); return; }
    S.files.unshift(f);
    renderList();
  }
  selectFile(S.files.find(f => f.path.toLowerCase() === path.toLowerCase())?.path || path);
}

// Star or unstar a file; every place that shows it updates at once.
async function toggleStar(e) {
  const on = !e.starred;
  const r = await post('/api/star', { path: e.path, on });
  if (!r.ok) { notify(esc(errText(r)), true); return; }
  for (const x of [...S.byId.values(), ...S.files, S.fileItem].filter(Boolean)) if (x.path === e.path) x.starred = on;
  e.starred = on;
  renderList();
  highlight();
  $$('.star-btn').forEach(b => { b.outerHTML = starBtnHTML(e); });
}

// Open the selected item's file in its own app (double-click or Enter).
async function openItemFile(item) {
  if (!item || !item.path || item.exists === false) return;
  const r = await post('/api/open', { path: item.path });
  if (!r.ok) notify(esc(errText(r)), true);
}

function refreshAll() { loadEvents(); loadFiles(); loadStats(); }

// 1.6.1 keys: 1–4 filter by kind, C copy path, E show in Explorer, N note, ← → tabs, Home / End.
function keys161(ev) {
  const it = currentItem(), k = ev.key;
  const kinds = { 1: 'created', 2: 'modified', 3: 'deleted', 4: 'renamed' };
  if (kinds[k]) {
    S.kinds.has(kinds[k]) ? S.kinds.delete(kinds[k]) : S.kinds.add(kinds[k]);
    if (S.mode !== 'changes') setMode('changes');
    return applyFilters();
  }
  if ((k === 'c' || k === 'C') && it) {
    navigator.clipboard.writeText(it.path).then(() => notify(t('key.copied', { path: `<span class="mono" style="font-size:12px">${esc(it.path)}</span>` })));
  } else if ((k === 'e' || k === 'E') && it) {
    act('reveal', it);
  } else if ((k === 'n' || k === 'N') && it && it.kind !== 'file') {
    ev.preventDefault();
    editNote(it);
  } else if ((k === 'ArrowLeft' || k === 'ArrowRight') && it) {
    const tabs = tabsFor(it).map(x => x[0]), i = tabs.indexOf(S.tab);
    ev.preventDefault();
    switchTab(tabs[(i + (k === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length]);
  } else if (k === 'Home' || k === 'End') {
    ev.preventDefault();
    move(k === 'Home' ? -1e9 : 1e9);
  }
}

function showShortcuts() {
  const row = (keys, key) => `<tr><td>${keys.map(k => `<kbd>${k}</kbd>`).join(' ')}</td><td>${t(key)}</td></tr>`;
  openModal(`<div class="m-head"><h3>${t('help.title')}</h3><button class="icon-btn" data-close aria-label="${esc(t('btn.close'))}">${svg('x')}</button></div>
    <div class="m-body"><table class="keys-table">
      ${row(['↑', '↓'], 'help.move')}${row(['/'], 'help.find')}${row(['Enter'], 'help.open')}${row(['S'], 'help.star')}
      ${row(['M'], 'help.mode')}${F161 ? row(['1', '–', '4'], 'help.kinds') + row(['C'], 'help.copy')
        + row(['E'], 'help.reveal') + row(['N'], 'help.note') + row(['←', '→'], 'help.tabs') + row(['Home', 'End'], 'help.ends')
        + row(['Ctrl', 'E'], 'help.export') + row(['Ctrl', '1', '…', '5'], 'help.views') : ''}${row(['F5'], 'help.refresh')}${row(['Ctrl', ','], 'help.settings')}
      ${row(['Ctrl', 'Alt', 'Z'], 'help.hotkey')}${row(['Ctrl', 'W'], 'help.close')}${row(['Esc'], 'help.esc')}${row(['?'], 'help.help')}
    </table><p class="hint" style="margin-top:12px">${t('help.dbl')} ${t('help.right')}</p>
    <p style="margin-top:12px"><button class="btn sm" id="helpGuide">${svg('info')}${t('gd.why')}</button></p></div><div class="m-foot"></div>`, 'sm');
  $('#helpGuide').onclick = () => { closeModal(); showGuide(1); };
}

function move(delta) {
  if (S.mode === 'space') {
    const cards = $$('.card[data-space]'); if (!cards.length) return;
    const i = cards.findIndex(c => c.dataset.space === S.fileSel);
    const c = cards[Math.max(0, Math.min(cards.length - 1, i < 0 ? 0 : i + delta))];
    c.scrollIntoView({ block: 'nearest' });
    return selectSpaceFile(c.dataset.space);
  }
  if (S.mode === 'dups') {
    const gs = dupGroups(); if (!gs.length) return;
    const i = gs.findIndex(g => g.hash === S.dupSel);
    const g = gs[Math.max(0, Math.min(gs.length - 1, i < 0 ? 0 : i + delta))];
    selectDup(g.hash);
    $(`.card[data-dup="${g.hash}"]`)?.scrollIntoView({ block: 'nearest' });
    return;
  }
  if (S.mode === 'files') {
    if (!S.files.length) return;
    const i = S.files.findIndex(f => f.path === S.fileSel);
    const j = Math.max(0, Math.min(S.files.length - 1, i < 0 ? 0 : i + delta));
    return selectFile(S.files[j].path, { keepTab: true });
  }
  if (!S.events.length) return;
  const i = S.events.findIndex(e => e.id === S.sel);
  const j = Math.max(0, Math.min(S.events.length - 1, i < 0 ? 0 : i + delta));
  select(S.events[j].id, { keepTab: true });
}

function wire() {
  $('#list').addEventListener('click', ev => {
    if (ev.target.closest('#folderAtBtn')) { folderAtDialog(); return; }
    const ds = ev.target.closest('[data-draft-save]');
    if (ds) { post('/api/draft-save', { path: ds.dataset.draftSave }).then(r => r.ok ? notifyAction(t('dr.saved', { path: `<span class="mono">${esc(r.path)}</span>` }), t('act.open'), () => post('/api/open', { path: r.path }), 12000) : notify(esc(errText(r)), true)); return; }
    if (S.mode === 'clean' && ev.target.closest('.cl-item,.cl-bar,[data-cl-drive],[data-cl-file],[data-cl-reveal]')) return cleanAct(ev);
    if (ev.target.closest('#moreBtn')) { loadEvents(true); return; }
    if (ev.target.closest('#restoreShown')) {
      const ids = S.events.filter(e => e.kind === 'deleted' && e.has_prev_blob).map(e => e.id);
      confirmBox(t('g.restoreTitle', { n: ids.length }), esc(t('g.restoreText')), t('restore.ok')).then(async yes => {
        if (!yes) return;
        const r = await post('/api/restore-many', { ids, lang: LANG });
        notify(t('g.restored', { n: r.restored || 0 }) + (r.failed ? ' ' + t('g.failed', { n: r.failed }) : ''), !!r.failed);
      });
      return;
    }
    if (ev.target.closest('#moreFilesBtn')) { loadFiles(true); return; }
    const tog = ev.target.closest('[data-gtoggle]');
    if (tog) {
      const k = tog.dataset.gtoggle;
      S.openGroups.has(k) ? S.openGroups.delete(k) : S.openGroups.add(k);
      renderList();
      highlight();
      return;
    }
    if (ev.target.closest('[data-sp-folder-clear]')) { S.spaceFolder = null; loadSpace(true); return; }
    if (ev.target.closest('[data-sp-stale]')) { S.spaceStale = false; renderList(); if (!S.fileSel) renderSpaceOverview(); return; }
    const ff = ev.target.closest('[data-folder-filter]');
    if (ff) { ev.stopPropagation(); return filterFolder(ff.dataset.folderFilter); }
    const unhide = ev.target.closest('[data-unhide]'); if (unhide) return hideItem(unhide.dataset.unhide);  // show hidden sets / documents again (2.1.0)
    if (ev.target.closest('[data-sp-cat-clear]')) { S.spaceCat = null; renderList(); if (!S.fileSel) renderSpaceOverview(); return; }
    const card = ev.target.closest('.card');
    if (!card) return;
    if (ev.target.closest('[data-to-history]') && card.dataset.path) {  // "N changes" goes straight to History (2.0.1)
      selectFile(card.dataset.path, { scroll: false });
      return switchTab('history');
    }
    if (card.dataset.dup) return selectDup(card.dataset.dup);
    if (card.dataset.space) return selectSpaceFile(card.dataset.space);
    if (card.dataset.gkey) selectGroup(card.dataset.gkey);
    else if (card.dataset.path) selectFile(card.dataset.path, { scroll: false });
    else select(+card.dataset.id, { scroll: false });
  });
  // right-click a change or file: its common actions, like any desktop app (2.0.1)
  $('#list').addEventListener('contextmenu', ev => {
    const dupCard = ev.target.closest('.card[data-dup]');
    if (dupCard) {  // a set of duplicates: open / show the newest, or keep it and recycle the rest (2.0.1)
      ev.preventDefault();
      selectDup(dupCard.dataset.dup);
      const g = dupGroups().find(x => x.hash === dupCard.dataset.dup); if (!g) return;
      const m = $('#ctxMenu');
      m.innerHTML = `<button data-dctx="open">${svg('open')}<span>${t('act.open')}</span></button>
        <button data-dctx="reveal">${svg('folder')}<span>${t('act.reveal')}</span></button>
        <button data-dctx="keep-newest">${svg('trash')}<span>${t('dup.keepNewest', { n: g.count - 1 })}</span></button>
        <button data-dctx="not-dup">${svg('eyeoff')}<span>${t('hide.dup')}</span></button>`;
      m.hidden = false;
      m.style.left = Math.min(ev.clientX, innerWidth - m.offsetWidth - 8) + 'px';
      m.style.top = Math.min(ev.clientY, innerHeight - m.offsetHeight - 8) + 'px';
      m.onclick = c => { const b = c.target.closest('[data-dctx]'); if (!b) return; m.hidden = true; dupAct(b.dataset.dctx, g.files[0].path); };
      return;
    }
    const card = ev.target.closest('.card[data-id], .card[data-path], .card[data-space]');
    if (!card) return;
    ev.preventDefault();
    const path = card.dataset.path || card.dataset.space;
    const e = card.dataset.id ? S.byId.get(+card.dataset.id) : (S.files.find(f => f.path === path) || { path, name: basename(path), kind: 'file', exists: true });
    if (!e) return;
    const restoreVer = e.kind === 'deleted' ? (e.has_prev_blob && 'prev') : (e.kind !== 'file' && e.has_blob && 'this');
    const items = [
      e.exists !== false && ['open', 'open', t('act.open')], ['reveal', 'folder', t('act.reveal')],
      restoreVer && ['restore', 'restore', t(e.kind === 'deleted' ? 'act.restoreFile' : 'act.restoreThis'), restoreVer],
      e.kind !== 'deleted' && e.kind !== undefined && ['star', 'star', t(e.starred ? 'star.remove' : 'star.add')],
      F161 && e.kind !== 'file' && ['note', 'note', t(e.note ? 'note.edit' : 'note.add')],
      ['folder-filter', 'folder', t('folder.only')], ['copy-path', 'copy', t('path.copy')]].filter(Boolean);
    const m = $('#ctxMenu');
    m.innerHTML = items.map(([a, ic, label, v]) => `<button data-ctx="${a}" ${v ? `data-version="${v}"` : ''}>${svg(ic)}<span>${label}</span></button>`).join('');
    m.hidden = false;
    m.style.left = Math.min(ev.clientX, innerWidth - m.offsetWidth - 8) + 'px';
    m.style.top = Math.min(ev.clientY, innerHeight - m.offsetHeight - 8) + 'px';
    m.onclick = async c => {
      const b = c.target.closest('[data-ctx]'); if (!b) return;
      m.hidden = true;
      if (b.dataset.ctx === 'note') { if (card.dataset.id) { select(e.id); setTimeout(() => editNote(e), 50); } return; }
      act(b.dataset.ctx, e, b);
    };
  });
  document.addEventListener('click', ev => { if (!ev.target.closest('#ctxMenu')) $('#ctxMenu').hidden = true; });
  $('#list').addEventListener('scroll', () => { $('#ctxMenu').hidden = true; }, { passive: true });
  $('#list').addEventListener('dblclick', ev => {
    const card = ev.target.closest('.card');
    if (!card || card.dataset.gkey || ev.target.closest('[data-gtoggle]')) return;
    openItemFile(card.dataset.path ? S.files.find(f => f.path === card.dataset.path) : S.byId.get(+card.dataset.id));
  });
  $('#list').addEventListener('scroll', () => {  // load older items before the end is reached
    const l = $('#list');
    if (l.scrollTop + l.clientHeight < l.scrollHeight - 400) return;
    if (S.mode === 'changes' && S.more) loadEvents(true);
    else if (S.mode === 'files' && S.files.length < S.fileTotal) loadFiles(true);
  }, { passive: true });
  $('#rangeSeg').addEventListener('click', ev => {
    const b = ev.target.closest('[data-range]'); if (!b || (b.dataset.range === S.range && !S.day)) return;
    S.range = b.dataset.range;
    S.day = null;
    saveView();
    applyFilters();
  });
  // go to any day in the change list (2.1.0): a one-day filter
  $('#dayPick').innerHTML = svg('clock');
  $('#dayPick').onclick = () => {
    const inp = $('#dayInput'), now = new Date();
    inp.max = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    try { inp.showPicker(); } catch { inp.focus(); }
  };
  $('#dayInput').onchange = ev => {
    const v = ev.target.value; if (!v) return;
    S.day = { since: new Date(v + 'T00:00') / 1000, label: new Date(v + 'T12:00').toLocaleDateString(loc(), { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' }) };
    ev.target.value = '';
    if (S.mode !== 'changes') setMode('changes');
    applyFilters();
  };
  $('#rangeYesterday').hidden = !F161;
  $('#notedBtn').innerHTML = svg('note') + '<span class="n" id="notesCount"></span>';
  $('#notedBtn').onclick = () => { S.notedOnly = !S.notedOnly; applyFilters(); };
  $('#similarBtn').onclick = findSimilar;  // 2.6.0 #32
  document.addEventListener('toggle', ev => { if (ev.target.classList?.contains('cl-drawer')) S.drawerOpen = ev.target.open; }, true);
  $('#goneBtn').innerHTML = svg('restore') + `<span data-i18n="del.btn">${t('del.btn')}</span>`;
  $('#goneBtn').onclick = () => {  // one click to the files that were deleted and are still missing (2.4.2)
    get('/api/drafts').then(r => { S.drafts = r.items || []; if (S.goneOnly) renderList(); }).catch(() => {});
    S.goneOnly = !S.goneOnly;
    if (S.goneOnly) { S.kinds = new Set(['deleted']); S.range = 'all'; S.day = null; S.notedOnly = false; }
    else S.kinds.delete('deleted');
    if (S.mode !== 'changes') setMode('changes');
    applyFilters();
  };  // versions with a note (2.2.0: was its own sidebar entry)
  $('#starBtn').addEventListener('click', () => { S.starOnly = !S.starOnly; applyFilters(); });
  $('#exportBtn').addEventListener('click', () => { location.href = `/api/export?${qs({ ...eventParams(), lang: LANG })}`; });
  $('#modeSeg').addEventListener('click', ev => { const b = ev.target.closest('[data-mode]'); if (b) setMode(b.dataset.mode); });
  $('#sortSel').addEventListener('change', ev => { S.sort = ev.target.value; saveView(); loadFiles(); });
  $('#dupSort').addEventListener('change', ev => { S.dupSort = ev.target.value; saveView(); renderList(); });
  $('#changedOnly').addEventListener('click', () => {  // Files: only files that have a history (2.0.1)
    S.changedOnly = !S.changedOnly;
    $('#changedOnly').classList.toggle('on', S.changedOnly);
    $('#changedOnly').setAttribute('aria-pressed', S.changedOnly);
    saveView(); loadFiles();
  });
  $('#spaceOverview').addEventListener('click', renderSpaceOverview);
  $('#cleanTools').addEventListener('click', ev => { if (ev.target.closest('[data-cl-rescan],[data-cl-stop]')) cleanAct(ev); });
  new MutationObserver(renderTabs).observe($('#modeSeg'), { subtree: true, childList: true, characterData: true });  // badges follow
  $('#warnBar').addEventListener('click', ev => {
    const b = ev.target.closest('[data-warn-go]'); if (!b) return;
    if (b.dataset.warnGo === 'clean') setMode('clean'); else { openSettings(); setTimeout(() => $('#backupBtn')?.scrollIntoView({ block: 'center' }), 300); }
  });
  $('#viewTabs').addEventListener('click', ev => {  // the tabs of the open group (2.3.0)
    const b = ev.target.closest('[data-mode]'); if (b) setMode(b.dataset.mode);
  });
  $$('[data-export-view]').forEach(b => {  // Duplicates / Space as Excel (2.0.1)
    b.innerHTML = `${svg('download')}Excel`;
    b.onclick = () => { location.href = `/api/export-view?${qs({ view: b.dataset.exportView, lang: LANG, folder: b.dataset.exportView === 'space' ? S.spaceFolder : '', stale: b.dataset.exportView === 'space' && S.spaceStale ? 1 : '' })}`; };
  });
  $('#searchSeg').addEventListener('click', ev => {
    const b = ev.target.closest('[data-smode]'); if (!b || b.dataset.smode === S.smode) return;
    S.smode = b.dataset.smode;
    saveView();
    S.files = [];
    renderList();
    loadFiles();
    $('#q').focus();
  });
  $('#kpis').addEventListener('click', ev => {
    const b = ev.target.closest('[data-kind]'); if (!b) return;
    const k = b.dataset.kind;
    S.kinds.has(k) ? S.kinds.delete(k) : S.kinds.add(k);
    if (S.mode !== 'changes') setMode('changes');
    applyFilters();
  });
  $('#cats').addEventListener('click', ev => {
    const b = ev.target.closest('[data-cat]'); if (!b) return;
    const c = b.dataset.cat;
    S.cats.has(c) ? S.cats.delete(c) : S.cats.add(c);
    applyFilters();
  });
  $('#activeFilters').addEventListener('click', ev => {
    const b = ev.target.closest('.chip'); if (!b) return;
    if ('rmGone' in b.dataset) { S.goneOnly = false; S.kinds.delete('deleted'); }
    else if ('rmKind' in b.dataset) { S.kinds.delete(b.dataset.rmKind); if (b.dataset.rmKind === 'deleted') S.goneOnly = false; }
    else if ('rmCat' in b.dataset) S.cats.delete(b.dataset.rmCat);
    else if ('rmQ' in b.dataset) { S.q = ''; $('#q').value = ''; }
    else if ('rmStar' in b.dataset) S.starOnly = false;
    else if ('rmDay' in b.dataset) S.day = null;
    else if ('rmNoted' in b.dataset) S.notedOnly = false;
    else if ('rmFolder' in b.dataset) S.folder = null;
    else { S.kinds.clear(); S.cats.clear(); S.q = ''; $('#q').value = ''; S.starOnly = false; S.day = null; S.notedOnly = false; S.folder = null; S.goneOnly = false; }
    applyFilters();
  });
  let qt;
  $('#q').addEventListener('input', ev => {
    clearTimeout(qt);
    qt = setTimeout(() => { S.q = ev.target.value.trim(); applyFilters(); }, 250);
  });
  $('#detail').addEventListener('click', ev => {
    if (S.mode === 'clean' && ev.target.closest('[data-cl-folder],[data-cl-up],[data-cl-reveal],[data-cl-del],[data-cl-online],[data-cl-apps],[data-cl-file],[data-cl-back],[data-cl-jump],[data-growth],[data-cl-tool],[data-lo-del],[data-git-gc],[data-cl-move],[data-cl-moveback],[data-fix-name],[data-cloud-free]')) return cleanAct(ev);
    const e = currentItem();
    const mb = ev.target.closest('[data-more]');
    if (mb) { const m = mb.nextElementSibling; m.hidden = !m.hidden; return; }
    if (ev.target.closest('.act-menu')) ev.target.closest('.act-menu').hidden = true;
    const ga = ev.target.closest('[data-gact]'); if (ga) return groupAct(ga.dataset.gact);
    const da = ev.target.closest('[data-dup-act]'); if (da) return dupAct(da.dataset.dupAct, da.dataset.path);
    const so = ev.target.closest('[data-sp-open]'); if (so) return post('/api/reveal', { path: so.dataset.spOpen });
    const sf = ev.target.closest('[data-sp-folder]');  // drill into a folder (2.0.1)
    if (sf) { S.spaceFolder = sf.dataset.spFolder; S.spaceCat = null; return loadSpace(true); }
    if (ev.target.closest('[data-sp-up]')) { S.spaceFolder = null; return loadSpace(true); }
    if (ev.target.closest('[data-sp-stale]')) { S.spaceStale = !S.spaceStale; S.spaceCat = null; renderList(); return renderSpaceOverview(); }
    const sc = ev.target.closest('[data-sp-cat]');
    if (sc) { S.spaceStale = false; S.spaceCat = S.spaceCat === sc.dataset.spCat ? null : sc.dataset.spCat; renderList(); return renderSpaceOverview(); }
    if (ev.target.closest('[data-note-edit]') && e) return editNote(e);
    if (ev.target.closest('.vpick')) return;  // ticking a version to compare, not opening that change
    const cc = ev.target.closest('[data-cmp-current]');
    if (cc && e) return showCompare(e, $('#tabBody'), { v: cc.dataset.cmpCurrent, ts: 0, label: cc.dataset.cmpLabel },
      { v: 'current', ts: 1, label: t('cmp.current') });
    const tb = ev.target.closest('[data-tab]'); if (tb) return switchTab(tb.dataset.tab);
    const g = ev.target.closest('[data-goto]'); if (g) return switchTab(g.dataset.goto);
    const a = ev.target.closest('[data-act]'); if (a && e) return act(a.dataset.act, e, a);
    const h = ev.target.closest('[data-hid]'); if (h) return select(+h.dataset.hid, { keepTab: false });
    if (ev.target.closest('#dClose')) { $('#detail').classList.remove('open'); if (S.mode === 'clean') renderCleanOverview(); return; }
    const c = ev.target.closest('[data-copy]');
    if (c) {
      navigator.clipboard.writeText(c.dataset.copy).then(() => {
        c.innerHTML = svg('check');
        setTimeout(() => { c.innerHTML = svg('copy'); }, 1200);
      });
    }
  });
  $('#scope').addEventListener('click', ev => { if (ev.target.id === 'editScope') { ev.preventDefault(); openSettings(); } });
  const setPause = async (paused, minutes = 0) => {
    const r = await post('/api/pause', { paused, minutes });
    if (S.status) Object.assign(S.status, { paused: r.paused, pause_until: r.paused ? r.pause_until : 0 });
    renderStatus();
  };
  $('#pauseBtn').onclick = ev => {  // resume at once; pausing asks for how long
    ev.stopPropagation();
    if (S.status && S.status.paused) return setPause(false);
    if (!F161) return setPause(true);
    const now = new Date(), morning = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 8);
    const toMorning = String(Math.round((morning - now) / 60000));
    $('#pauseMenu').innerHTML = [['30', 'pause.30'], ['120', 'pause.120'], [toMorning, 'pause.tomorrow'], ['0', 'pause.indef']]
      .map(([m, k]) => `<button data-pause="${m}">${svg(m === '0' ? 'pause' : 'clock')}<span>${t(k)}</span></button>`).join('');
    $('#pauseMenu').hidden = !$('#pauseMenu').hidden;
  };
  $('#pauseMenu').addEventListener('click', ev => {
    const b = ev.target.closest('[data-pause]'); if (!b) return;
    $('#pauseMenu').hidden = true;
    setPause(true, +b.dataset.pause);
  });
  $('#langBtn').onclick = ev => { ev.stopPropagation(); $('#langMenu').hidden = !$('#langMenu').hidden; };
  $('#langMenu').addEventListener('click', ev => {
    const b = ev.target.closest('[data-lang]'); if (!b) return;
    $('#langMenu').hidden = true;
    setLang(b.dataset.lang);
  });
  document.addEventListener('click', ev => {
    if (!ev.target.closest('.lang-wrap')) { $('#langMenu').hidden = true; $('#pauseMenu').hidden = true; $('#ctxMenu').hidden = true; }
    if (!ev.target.closest('.more-wrap')) $$('.act-menu').forEach(m => { m.hidden = true; });
  });
  $('#settingsBtn').innerHTML = svg('gear');
  $('#settingsBtn').onclick = openSettings;
  $('#updBtn').onclick = showUpdate;
  $('#themeBtn').onclick = () => setTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark');
  $('#sidebarBtn').innerHTML = svg('menu');
  $('#sidebarBtn').onclick = () => $('#sidebar').classList.toggle('open');
  $('#modalBack').addEventListener('click', ev => {
    if (S.stopped) return;  // the "stopped" notice stays up
    if (ev.target.id === 'modalBack' || ev.target.closest('[data-close]')) closeModal();
  });
  document.addEventListener('keydown', ev => {
    // Desktop-app shortcuts (the window turns off the browser's own ones)
    const k = ev.key.toLowerCase();
    if (ev.ctrlKey && !ev.altKey && k === 'w') { ev.preventDefault(); hostMessage({ cmd: 'close' }); return; }
    if (!$('#modalBack').hidden) { if (ev.key === 'Escape' && !S.stopped) closeModal(); return; }
    if (ev.ctrlKey && !ev.altKey && !ev.shiftKey) {
      if (k === 'f' || k === 'k') { ev.preventDefault(); $('#q').focus(); $('#q').select(); return; }
      if (k === ',') { ev.preventDefault(); openSettings(); return; }
      if (k === 'r') { ev.preventDefault(); refreshAll(); return; }
      if (F161 && k === 'e') { ev.preventDefault(); $('#exportBtn').click(); return; }
      const views = { 1: 'changes', 2: 'files', 3: 'dups', 4: 'space', 5: 'clean' };  // Ctrl+3-5 added in 2.0.1
      if (F161 && views[k]) { ev.preventDefault(); setMode(views[k]); return; }
    }
    if (ev.key === 'F5') { ev.preventDefault(); refreshAll(); return; }
    if (ev.target.matches?.('input, textarea, select')) {
      if (ev.key === 'Escape') { if (ev.target.id === 'q' && ev.target.value) { ev.target.value = ''; S.q = ''; applyFilters(); } ev.target.blur(); }
      return;
    }
    if (ev.key === '/') { ev.preventDefault(); $('#q').focus(); }
    else if (ev.key === 'ArrowDown' || ev.key === 'j') { ev.preventDefault(); move(1); }
    else if (ev.key === 'ArrowUp' || ev.key === 'k') { ev.preventDefault(); move(-1); }
    else if (ev.key === 'Enter' && !ev.target.closest?.('button, a')) {
      ev.preventDefault();
      const g = S.mode === 'dups' && dupGroups().find(x => x.hash === S.dupSel);
      if (g) dupAct('open', g.files[0].path); else openItemFile(currentItem());  // a duplicate set: its newest copy
    }
    else if (ev.key === 's' || ev.key === 'S') { const it = currentItem(); if (it && it.kind !== 'deleted') toggleStar(it); }
    else if (ev.key === 'm' || ev.key === 'M') setMode(S.mode === 'changes' ? 'files' : 'changes');
    else if (ev.key === '?') showShortcuts();
    else if (ev.key === 'Escape') { $('#detail').classList.remove('open'); $('#sidebar').classList.remove('open'); $('#langMenu').hidden = true; $('#pauseMenu').hidden = true; $('#ctxMenu').hidden = true; }
    else if (F161 && !ev.ctrlKey && !ev.altKey) keys161(ev);  // last: it looks at any key (Esc above it, fixed in 2.0.1)
  });
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) { S.unseen = 0; document.title = t('app.name'); }
  });
  // periodic refreshes only while the window can be seen; a hidden or minimized window does no work (2.1.0)
  const refreshTimes = () => $$('[data-ts]').forEach(el => { const ts = +el.dataset.ts; el.textContent = `${rel(ts)} · ${fmtTime(ts)}`; });
  const refreshBadges = () => { loadDups(); loadSpace(false); };  // sidebar counts of the views that aren't open
  setInterval(() => { if (!document.hidden) refreshTimes(); }, 15000);
  setInterval(() => { if (!document.hidden) loadStats(); }, 30000);
  setInterval(() => { if (!document.hidden) refreshBadges(); }, 120000);
  let hiddenAt = 0;
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) { hiddenAt = Date.now(); return; }
    refreshTimes();
    if (S.missed) {  // changes arrived while hidden: one redraw and one reload of each view now (2.1.0)
      S.missed = false;
      if (S.mode === 'changes') renderList();
      $('#count').textContent = S.events.length ? num(S.events.length) : '';
      loadStats(); loadFiles(); refreshBadges(); scheduleGroupDetail();
    } else if (Date.now() - hiddenAt > 30000) { loadStats(); refreshBadges(); }  // catch up after a while away
  });
}

// The window opens where it was left: view, date range, sort order and search mode (1.6.2).
function saveView() { store('dw-view', JSON.stringify({ mode: S.mode, range: S.range, sort: S.sort, smode: S.smode, dupSort: S.dupSort, changedOnly: !!S.changedOnly })); }
function restoreView() {
  let v = {};
  try { v = JSON.parse(store('dw-view') || '{}'); } catch { /* ignore a damaged value */ }
  if (['changes', 'files', 'dups', 'space', 'clean'].includes(v.mode)) S.mode = v.mode;
  if (['all', 'today', 'yesterday', '7', '30'].includes(v.range)) S.range = v.range;
  if (['recent', 'name', 'size', 'changes'].includes(v.sort)) { S.sort = v.sort; $('#sortSel').value = v.sort; }
  if (['name', 'content'].includes(v.smode)) S.smode = v.smode;
  if (['wasted', 'count', 'name'].includes(v.dupSort)) { S.dupSort = v.dupSort; $('#dupSort').value = v.dupSort; }
  if (v.changedOnly) { S.changedOnly = true; $('#changedOnly').classList.add('on'); $('#changedOnly').setAttribute('aria-pressed', 'true'); }
}

async function init() {
  LANG = LANGS[store('dw-lang')] ? store('dw-lang') : detectLang();
  S.diffView = store('dw-diffview') || 'unified';
  restoreView();
  setTheme(getTheme());
  applyStatic();
  wire();
  renderWelcome();
  renderStatus();
  loadStats();
  loadEvents();
  loadFiles();
  // the open view loads at once; the other views' sidebar counts follow once the window is drawn (2.1.0)
  const later = fn => setTimeout(fn, 1500);
  (S.mode === 'dups' ? loadDups : () => later(loadDups))();
  (S.mode === 'space' ? () => loadSpace(true) : () => later(() => loadSpace(false)))();
  if (S.mode === 'clean') loadClean();
  get('/api/settings').then(s => { if (s && s.onboarded === false) setTimeout(() => showGuide(1), 800); }).catch(() => {});
  connect();
  window.addEventListener('hashchange', openFromHash);
  // The server remembers the chosen language, so it survives a port change or a cleared browser.
  const s = await get('/api/settings');
  if (s.lang && LANGS[s.lang] && s.lang !== LANG) setLang(s.lang, false);
  openFromHash();
  checkUpdate(/update/.test(location.hash));
}

/* Links like #event=123 (desktop notifications, tray), #file=<path> (Explorer's right-click entry)
   and #update (tray) open that thing directly. */
async function openFromHash() {
  const h = location.hash;
  if (!h) return;
  history.replaceState(null, '', location.pathname);
  const ev = /event=(\d+)/.exec(h), file = /file=([^&]+)/.exec(h), del = /deleted=([^&]+)/.exec(h);
  if (/update/.test(h)) return checkUpdate(true);
  if (/recent/.test(h)) {  // Ctrl+Alt+Z: what was just deleted or overwritten (2.6.0 #14)
    S.folder = null; S.goneOnly = false; S.kinds = new Set(['deleted', 'modified']); S.range = 'today'; S.day = null;
    setMode('changes'); applyFilters();
    return;
  }
  if (del) {  // Explorer: "deleted files here" (2.6.0 #4)
    S.folder = decodeURIComponent(del[1]); S.goneOnly = true; S.kinds = new Set(['deleted']); S.range = 'all'; S.day = null;
    setMode('changes'); applyFilters();
    return;
  }
  if (file) {
    setMode('files');
    return openFileByPath(decodeURIComponent(file[1]));
  }
  if (!ev) return;
  const id = +ev[1];
  if (!S.byId.has(id)) {
    const e = await get('/api/event', { id }).catch(() => null);
    if (!e || !e.id) return;
    S.byId.set(e.id, e);
  }
  setMode('changes');
  select(id);
}

/* ------------------------------------------------------------------ updates (version licenses) */
// Asked on every start of the window while an update is waiting; never forced.
async function checkUpdate(force = false) {
  const u = await get('/api/update', { lang: LANG }).catch(() => null);
  if (!u) return;
  S.update = u;
  renderUpdateBadge();
  if (u.result) {
    const r = u.result;
    if (r.ok && (r.changelog || []).length) notifyAction(t('upd.done', { from: esc(r.from), to: esc(r.to) }), t('upd.whatsNewBtn'), () => showWhatsNew(r));
    else notify(r.ok ? t('upd.done', { from: esc(r.from), to: esc(r.to) })
      : t('upd.failed', { from: esc(r.from), to: esc(r.to || '?'), err: esc(r.error || '') }), !r.ok);
    post('/api/update/seen');
  }
  if (u.available && $('#modalBack').hidden) showUpdate();
  else if (force && !u.available) notify(t('upd.none'));
}
// After an update: what it brought, newest version first, each change with its level (2.0.1).
function showWhatsNew(r) {
  const rels = [...r.changelog].sort((a, b) => b.version.localeCompare(a.version, undefined, { numeric: true }));
  openModal(`<div class="m-head"><h3>${t('upd.whatsNewTitle', { v: esc(r.to) })}</h3><button class="icon-btn" data-close>${svg('x')}</button></div>
    <div class="m-body"><div class="upd-changes">${rels.map(x => `<div class="upd-rel"><div class="upd-rel-h"><b>${esc(x.version)}</b>${x.date ? `<span class="hint">${t('upd.released', { d: esc(x.date) })}</span>` : ''}</div>
      ${(x.changes || []).length ? `<ul class="upd-items">${[...x.changes].sort((a, b) => b.level - a.level).map(c => `<li>${levelHTML(c.level)}<span>${esc(c[LANG] || c.en)}</span></li>`).join('')}</ul>`
        : `<div class="upd-notes">${esc((x.notes || {})[LANG] || (x.notes || {}).en || '')}</div>`}</div>`).join('')}</div></div>
    <div class="m-foot"><button class="btn primary" data-close>${t('btn.close')}</button></div>`, 'upd');
}

function renderUpdateBadge() {
  const u = S.update, b = $('#updBtn');
  b.hidden = !(u && u.available);
  const n = (u && u.versions || []).length;
  if (!b.hidden) b.innerHTML = `${svg('download')}${n > 1 ? t('upd.badgeMany', { n }) : t('upd.badge', { v: esc(u.version) })}`;
}
const levelHTML = l => `<span class="lvl l${l}" title="${esc(t('lvl.hint' + l))}">${t('lvl.' + l)}</span>`;

// Every newer version found is offered; the newest is preselected, any other can be chosen.
function showUpdate() {
  const u = S.update;
  if (!u || !u.available) return;
  const vs = u.versions && u.versions.length ? u.versions
    : [{ version: u.version, released: u.released, source: u.source, top: 0, changes: [{ version: u.version, items: [], notes: u.notes }] }];
  let pick = vs[0].version;
  const changesHTML = v => v.changes.map(r => `<div class="upd-rel"><div class="upd-rel-h"><b>${esc(r.version)}</b>${r.released ? `<span class="hint">${t('upd.released', { d: esc(r.released) })}</span>` : ''}</div>
      ${r.items.length ? `<ul class="upd-items">${[...r.items].sort((a, b) => b.level - a.level).map(c => `<li>${levelHTML(c.level)}<span>${esc(c.text)}</span></li>`).join('')}</ul>`
        : r.notes ? `<div class="upd-notes">${esc(r.notes)}</div>` : ''}</div>`).join('');
  const draw = () => {
    const v = vs.find(x => x.version === pick);
    $('#updList').innerHTML = vs.map((x, i) => `<button class="upd-ver${x.version === pick ? ' on' : ''}" data-ver="${esc(x.version)}">
        <span class="radio"></span><span class="vv">${esc(x.version)}</span>${i === 0 ? `<span class="tag latest">${t('upd.latest')}</span>` : ''}
        ${x.top ? levelHTML(x.top) : ''}<span class="hint">${t('upd.nChanges', { n: x.changes.reduce((a, r) => a + r.items.length, 0) })}</span></button>`).join('');
    $('#updChanges').innerHTML = changesHTML(v);
    $('#updSrc').innerHTML = v.source ? `${svg('folder')}<span>${t('upd.from')}</span><code>${esc(v.source)}</code>` : '';
    $('#updNow').innerHTML = `${svg('download')}${t('upd.install', { v: esc(pick) })}`;
  };
  openModal(`<div class="m-head"><h3>${vs.length > 1 ? t('upd.titleMany', { n: vs.length }) : t('upd.title', { v: esc(vs[0].version) })}</h3><button class="icon-btn" data-close>${svg('x')}</button></div>
    <div class="m-body upd-body">
      <p>${vs.length > 1 ? t('upd.leadMany', { cur: esc(u.current) }) : t('upd.lead', { v: esc(vs[0].version), cur: esc(u.current) })}</p>
      <div class="upd-list" id="updList" ${vs.length > 1 ? '' : 'hidden'}></div>
      <div class="field"><label>${t('upd.whatsNew')}</label><div class="upd-changes" id="updChanges"></div></div>
      <div class="upd-src" id="updSrc"></div>
      ${u.can_apply ? noteHTML(t('upd.keep')) : noteHTML(t('upd.cannot'), true)}
    </div>
    <div class="m-foot"><span class="hint left">${t('upd.laterHint')}</span><button class="btn" data-close>${t('upd.later')}</button>
      <button class="btn primary" id="updNow" ${u.can_apply ? '' : 'disabled'}></button></div>`, 'upd');
  draw();
  $('#updList').onclick = ev => { const b = ev.target.closest('[data-ver]'); if (b) { pick = b.dataset.ver; draw(); } };
  $('#updNow').onclick = () => applyUpdate(pick);
}
async function applyUpdate(version) {
  const v = version || S.update.version;
  S.updating = true;
  const r = await post('/api/update/apply', { version: v }).catch(() => ({ ok: false, code: 'generic' }));
  if (!r.ok) { S.updating = false; notify(esc(errText(r)), true); return; }
  S.stopped = true;  // the service restarts: no "reconnecting" noise
  if (S.es) S.es.close();
  openModal(`<div class="welcome" style="padding:36px 28px">${ART}<h2>${t('upd.working', { v: esc(v) })}</h2>
    <p>${t('upd.workingText')}</p>${loadingHTML()}</div>`, 'sm');
}

init();
