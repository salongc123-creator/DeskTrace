'use strict';
/* DeskTrace 2.7.0 — window side of the 2.7.0 list and the 2.8.0 proposal. Loaded after app.js; it extends
   app.js's functions by wrapping them (they are plain global functions), so app.js itself stays as it was.
   Every text goes through t() (i18n.js, en + zh). */

const P = {};  // the 2.7.0 preferences (Settings), as the service keeps them
const pf = k => P[k];
async function loadPrefs() {
  const s = await get('/api/settings').catch(() => null); if (!s) return;
  Object.assign(P, s);
  applyPrefs();
}
function setPref(k, v) { P[k] = v; applyPrefs(); return post('/api/settings', { [k]: v }); }
const reduceMotion = () => matchMedia('(prefers-reduced-motion: reduce)').matches || P.animations === false;
function applyPrefs() {
  document.documentElement.style.zoom = (P.zoom || 100) / 100;   // M1-4
  document.documentElement.classList.toggle('no-motion', reduceMotion());  // M2-12
  document.documentElement.dataset.split = P.split || 'auto';   // M2-19
  hostMessage({ topmost: !!P.topmost, compact: !!P.compact });  // M1-2 (the app window does it)
}

/* ---------------------------------------------------------------- M1-1 scroll position per view */
S.scrollAt = {};
const _setMode = setMode;
setMode = function (mode) {
  if (S.mode !== mode) S.scrollAt[S.mode] = $('#list').scrollTop;
  _setMode(mode);
  S.wantScroll = S.scrollAt[mode] || 0;
  restoreScroll();
};
function restoreScroll() {
  if (!S.wantScroll) return;
  const l = $('#list');
  if (l.scrollHeight - l.clientHeight >= S.wantScroll) { l.scrollTop = S.wantScroll; S.wantScroll = 0; }
}
const _renderList = renderList;
renderList = function (prepended) {
  _renderList(prepended);
  if (S.mode === 'changes') decorateCards();
  if (S.mode === 'clean') decorateClean();
  restoreScroll();
};

/* ---------------------------------------------------------------- M2-10 relative / absolute time */
const _rel = rel;
rel = function (ts) {
  if (P.time_mode === 'abs') return new Date(ts * 1000).toLocaleDateString(loc(), { month: 'short', day: 'numeric', year: new Date(ts * 1000).getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined });
  return _rel(ts);
};

/* ---------------------------------------------------------------- cards: labels, unread, restorability, multi-select */
const LABELS = ['final', 'draft', 'important', 'sent'];
const labelHTML = l => l ? `<span class="nlabel l-${l}" title="${esc(t('lbl.' + l))}"><i></i>${t('lbl.' + l)}</span>` : '';
function decorateCards() {
  const seen = +(P.seen_upto || 0);
  $$('#list .card[data-id]').forEach(c => {
    const e = S.byId.get(+c.dataset.id); if (!e) return;
    c.classList.toggle('multi', !!(S.multi && S.multi.has(e.id)));
    if (e.id > seen && seen) c.classList.add('unread');                       // M2-29
    if (e.label && !c.querySelector('.nlabel')) c.querySelector('.crow1')?.insertAdjacentHTML('beforeend', labelHTML(e.label));  // M1-15
    if ((e.kind === 'modified' || e.kind === 'created') && !e.has_blob && !c.querySelector('.rs-no'))  // S3.1: no copy of this version
      c.querySelector('.crow2')?.insertAdjacentHTML('beforeend', `<span class="rs-no" title="${esc(t('rs.noVerWhy'))}">${t('rs.noVer')}</span>`);
  });
  renderMultiBar();
}

S.multi = new Set();
$('#list').addEventListener('click', ev => {  // M2-8: Ctrl+click picks one more, Shift+click a run
  const card = ev.target.closest('.card[data-id]');
  if (!card || !(ev.ctrlKey || ev.shiftKey) || S.mode !== 'changes') return;
  ev.preventDefault(); ev.stopImmediatePropagation();
  const id = +card.dataset.id;
  if (ev.shiftKey && S.multiLast != null) {
    const ids = S.events.map(e => e.id), a = ids.indexOf(S.multiLast), b = ids.indexOf(id);
    ids.slice(Math.min(a, b), Math.max(a, b) + 1).forEach(i => S.multi.add(i));
  } else S.multi.has(id) ? S.multi.delete(id) : S.multi.add(id);
  if (S.sel != null && !S.multi.size) S.multi.add(S.sel);
  S.multiLast = id;
  decorateCards();
}, true);
function renderMultiBar() {
  let bar = $('#multiBar');
  if (!S.multi.size || S.mode !== 'changes') { if (bar) bar.remove(); return; }
  if (!bar) { bar = document.createElement('div'); bar.id = 'multiBar'; bar.className = 'multi-bar'; $('#list').before(bar); }
  bar.innerHTML = `<b>${t('ms.picked', { n: S.multi.size })}</b><span class="spacer"></span>
    <button class="btn sm" data-mb="note">${svg('note')}${t('ms.note')}</button>
    <button class="btn sm" data-mb="save">${svg('copy')}${t('ms.save')}</button>
    <button class="btn sm primary" data-mb="restore">${svg('restore')}${t('ms.restore')}</button>
    <button class="btn sm ghost" data-mb="clear">${svg('x')}</button>`;
  bar.onclick = async ev => {
    const b = ev.target.closest('[data-mb]'); if (!b) return;
    const ids = [...S.multi];
    if (b.dataset.mb === 'clear') { S.multi.clear(); return decorateCards(); }
    if (b.dataset.mb === 'note') return noteMany(ids);
    if (b.dataset.mb === 'save') {
      const p = await post('/api/pick-folder'); if (!p.path) return;
      if (!await confirmBox(t('ms.saveTitle', { n: ids.length }), esc(t('ms.saveText', { dir: p.path })), t('ms.save'))) return;
      const r = await post('/api/restore-many', { ids, to: p.path, lang: LANG });
      notify(t('ms.saved', { n: r.restored || 0, dir: `<span class="mono">${esc(p.path)}</span>` }) + (r.failed ? ' ' + t('g.failed', { n: r.failed }) : ''), !!r.failed);
      return;
    }
    if (!await confirmBox(t('ms.restoreTitle', { n: ids.length }), esc(t('ms.restoreText')), t('restore.ok'))) return;
    const r = await post('/api/restore-many', { ids, lang: LANG });
    notify(t('g.restored', { n: r.restored || 0 }) + (r.failed ? ' ' + t('g.failed', { n: r.failed }) : ''), !!r.failed);
    sound();
  };
}
function labelPicker(cur) {
  return `<span class="seg small lbl-seg">${['', ...LABELS].map(l => `<button type="button" data-lbl="${l}" class="${(cur || '') === l ? 'on' : ''}">${l ? `<i class="dot l-${l}"></i>${t('lbl.' + l)}` : t('lbl.none')}</button>`).join('')}</span>`;
}
async function noteMany(ids) {
  openModal(`<div class="m-head"><h3>${t('ms.noteTitle', { n: ids.length })}</h3><button class="icon-btn" data-close>${svg('x')}</button></div>
    <div class="m-body"><textarea id="mnText" rows="2" maxlength="500" placeholder="${esc(t('note.ph'))}" style="width:100%"></textarea>
      <div style="margin-top:8px">${labelPicker('')}</div><p class="hint">${t('note.keep')}</p></div>
    <div class="m-foot"><button class="btn" data-close>${t('btn.cancel')}</button><button class="btn primary" id="mnGo">${t('note.save')}</button></div>`, 'sm');
  let label = '';
  $('.lbl-seg').onclick = ev => { const b = ev.target.closest('[data-lbl]'); if (!b) return; label = b.dataset.lbl; $$('.lbl-seg button').forEach(x => x.classList.toggle('on', x === b)); };
  $('#mnGo').onclick = async () => {
    const r = await post('/api/note-many', { ids, text: $('#mnText').value.trim(), label: label || null });
    closeModal(); notify(r.ok ? t('ms.noted', { n: r.n }) : esc(errText(r)), !r.ok);
    loadEvents(); loadStats();
  };
}

/* ---------------------------------------------------------------- M1-15 note colour labels in the detail */
const _editNote = editNote;
editNote = function (e) {
  _editNote(e);
  const row = $('#dNote .editing .row'); if (!row) return;
  row.insertAdjacentHTML('beforebegin', `<div class="lbl-row">${labelPicker(e.label)}</div>`);
  let label = e.label || '';
  $('#dNote .lbl-seg').onclick = ev => { const b = ev.target.closest('[data-lbl]'); if (!b) return; label = b.dataset.lbl; $$('#dNote .lbl-seg button').forEach(x => x.classList.toggle('on', x === b)); };
  const save = async text => {
    const r = await post('/api/note', { id: e.id, text, label: label || null });
    if (!r.ok) { notify(esc(errText(r)), true); return; }
    e.note = r.note || null; e.label = r.label || null;
    renderDetail(e); loadStats(); renderList();
    notify(t(e.note || e.label ? 'note.saved' : 'note.removed'));
  };
  $('#noteSave').onclick = () => save($('#noteText').value.trim());
  $('#noteText').onkeydown = ev => {
    if (ev.key === 'Enter' && (ev.ctrlKey || !ev.shiftKey)) { ev.preventDefault(); save($('#noteText').value.trim()); }
    if (ev.key === 'Escape') { ev.stopPropagation(); renderDetail(e); }
  };
  if ($('#noteDel')) $('#noteDel').onclick = () => { label = ''; save(''); };
};
const _renderDetail = renderDetail;
renderDetail = function (e) {
  _renderDetail(e);
  if (!e) return;
  if (e.label) $('#dNote .d-note')?.insertAdjacentHTML('afterbegin', labelHTML(e.label));
  if (e.kind !== 'file' && e.kind) hashBadge(e);
  dragOut(e);
};

/* M1-14: drag the shown version out of the window (Chromium's DownloadURL drag; whether the WebView2 host lets
   Explorer accept it is checked by hand — see the plan). The copy is written by Windows where it is dropped. */
function dragOut(e) {
  const hash = e.kind === 'deleted' ? (e.has_prev_blob && e.prev_hash) : e.kind === 'file' ? null : (e.has_blob && e.hash);
  const icon = $('#detail .d-head .ficon'); if (!icon) return;
  const url = hash ? location.origin + blobUrl(hash, e.name) : e.kind === 'file' ? location.origin + fileUrl(e.path) : null;
  if (!url) return;
  icon.draggable = true;
  icon.title = t('drag.hint');
  icon.classList.add('drag-out');
  icon.ondragstart = ev => {
    ev.dataTransfer.effectAllowed = 'copy';
    ev.dataTransfer.setData('DownloadURL', `application/octet-stream:${e.name}:${url}`);
    ev.dataTransfer.setData('text/uri-list', url);
  };
}

/* ---------------------------------------------------------------- M2-21 short hash with the real algorithm */
function hashBadge(e) {
  const h = e.kind === 'deleted' ? e.prev_hash : e.hash; if (!h) return;
  const alg = h.length === 40 ? 'SHA-1' : 'SHA-256';
  $('#detail .d-meta')?.insertAdjacentHTML('beforeend', `<span class="dot"></span><button class="hash-badge" data-copy="${esc(h)}" title="${esc(t('hash.why', { alg }))}">${alg}: ${esc(h.slice(0, 8))}</button>`);
}

/* ---------------------------------------------------------------- M1-12 long runs of unchanged lines folded */
function foldRuns(rows, draw) {
  let out = '', run = [];
  const flush = () => {
    if (run.length > 5) {
      out += draw(run.slice(0, 2)) + `<button type="button" class="fold-btn" data-fold>${t('diff.fold', { n: run.length - 4 })}</button><div class="folded" hidden>${draw(run.slice(2, -2))}</div>` + draw(run.slice(-2));
    } else out += draw(run);
    run = [];
  };
  for (const r of rows) { if (r.k === ' ') run.push(r); else { flush(); out += draw([r]); } }
  flush();
  return out;
}
diffHTML = function (d) {
  const unit = UNIT[d.type] || 'line';
  const one = r => {
    const cls = r.k === '+' ? 'add' : r.k === '-' ? 'del' : '';
    const tx = r.s ? r.s.map(([c, x]) => c ? `<mark>${esc(x)}</mark>` : esc(x)).join('') : decorate(r.t, d.type);
    return `<div class="drow ${cls}" data-pi="${r.k === '+' ? r.b : r.a}"><span class="ln">${r.a ?? ''}</span><span class="ln">${r.b ?? ''}</span><span class="sg">${r.k === '+' ? '+' : r.k === '-' ? '−' : ''}</span><span class="tx">${tx || ' '}</span></div>`;
  };
  return d.hunks.map(h => `<div class="hunk-h"><span>${t('diff.hunk', { U: unitCap(unit), a: h.a, b: h.b })}</span><span>${t('diff.changedN', { n: h.rows.filter(r => r.k !== ' ').length })}</span></div>`
    + foldRuns(h.rows, rs => rs.map(one).join(''))).join('');
};
document.addEventListener('click', ev => {
  const b = ev.target.closest('[data-fold]'); if (!b) return;
  b.nextElementSibling.hidden = false; b.remove();
});

/* ---------------------------------------------------------------- M1-3 Space bar: quick look at the selected item */
document.addEventListener('keydown', async ev => {
  if (ev.key !== ' ' || ev.ctrlKey || ev.altKey || ev.target.matches?.('input, textarea, select, button, a')) return;
  if (!$('#modalBack').hidden) { if ($('#modal .quicklook')) { ev.preventDefault(); closeModal(); } return; }
  const it = currentItem(); if (!it) return;
  ev.preventDefault();
  openModal(`<div class="m-head"><h3>${esc(it.name)}</h3><span class="hint">${t('ql.hint')}</span><button class="icon-btn" data-close>${svg('x')}</button></div><div class="m-body quicklook" id="qlBody">${loadingHTML()}</div>`, 'upd');
  const body = $('#qlBody');
  const hash = it.kind === 'deleted' ? it.prev_hash : it.kind === 'file' ? null : it.hash;
  const r = hash ? await get('/api/content', { hash, ext: it.ext }) : await get('/api/current', { path: it.path });
  if (!$('#qlBody')) return;
  if (!r.ok) { body.innerHTML = noteHTML(t('ql.none'), true); return; }
  const blob = hash ? (it.kind === 'deleted' ? it.has_prev_blob : it.has_blob) : true;
  renderContent(body, r.content, blob ? (hash ? blobUrl(hash, it.name) : fileUrl(it.path)) : null, '', hash ? (blob ? mediaFromHash(hash) : null) : mediaFromPath(it.path));
});

/* ---------------------------------------------------------------- Clean up: kinds of big files, Downloads bands, map */
const BIG_KINDS = {
  video: /\.(mp4|mkv|mov|avi|wmv|flv|webm|m4v|ts|mts)$/i, archive: /\.(zip|rar|7z|iso|img|tar|gz|cab|tgz)$/i,
  vm: /\.(vmdk|vhd|vhdx|vdi|qcow2|avhdx|vmem|vmsn)$/i, db: /\.(db|sqlite3?|mdb|accdb|mdf|ldf|edb|realm|kdbx|db-wal)$/i,
  installer: /\.(exe|msi|msix|appx|msixbundle)$/i,
};
function decorateClean() {  // M1-8: chips over the biggest files
  const d = S.clean; if (!d || !d.big || d.state === 'scanning') return;
  const head = $$('#list .day').find(x => x.textContent === t('cl.big')); if (!head || $('#bigKinds')) return;
  const big = d.big.filter(f => !S.q || f.path.toLowerCase().includes(S.q.toLowerCase())).slice(0, 120);
  const count = k => big.filter(f => BIG_KINDS[k].test(f.path)).length;
  head.insertAdjacentHTML('afterend', `<div class="chips big-kinds" id="bigKinds">${['all', ...Object.keys(BIG_KINDS)].map(k =>
    `<button class="chip${(S.bigKind || 'all') === k ? ' on' : ''}" data-big-kind="${k}">${t('bk2.' + k)} <b>${num(k === 'all' ? big.length : count(k))}</b></button>`).join('')}</div>`);
  applyBigKind();
}
function applyBigKind() {
  const k = S.bigKind && S.bigKind !== 'all' ? BIG_KINDS[S.bigKind] : null;
  $$('#list .card.cl-file').forEach(c => { c.hidden = !!k && !k.test(c.dataset.clFile); });
}
$('#list').addEventListener('click', ev => {
  const b = ev.target.closest('[data-big-kind]'); if (!b) return;
  ev.stopPropagation();
  S.bigKind = b.dataset.bigKind;
  $$('#bigKinds .chip').forEach(x => x.classList.toggle('on', x === b));
  applyBigKind();
}, true);

// S1.2: the space map coloured by how each folder changed (grew / shrank / stable), with the numbers
const _spaceGridHTML = spaceGridHTML;
spaceGridHTML = function (d) {
  let html = _spaceGridHTML(d); if (!html) return html;
  const on = !!S.heatOn, h = S.heat && S.heat.ready && S.heat.drive === S.cleanDrive ? S.heat : null;
  const tog = `<span class="seg small"><button data-heat="0" class="${on ? '' : 'on'}">${t('heat.size')}</button><button data-heat="1" class="${on ? 'on' : ''}">${t('heat.change')}</button></span>`;
  html = html.replace(`<span class="hint">· ${t('cl.gridHint')}</span>`, `${tog} <span class="hint">· ${t(on ? 'heat.hint' : 'cl.gridHint')}</span>`);
  if (!on) return html;
  if (!h) return html.replace('<div class="cl-grid">', `<div class="hint">${S.heat && !S.heat.ready ? t('heat.notReady', { n: S.heat.scans || 0 }) : loadingHTML()}</div><div class="cl-grid">`);
  const f = h.folders, key = p => f[p] || f[p.replace(/\\$/, '')];
  html = html.replace(/(<button type="button" class="cl-cell[^"]*)("[^>]*data-cl-jump=")([^"]+)"([^>]*)>/g, (m, a, b, p, rest) => {
    const x = key(p.replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#39;/g, "'"));
    const cls = x ? ' heat-' + x.trend : ' heat-none';
    const tip = x ? ` · ${x.delta >= 0 ? '+' : '−'}${fmtSize(Math.abs(x.delta))}` : '';
    return `${a}${cls}${b}${p}"${rest.replace(/title="([^"]*)"/, (q, tt) => `title="${tt}${tip}"`)} data-heat-d="${x ? (x.delta >= 0 ? '+' : '−') + fmtSize(Math.abs(x.delta)) : ''}">`;
  });
  const legend = `<div class="heat-legend"><span class="heat-k heat-grew"><i></i>${t('heat.grew')}</span><span class="heat-k heat-shrank"><i></i>${t('heat.shrank')}</span><span class="heat-k heat-stable"><i></i>${t('heat.stable')}</span>
    <span class="hint">${t('heat.span', { a: fmtFull(h.from), b: fmtFull(h.to) })}</span></div>`;
  return html.replace('<div class="cl-grid">', legend + '<div class="cl-grid heat">');
};
$('#detail').addEventListener('click', async ev => {
  const b = ev.target.closest('[data-heat]'); if (!b || S.mode !== 'clean') return;
  ev.stopPropagation();
  S.heatOn = b.dataset.heat === '1';
  if (S.heatOn && (!S.heat || S.heat.drive !== S.cleanDrive)) {
    renderCleanOverview();
    S.heat = await get('/api/clean/heat', { drive: S.cleanDrive, days: 7 }).catch(() => null);
    if (S.heat) S.heat.drive = S.cleanDrive;
  }
  renderCleanOverview();
}, true);

// M1-6: right-click a block of the space map
$('#detail').addEventListener('contextmenu', ev => {
  const cell = ev.target.closest('.cl-cell[data-cl-jump]'); if (!cell || S.mode !== 'clean') return;
  ev.preventDefault();
  const path = cell.dataset.clJump, m = $('#ctxMenu');
  m.innerHTML = `<button data-gm="reveal">${svg('folder')}<span>${t('act.reveal')}</span></button>
    <button data-gm="copy">${svg('copy')}<span>${t('path.copy')}</span></button>
    <button data-gm="only">${svg('chart')}<span>${t('gm.only')}</span></button>
    <button data-gm="rescan">${svg('restore')}<span>${t('gm.rescan')}</span></button>`;
  m.hidden = false;
  m.style.left = Math.min(ev.clientX, innerWidth - m.offsetWidth - 8) + 'px';
  m.style.top = Math.min(ev.clientY, innerHeight - m.offsetHeight - 8) + 'px';
  m.onclick = c => {
    const b = c.target.closest('[data-gm]'); if (!b) return;
    m.hidden = true;
    if (b.dataset.gm === 'reveal') post('/api/clean/reveal', { path });
    else if (b.dataset.gm === 'copy') navigator.clipboard.writeText(path).then(() => notify(t('key.copied', { path: `<span class="mono">${esc(path)}</span>` })));
    else if (b.dataset.gm === 'only') { S.cleanFolder = path; loadClean(); }
    else loadClean(true);
  };
});

// M2-14: before emptying the Recycle Bin, its size and what was put there recently
const _emptyBinConfirm = emptyBinConfirm;
emptyBinConfirm = async function () {
  _emptyBinConfirm();
  const body = $('#modal .m-body'); if (!body) return;
  body.insertAdjacentHTML('beforeend', `<div id="binPeek">${loadingHTML()}</div>`);
  const r = await get('/api/clean/bin-peek', { drive: S.cleanDrive }).catch(() => null);
  const el = $('#binPeek'); if (!el) return;
  if (!r || !r.ok) { el.remove(); return; }
  el.innerHTML = `<p><b>${t('bin.total', { size: fmtSize(r.size), n: num(r.count) })}</b></p>` + (r.recent_n ? noteHTML(`${t('bin.recent', { n: r.recent_n })}<ul class="bin-recent">${r.recent.map(x =>
    `<li>${svg(x.dir ? 'folder' : 'note')}<span class="mono">${esc(x.name)}</span> <span class="hint">${esc(fmtFull(x.deleted))}${x.size ? ' · ' + fmtSize(x.size) : ''}</span></li>`).join('')}</ul>`, true) : '');
};

/* ---------------------------------------------------------------- S5.2 a deletion's notification opens its Restore */
const _openFromHash = openFromHash;
openFromHash = async function () {
  const m = /^#restore=(\d+)$/.exec(location.hash);
  if (!m) return _openFromHash();
  history.replaceState(null, '', location.pathname);
  const e = await get('/api/event', { id: m[1] }).catch(() => null);
  if (!e || e.error) return;
  S.byId.set(e.id, e);
  if (S.mode !== 'changes') setMode('changes');
  select(e.id);
  showRestore(e, 'prev');
};
window.addEventListener('hashchange', () => { if (location.hash.startsWith('#restore=')) openFromHash(); });

/* ---------------------------------------------------------------- M1-19 a short system sound when work is done */
function sound() { if (P.sound !== false) hostMessage({ cmd: 'beep' }); }
const _cleanResult = cleanResult;
cleanResult = function (res) { _cleanResult(res); sound(); };

/* ---------------------------------------------------------------- Settings: the 2.7.0 preferences */
const PREF_UI = [  // [key, kind, values]
  ['notify_deleted', 'switch'], ['notify_lowdisk', 'switch'], ['notify_changes', 'switch'],
  ['restore_suffix', 'seg', ['time', 'n', 'tag']], ['time_mode', 'seg', ['rel', 'abs']], ['dblclick', 'seg', ['open', 'reveal', 'details']],
  ['split', 'seg', ['auto', 'side', 'stack']], ['zoom', 'seg', [100, 110, 125, 150]], ['hotkey', 'seg', ['ctrl+alt+z', 'ctrl+shift+alt+z', 'off']],
  ['topmost', 'switch'], ['compact', 'switch'], ['sound', 'switch'], ['animations', 'switch'], ['search_history', 'switch'], ['clipboard_hint', 'switch'],
];
function prefRow([k, kind, vals]) {
  const label = `<span><b>${t('pf.' + k)}</b><span class="hint">${t('pf.' + k + 'Hint')}</span></span>`;
  if (kind === 'switch') return `<label class="switch-row"><input type="checkbox" data-pref="${k}" ${P[k] ? 'checked' : ''}><span class="switch"></span>${label}</label>`;
  return `<div class="quit-row">${label}<span class="seg">${vals.map(v => `<button data-pref="${k}" data-v="${v}" class="${String(P[k]) === String(v) ? 'on' : ''}">${t('pf.' + k + '.' + String(v).replace(/\+/g, '_'))}</button>`).join('')}</span></div>`;
}
const _openSettings = openSettings;
openSettings = async function () {
  await _openSettings();
  await loadPrefs();
  const box = $('#modal .m-body'); if (!box) return;
  const notifyRow = $('#notifySeg')?.closest('.quit-row');
  if (notifyRow) notifyRow.outerHTML = `<div class="pref-notify">${PREF_UI.slice(0, 3).map(prefRow).join('')}</div>`;
  $('#diagBox')?.insertAdjacentHTML('beforebegin', `<details class="diag adv" id="prefBox"><summary>${t('pf.title')}</summary>${PREF_UI.slice(3).map(prefRow).join('')}
    <div class="quit-row"><span><b>${t('sc.title')}</b><span class="hint">${t('sc.hint')}</span></span><button class="btn sm" id="deskLnk">${svg('plus')}${t('sc.btn')}</button></div></details>`);
  $('#diagBox')?.insertAdjacentHTML('beforeend', `<div class="row" style="margin:8px 0"><button class="btn sm" id="bundleBtn">${svg('download')}${t('db.btn')}</button><span class="hint">${t('db.hint')}</span></div>`);
  box.addEventListener('click', async ev => {
    const b = ev.target.closest('button[data-pref]'); if (!b) return;
    const v = isNaN(+b.dataset.v) ? b.dataset.v : +b.dataset.v;
    await setPref(b.dataset.pref, v);
    $$(`button[data-pref="${b.dataset.pref}"]`, box).forEach(x => x.classList.toggle('on', x === b));
    if (b.dataset.pref === 'time_mode') renderList();
  });
  box.addEventListener('change', ev => { const c = ev.target.closest('input[data-pref]'); if (c) setPref(c.dataset.pref, c.checked); });
  $('#bundleBtn').onclick = bundleDialog;
  $('#deskLnk').onclick = async () => { const r = await post('/api/desktop-shortcut').catch(() => ({})); notify(r.ok ? t(r.existed ? 'sc.existed' : 'sc.done') : esc(errText(r)), !r.ok); };
};

// M1-20: the support bundle, shown before it is saved
async function bundleDialog() {
  const r = await get('/api/diag-bundle').catch(() => null); if (!r || !r.ok) return;
  openModal(`<div class="m-head"><h3>${t('db.title')}</h3><button class="icon-btn" data-close>${svg('x')}</button></div>
    <div class="m-body"><p class="hint">${t('db.lead')}</p>${Object.entries(r.files).map(([n, x]) => `<details class="diag"><summary class="mono">${esc(n)} · ${fmtSize(x.length)}</summary><pre class="diag-log">${esc(x.slice(0, 20000))}</pre></details>`).join('')}</div>
    <div class="m-foot"><button class="btn" data-close>${t('btn.cancel')}</button><button class="btn primary" id="dbSave">${svg('download')}${t('db.save')}</button></div>`, 'upd');
  $('#dbSave').onclick = async () => {
    const s = await post('/api/diag-bundle').catch(() => ({}));
    if (s.code === 'cancelled') return;
    closeModal();
    notify(s.ok ? t('db.saved', { path: `<span class="mono">${esc(s.path)}</span>` }) : esc(errText(s)), !s.ok);
  };
}

/* ---------------------------------------------------------------- M2-10 click a time to switch the format */
$('#list').addEventListener('click', ev => {
  const tm = ev.target.closest('.time'); if (!tm || ev.ctrlKey || ev.shiftKey) return;
  ev.stopPropagation();
  setPref('time_mode', P.time_mode === 'abs' ? 'rel' : 'abs').then(() => { renderList(); highlight(); });
}, true);

$('#settingsBtn').onclick = openSettings;  // app.js bound the earlier function
loadPrefs().then(() => {
  if (!P.seen_upto) get('/api/events', { limit: 1 }).then(r => { if (r.events[0]) setPref('seen_upto', r.events[0].id); }).catch(() => {});
});

/* ================================================================ batch 2: data put together */

/* S1.1: the space map as it was 7 / 14 / 30 days ago (kept full scans), differences outlined */
const _gridB2 = spaceGridHTML;
spaceGridHTML = function (d) {
  const days = S.playDays || 0;
  const seg = `<span class="seg small" id="playSeg">${[0, 7, 14, 30].map(n => `<button data-play="${n}" class="${days === n ? 'on' : ''}">${t(n ? 'pb.ago' : 'pb.now', { n })}</button>`).join('')}</span>`;
  const h = S.play && S.play.drive === S.cleanDrive && S.play.days === days ? S.play : null;
  if (!days || !h || !h.ready) {
    let html = _gridB2(d);
    if (!html) return html;
    const note = days && h && !h.ready ? `<div class="hint">${t('pb.none')}</div>` : days && !h ? `<div class="hint">${loadingHTML()}</div>` : '';
    return html.replace('<div class="cl-grid', `<div class="pb-bar">${seg}</div>${note}<div class="cl-grid`);
  }
  const sz = p => h.sizes[p] ?? h.sizes[p.replace(/\\$/, '')];
  const then = {
    ...d, size: sz(d.folder || d.drive) || d.size,
    folders: (d.folders || []).map(f => ({ ...f, now: f.size, size: sz(f.path) || 0, sub: (f.sub || []).map(x => ({ ...x, now: x.size, size: sz(x.path) || 0 })).filter(x => x.size) }))
      .filter(f => f.size).sort((a, b) => b.size - a.size),
  };
  const nowOf = {};
  (d.folders || []).forEach(f => { nowOf[f.path] = f.size; (f.sub || []).forEach(x => { nowOf[x.path] = x.size; }); });
  let html = _spaceGridHTML(then) || `<div class="field"><div class="cl-grid"></div></div>`;
  html = html.replace(/(<button type="button" class="cl-cell[^"]*)("[^>]*data-cl-jump=")([^"]+)"([^>]*)>/g, (m, a, b, p, rest) => {
    const path = p.replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#39;/g, "'");
    const was = sz(path) || 0, now = nowOf[path] ?? 0;
    const diff = Math.abs(now - was) > Math.max(50 * 2 ** 20, was * 0.1);
    return `${a}${diff ? ' pb-diff' : ''}${b}${p}"${rest.replace(/title="([^"]*)"/, (q, tt) => `title="${tt}
${esc(t('pb.nowVs', { now: fmtSize(now), then: fmtSize(was) }))}"`)}>`;
  });
  const lead = `<div class="hint">${t(h.exact ? 'pb.lead' : 'pb.nearest', { when: fmtFull(h.at), back: h.days_back })} · <span class="pb-key"><i></i>${t('pb.changed')}</span></div>`;
  return html.replace('<div class="cl-grid', `<div class="pb-bar">${seg}</div>${lead}<div class="cl-grid`);
};
$('#detail').addEventListener('click', async ev => {
  const b = ev.target.closest('[data-play]'); if (!b || S.mode !== 'clean') return;
  ev.stopPropagation();
  S.playDays = +b.dataset.play;
  if (S.playDays) S.heatOn = false;
  renderCleanOverview();
  if (S.playDays) {
    const r = await get('/api/clean/space-at', { drive: S.cleanDrive, days: S.playDays }).catch(() => null);
    S.play = r ? { ...r, drive: S.cleanDrive, days: S.playDays } : null;
    if (S.mode === 'clean' && !S.cleanSel) renderCleanOverview();
  }
}, true);

/* S1.3: "full in about N–M days" — only with 7+ days of steady data; never a notification */
const _overviewB2 = renderCleanOverview;
renderCleanOverview = function () {
  _overviewB2();
  const d = S.clean; if (!d) return;
  const f = S.forecast && S.forecast.drive === d.drive ? S.forecast : null;
  if (!f) {
    get('/api/clean/forecast', { drive: d.drive }).then(r => { S.forecast = { ...r, drive: d.drive }; if (r.show && S.mode === 'clean' && !S.cleanSel) renderCleanOverview(); }).catch(() => {});
  } else if (f.show && (!d.folder || d.folder === d.drive)) {
    $('#detail .cl-hero-text')?.insertAdjacentHTML('beforeend', `<div class="cl-forecast" title="${esc(t('fc.why', { n: f.days }))}">${svg('clock')} ${t('fc.text', { lo: f.lo, hi: f.hi, per: fmtSize(f.per_day) })}</div>`);
  }
};

/* S2.1: plain-language search in Changes -> filters shown as chips (each can be taken off); else as typed */
const _rangeBounds = rangeBounds;
rangeBounds = function () {
  if (S.day && S.day.until) return [S.day.since, S.day.until];
  return _rangeBounds();
};
const _applyFilters = applyFilters;
applyFilters = async function () {
  if (S.mode === 'changes' && S.q && S.q !== S.nlSeen && !S.nlBusy) {
    S.nlBusy = true;
    const typed = S.q;
    const r = await get('/api/nl', { q: typed }).catch(() => null);
    S.nlBusy = false;
    S.nlSeen = typed;
    if (r && r.chips && r.chips.length) {
      for (const c of r.chips) {
        if (c.type === 'kind') S.kinds.add(c.value);
        else if (c.type === 'cat') S.cats.add(c.value);
        else if (c.type === 'folder') S.folder = c.value;
        else if (c.type === 'time') {
          if (['today', 'yesterday'].includes(c.value)) { S.range = c.value; S.day = null; }
          else S.day = { since: c.since, until: c.until || Date.now() / 1000 + 60, label: t('nl.' + c.value, { n: c.n }) };
        }
      }
      S.q = S.nlSeen = r.rest; $('#q').value = r.rest;
      S.nlUnderstood = typed;
      notify(t('nl.understood', { q: esc(typed) }));
    }
  }
  _applyFilters();
};
const _loadEventsB2 = loadEvents;
loadEvents = async function (append) {
  await _loadEventsB2(append);
  if (!append && S.mode === 'changes' && S.q && !S.events.length && S.nlOffered !== S.q) {  // fallback: inside the documents (FTS5)
    S.nlOffered = S.q;
    const q = S.q;
    notifyAction(t('nl.fallback', { q: esc(q) }), t('nl.inside'), () => { S.smode = 'content'; setMode('files'); S.q = q; $('#q').value = q; loadFiles(); }, 12000);
  }
};

/* S2.2: what changed in the structure of a Word / Markdown / PowerPoint / Excel file, above its diff */
const _diffTabB2 = renderDiffTab;
renderDiffTab = async function (e, body, live) {
  await _diffTabB2(e, body, live);
  if (e.kind !== 'modified' || !live()) return;
  const r = await get('/api/diff-summary', { id: e.id }).catch(() => null);
  if (!r || !r.items || !r.items.length || !live()) return;
  const line = x => {
    switch (x.k) {
      case 'heading+': return t('ss.headAdd', { v: esc(x.v) });
      case 'heading-': return t('ss.headDel', { v: esc(x.v) });
      case 'slides': return t('ss.slides', { a: x.from, b: x.to });
      case 'slide+': return t('ss.slideAdd', { v: esc(x.v) });
      case 'slide-': return t('ss.slideDel', { v: esc(x.v) });
      case 'rows': return t('ss.rows', { a: x.add, d: x.del });
      case 'cells': return t('ss.cells', { c: x.changed, a: x.add, d: x.del });
      case 'xrows': return t('ss.xrows', { n: x.n });
      case 'num': return t('ss.num', { a: esc(x.from), b: esc(x.to) });
      case 'numMore': return t('ss.numMore', { n: x.n });
      default: return '';
    }
  };
  body.insertAdjacentHTML('afterbegin', `<div class="ss-box"><b>${t('ss.title')}</b><ul>${r.items.map(x => `<li>${line(x)}${x.times > 1 ? ` ×${x.times}` : ''}</li>`).join('')}</ul></div>`);
};

/* ================================================================ batch 3: the rest of the experience */

/* Changes: sort by size of change / how often, only big changes, in the Recycle Bin / only DeskTrace has it,
   mark all read (M2-7, M2-9, M2-11, M2-29) — one "View" menu next to the date range */
S.esort = 'time'; S.bigOnly = false; S.where = '';
const _eventParams = eventParams;
eventParams = function () {
  const p = _eventParams();
  if (S.esort !== 'time') p.sort = S.esort;
  if (S.bigOnly) p.big = 1;
  if (S.where) p[S.where] = 1;
  return p;
};
const _matches = matches;
matches = function (e) {  // a live change joins the list only if it passes the extra filters too
  if (!_matches(e)) return false;
  if (S.bigOnly && Math.abs((e.size || 0) - (e.old_size || 0)) < 1024) return false;
  if (S.where) return false;  // "in the Recycle Bin" / "only DeskTrace has it" are decided by the service: reload
  return S.esort === 'time';
};
const _loadEventsB3 = loadEvents;
loadEvents = async function (append) {
  if (append && S.esort !== 'time') {  // sorted lists page by offset, not by id
    if (S.loadingMore) return;
    S.loadingMore = true;
    const r = await get('/api/events', { limit: 150, offset: S.events.length, ...eventParams() }).finally(() => { S.loadingMore = false; });
    r.events.forEach(e => S.byId.set(e.id, e));
    S.events = S.events.concat(r.events); S.more = r.more;
    renderList(); return;
  }
  return _loadEventsB3(append);
};
const _groupEvents = groupEvents;
groupEvents = function (events) { return S.esort === 'time' ? _groupEvents(events) : events; };  // no bulk cards in a sorted list
function viewMenuHTML() {
  const opt = (k, v, on) => `<button data-vm="${k}" data-v="${v}" class="${on ? 'on' : ''}">${on ? svg('check') : '<i class="nochk"></i>'}<span>${t('vm.' + k + '.' + v)}</span></button>`;
  return [['time', 'size', 'freq'].map(v => opt('sort', v, S.esort === v)).join(''), '<hr>', opt('big', '1', S.bigOnly), '<hr>',
    ['', 'inbin', 'snaponly'].map(v => opt('where', v || 'all', S.where === v)).join(''), '<hr>',
    `<button data-vm="read" data-v="1">${svg('check')}<span>${t('vm.read')}</span></button>`].join('');
}
(function addViewMenu() {
  const tools = $('#changesTools'); if (!tools) return;
  tools.querySelector('.spacer')?.insertAdjacentHTML('beforebegin', `<span class="lang-wrap view-wrap"><button class="btn sm" id="viewBtn" aria-haspopup="menu">${svg('menu')}<span id="viewLbl"></span></button>
    <div class="menu" id="viewMenu" role="menu" hidden></div></span>`);
  const lbl = () => { $('#viewLbl').textContent = t('vm.btn') + (S.esort !== 'time' || S.bigOnly || S.where ? ' •' : ''); };
  lbl();
  const _applyStaticVM = applyStatic;  // follow a change of language
  applyStatic = function () { _applyStaticVM(); lbl(); const c = $('.q-clear'); if (c) c.title = t('rq.clearQ'); };
  $('#viewBtn').onclick = ev => {
    ev.stopPropagation();
    const m = $('#viewMenu');
    m.innerHTML = viewMenuHTML(); m.hidden = !m.hidden;
    if (!m.hidden) {  // the toolbar clips its children: the menu floats over the page, under the button
      if (m.parentElement !== document.body) document.body.append(m);
      const r = ev.currentTarget.getBoundingClientRect();
      m.style.right = 'auto';
      m.style.position = 'fixed'; m.style.top = r.bottom + 4 + 'px';
      const page = document.body.getBoundingClientRect();
      const vw = Math.max(document.documentElement.clientWidth, innerWidth, page.width), vh = Math.max(document.documentElement.clientHeight, innerHeight, page.height);
      m.style.left = Math.max(8, Math.min(vw - m.offsetWidth - 8, r.right - m.offsetWidth)) + 'px';
      m.style.maxHeight = Math.max(160, vh - r.bottom - 16) + 'px'; m.style.overflowY = 'auto';
    }
  };
  $('#viewMenu').onclick = async ev => {
    const b = ev.target.closest('[data-vm]'); if (!b) return;
    ev.stopPropagation();
    const k = b.dataset.vm, v = b.dataset.v;
    if (k === 'read') {
      const top = S.events.reduce((m, e) => Math.max(m, e.id), +(P.seen_upto || 0));
      await setPref('seen_upto', top); $('#viewMenu').hidden = true; renderList(); return;
    }
    if (k === 'sort') S.esort = v; else if (k === 'big') S.bigOnly = !S.bigOnly; else S.where = v === 'all' ? '' : v;
    $('#viewMenu').innerHTML = viewMenuHTML(); lbl();
    S.sel = null; loadEvents();
  };
  document.addEventListener('click', ev => { if (!ev.target.closest('.view-wrap') && !ev.target.closest('#viewMenu')) $('#viewMenu').hidden = true; });
})();

/* M1-5: clear the search, and the last 5 searches as chips (this window only; off in Settings) */
(function searchHistory() {
  const q = $('#q'); if (!q) return;
  const load = () => { try { return JSON.parse(store('dw-recent-q') || '[]'); } catch { return []; } };
  const box = document.createElement('div'); box.className = 'recent-q menu'; box.hidden = true; q.closest('.search').append(box);
  const draw = () => {
    const list = P.search_history === false ? [] : load();
    box.innerHTML = list.length ? `${list.map(x => `<button data-rq="${esc(x)}">${svg('clock')}<span>${esc(x)}</span></button>`).join('')}<hr><button data-rq-clear>${svg('x')}<span>${t('rq.clear')}</span></button>` : '';
    box.hidden = !list.length || document.activeElement !== q || !!q.value;
  };
  q.addEventListener('focus', draw); q.addEventListener('input', draw);
  q.addEventListener('blur', () => setTimeout(() => { box.hidden = true; }, 150));
  q.addEventListener('change', () => {  // a search the user finished typing
    const v = q.value.trim(); if (!v || P.search_history === false) return;
    store('dw-recent-q', JSON.stringify([v, ...load().filter(x => x !== v)].slice(0, 5)));
  });
  box.addEventListener('mousedown', ev => {
    ev.preventDefault();
    const b = ev.target.closest('[data-rq]'); if (b) { q.value = b.dataset.rq; S.q = b.dataset.rq; S.nlSeen = null; applyFilters(); box.hidden = true; return; }
    if (ev.target.closest('[data-rq-clear]')) { store('dw-recent-q', '[]'); draw(); }
  });
  const clr = document.createElement('button'); clr.type = 'button'; clr.className = 'q-clear'; clr.title = t('rq.clearQ'); clr.innerHTML = svg('x');
  clr.onclick = () => { q.value = ''; S.q = ''; applyFilters(); q.focus(); };
  q.after(clr);
})();

/* M1-4: Ctrl + mouse wheel steps the text size 100 / 110 / 125 / 150 %, kept across restarts */
window.addEventListener('wheel', ev => {
  if (!ev.ctrlKey) return;
  ev.preventDefault();
  const steps = [100, 110, 125, 150], i = steps.indexOf(P.zoom || 100);
  const j = Math.max(0, Math.min(steps.length - 1, i + (ev.deltaY < 0 ? 1 : -1)));
  if (j !== i) setPref('zoom', steps[j]).then(() => notify(t('zoom.now', { n: steps[j] })));
}, { passive: false });

/* M2-23: double-click a change: open the file / show it in Explorer / open its details */
$('#list').addEventListener('dblclick', ev => {
  const card = ev.target.closest('.card'); if (!card || card.dataset.gkey || P.dblclick === 'open' || !P.dblclick) return;
  ev.stopImmediatePropagation();
  const it = card.dataset.path ? S.files.find(f => f.path === card.dataset.path) : S.byId.get(+card.dataset.id); if (!it) return;
  if (P.dblclick === 'reveal') act('reveal', it);
  else { $('#detail').classList.add('open'); switchTab('details'); }
}, true);

/* M1-11: hovering a version in the History tab shows its first lines or a thumbnail (never blocks scrolling) */
const hoverCache = new Map();
let hoverTimer = 0;
document.addEventListener('mouseover', ev => {
  const row = ev.target.closest('.h-item[data-hid]');
  clearTimeout(hoverTimer);
  if (!row) { $('#hoverPeek')?.remove(); return; }
  hoverTimer = setTimeout(async () => {
    const e = S.byId.get(+row.dataset.hid) || (S.histRows || []).find(x => x.id === +row.dataset.hid);
    const h = e && (e.kind === 'deleted' ? e.prev_hash : e.hash); if (!h) return;
    let html = hoverCache.get(h);
    if (!html) {
      if (WEB_IMG.test(e.name) && (e.has_blob || e.has_prev_blob)) html = `<img src="${blobUrl(h, e.name)}" alt="">`;
      else {
        const r = await get('/api/content', { hash: h, ext: e.ext }).catch(() => null);
        const lines = r && r.ok ? (r.content.preview || r.content.text || '') : '';
        html = lines ? `<pre>${esc(String(lines).split('\n').slice(0, 8).join('\n').slice(0, 600))}</pre>` : '';
      }
      hoverCache.set(h, html);
    }
    if (!html || !row.matches(':hover')) return;
    $('#hoverPeek')?.remove();
    const box = document.createElement('div'); box.id = 'hoverPeek'; box.className = 'hover-peek'; box.innerHTML = html;
    document.body.append(box);
    const r = row.getBoundingClientRect();
    box.style.left = Math.max(8, r.left - box.offsetWidth - 10) + 'px';
    box.style.top = Math.min(innerHeight - box.offsetHeight - 8, Math.max(8, r.top)) + 'px';
  }, 450);
}, { passive: true });
document.addEventListener('scroll', () => $('#hoverPeek')?.remove(), { passive: true, capture: true });

/* M2-3: code, JSON and logs with line numbers; hover a line to copy just that line (numbers are never copied) */
codeHTML = function (text, wrap) {
  const MAX = 5000;
  if (!text.trim()) return noteHTML(t('c.empty'));
  let lines = text.replace(/\r\n?/g, '\n').split('\n');
  const total = lines.length, cut = total > MAX;
  if (cut) lines = lines.slice(0, MAX);
  const tail = cut ? noteHTML(t('c.firstN', { a: num(MAX), b: num(total) })) : '';
  return `<div class="code-lines${wrap ? '' : ' nowrap'}">${lines.map((l, i) => `<div class="cl"><span class="n" aria-hidden="true">${i + 1}</span><span class="t">${esc(l) || ' '}</span><button type="button" class="cl-copy" title="${esc(t('code.copyLine'))}">${svg('copy')}</button></div>`).join('')}</div>` + tail;
};
document.addEventListener('click', ev => {
  const b = ev.target.closest('.cl-copy'); if (!b) return;
  const text = b.parentElement.querySelector('.t').textContent;
  navigator.clipboard.writeText(text === ' ' ? '' : text).then(() => { b.innerHTML = svg('check'); setTimeout(() => { b.innerHTML = svg('copy'); }, 1000); });
});

/* M2-4: the text view of a PDF: jump to a page; text can be selected and copied with Ctrl+C */
const _renderPdf = renderPdf;
renderPdf = function (body, c, raw, pre, preferText) {
  _renderPdf(body, c, raw, pre, preferText);
  const addJump = () => {
    const bar = $('.subbar', body); if (!bar || $('.pg-jump', bar) || !$$('.page', body).length) return;
    bar.insertAdjacentHTML('beforeend', `<span class="pg-jump">${t('pg.go')} <input type="number" min="1" max="${c.pages.length}" value="1"></span>`);
    $('.pg-jump input', bar).onchange = ev => { const p = $$('.page', body)[Math.max(0, Math.min(c.pages.length, +ev.target.value) - 1)]; p?.scrollIntoView({ block: 'start' }); };
  };
  addJump();
  new MutationObserver(addJump).observe(body, { childList: true });
};

/* M2-6: an archive's list says that only .zip is read */
const _renderContent = renderContent;
renderContent = function (body, c, raw, pre = '', media = null, opts = {}) {
  _renderContent(body, c, raw, pre, media, opts);
  if (c && c.type === 'archive') $('.subbar .meta', body)?.insertAdjacentHTML('afterend', `<span class="tag" title="${esc(t('zip.why'))}">${t('zip.only')}</span>`);
};

/* M2-2: Markdown / Word / PowerPoint "Document" view: step from change to change */
const _drawDiff = drawDiff;
drawDiff = async function (body, d, ctx) {
  await _drawDiff(body, d, ctx);
  const marks = $$('.rl-ins, .rl-del', body);
  if (!marks.length || !$('.paper.redline', body)) return;
  const sub = $('.subbar', body); if (!sub || $('.rl-nav', sub)) return;
  let k = 0;
  sub.insertAdjacentHTML('beforeend', `<span class="rl-nav"><button class="btn sm" data-rl="-1">‹</button><span class="meta" id="rlPos">1 / ${marks.length}</span><button class="btn sm" data-rl="1">›</button></span>`);
  sub.onclick = ev => {
    const b = ev.target.closest('[data-rl]'); if (!b) return;
    ev.stopPropagation();
    k = (k + +b.dataset.rl + marks.length) % marks.length;
    marks.forEach(m => m.classList.remove('rl-cur')); marks[k].classList.add('rl-cur');
    scrollToEl(marks[k], body); $('#rlPos').textContent = `${k + 1} / ${marks.length}`;
  };
};

/* M2-20: in the restore dialog, "Replace the file" shows its differences inline before anything happens */
const _showRestore = showRestore;
showRestore = async function (e, version, preferReplace) {
  await _showRestore(e, version, preferReplace);
  const opt = $('input[name=rpMode][value=replace]'); if (!opt || opt.disabled) return;
  const hash = version === 'prev' ? e.prev_hash : (e.hash || e.prev_hash);
  const d = await get('/api/compare', { a: 'current', b: hash, path: e.path, ext: e.ext }).catch(() => null);
  const lbl = opt.closest('.rp-opt'); if (!lbl || !d || !d.ok) return;
  const n = (d.hunks || []).length;
  lbl.insertAdjacentHTML('afterend', `<details class="rp-diff"><summary>${t(n ? 'rp.diffN' : 'rp.diffNone', { a: num(d.removed), b: num(d.added) })}</summary>
    ${n ? `<div class="diff">${diffHTML(d)}</div>` : ''}</details>`);
};

/* M2-18: "Save a copy to" Desktop / next to the original / Downloads / choose */
const _act = act;
act = async function (name, e, btn) {
  if (name === 'save-to') {
    const hash = e.kind === 'deleted' ? e.prev_hash : e.hash;
    const r = await post('/api/restore-as', { hash, name: e.name, ts: e.ts, dir: dirname(e.path), target: btn.dataset.target, path: e.path });
    if (r.cancelled) return;
    if (!r.ok) { notify(esc(errText(r)), true); return; }
    notifyAction(t('restore.done', { path: `<span class="mono" style="font-size:12px">${esc(r.path)}</span>` }), t('act.reveal'), () => post('/api/clean/reveal', { path: r.path }), 12000);
    sound(); return;
  }
  const r = await _act(name, e, btn);
  return r;
};
const _moreMenuHTML = moreMenuHTML;
moreMenuHTML = function (items) {
  const e = currentItem();
  const has = e && e.kind !== 'file' && (e.kind === 'deleted' ? e.has_prev_blob : e.has_blob);
  if (has) items = items.filter(Boolean).filter(x => !/data-act="restore-as"/.test(x)).concat(['desktop', 'beside', 'downloads', 'pick']
    .map(tg => `<button data-act="save-to" data-target="${tg}">${svg(tg === 'pick' ? 'folder' : 'copy')}<span>${t('st2.' + tg)}</span></button>`));
  if (e && e.kind === 'modified' && e.has_blob && e.has_prev_blob && ['text', 'code', 'markdown'].includes(e.cat))  // M2-17
    items = items.filter(Boolean).concat([`<a href="/api/patch?id=${e.id}" download>${svg('download')}<span>${t('patch.btn')}</span></a>`]);
  return _moreMenuHTML(items);
};

/* M2-12: a finished cleanup counts up what was freed (skipped with reduced motion) */
const _cleanResultB3 = cleanResult;
cleanResult = function (res) {
  _cleanResultB3(res);
  const h = $('#modal .m-head h3'); if (!h || reduceMotion()) return;
  const total = res.reduce((a, { r }) => a + (r.freed || 0), 0), t0 = performance.now();
  h.classList.add('roll');
  const step = now => { const k = Math.min(1, (now - t0) / 900); h.textContent = t('cl.resultTitle', { size: fmtSize(total * (1 - Math.pow(1 - k, 3))) }); if (k < 1) requestAnimationFrame(step); };
  requestAnimationFrame(step);
};

/* M1-7 / M1-9: scan time left as a range at a steady rate; the stale note offers "scan again now" */
const _renderClean = renderClean;
renderClean = function () {
  _renderClean();
  const d = S.clean; if (!d) return;
  const sum = $('#cleanSum');
  if (d.state === 'scanning' && d.expect_files && d.files > 2000 && d.seconds > 3) {
    const rate = d.files / d.seconds;
    S.etaRate = S.etaRate ? S.etaRate * 0.8 + rate * 0.2 : rate;  // smoothed: the range does not jump with each folder
    const left = Math.max(0, d.expect_files - d.files) / S.etaRate;
    sum.insertAdjacentHTML('beforeend', ` <span class="hint eta">${left < 5 ? t('eta.soon') : t('eta.left', { a: fmtDur(left * 0.8), b: fmtDur(left * 1.3), rate: num(Math.round(S.etaRate)) })}</span>`);
  } else if (d.state !== 'scanning') S.etaRate = 0;
  const stale = $('.cl-stale', sum);
  if (stale && !$('[data-cl-rescan-now]', sum)) stale.insertAdjacentHTML('afterend', ` <button class="btn sm primary" data-cl-rescan="" data-cl-rescan-now>${svg('restore')}${t('cl.rescanNow')}</button>`);
};
const fmtDur = s => s < 90 ? t('eta.s', { n: Math.max(1, Math.round(s)) }) : t('eta.m', { n: Math.round(s / 60) });

/* M1-10: a plain-text check-up of the drive to copy (paths can be shortened to folder names) */
const _overviewB3 = renderCleanOverview;
renderCleanOverview = function () {
  _overviewB3();
  const d = S.clean; if (!d || d.state === 'scanning' || (d.folder && d.folder !== d.drive)) return;
  $('#detail .cl-hero-text')?.insertAdjacentHTML('beforeend', `<div class="row cl-brief"><button class="btn sm" id="briefBtn">${svg('copy')}${t('brief.btn')}</button>
    <label class="chk"><input type="checkbox" id="briefRedact" ${store('dw-brief-redact') === '0' ? '' : 'checked'}> ${t('brief.redact')}</label>
    <button class="btn sm" id="freeBtn">${svg('check')}${t('fx.btn')}</button></div>`);
};
function checkupText(redact) {
  const d = S.clean, u = d.usage || {}, name = p => redact ? (basename(p) || p) : p;
  const items = (d.items || []).filter(x => ['delete', 'recycle'].includes(x.how));
  const lines = [t('brief.head', { d: d.drive.slice(0, 2), when: fmtFull(d.cached_at || d.finished || Date.now() / 1000) }),
    t('brief.space', { used: fmtSize(u.used), total: fmtSize(u.total), free: fmtSize(u.free) }), '', t('brief.top')];
  (d.folders || []).slice(0, 3).forEach((f, i) => lines.push(`  ${i + 1}. ${name(f.path)} — ${fmtSize(f.size)}`));
  const g = S.growth && S.growth.ready ? S.growth.items.slice(0, 3) : [];
  if (g.length) { lines.push('', t('brief.grew')); g.forEach(x => lines.push(`  + ${fmtSize(x.grew)}  ${name(x.path)}`)); }
  lines.push('', t('brief.can', { size: fmtSize(items.reduce((a, x) => a + x.size, 0)) }));
  items.slice(0, 6).forEach(x => lines.push(`  · ${t('cl.item.' + x.id)} — ${fmtSize(x.size)}`));
  lines.push('', t('brief.by', { v: VERSION }));
  return lines.join('\n');
}
$('#detail').addEventListener('click', ev => {
  if (ev.target.closest('#briefBtn')) {
    const red = $('#briefRedact').checked; store('dw-brief-redact', red ? '1' : '0');
    navigator.clipboard.writeText(checkupText(red)).then(() => notify(t('brief.copied')));
  }
  if (ev.target.closest('#freeBtn')) freeDialog();
});

/* M2-15: "free me X GB": ticks safe items only (caches, temporary files) until X is reached — never runs anything */
function freeDialog() {
  const safe = (S.clean.items || []).filter(x => x.level === 'safe' && x.how === 'delete').sort((a, b) => b.size - a.size);
  const most = safe.reduce((a, x) => a + x.size, 0);
  openModal(`<div class="m-head"><h3>${t('fx.title')}</h3><button class="icon-btn" data-close>${svg('x')}</button></div>
    <div class="m-body"><div class="row"><input type="number" id="fxGb" min="0.1" step="0.5" value="${Math.max(0.5, Math.min(5, Math.floor(most / 2 ** 30 * 10) / 10))}" style="width:90px"> GB
      <button class="btn sm" id="fxGo">${t('fx.pick')}</button></div><p class="hint">${t('fx.hint', { most: fmtSize(most) })}</p><div id="fxOut"></div></div>
    <div class="m-foot"><button class="btn" data-close>${t('btn.cancel')}</button><button class="btn primary" id="fxApply" disabled>${t('fx.apply')}</button></div>`, 'sm');
  let pick = [];
  $('#fxGo').onclick = () => {
    const want = +$('#fxGb').value * 2 ** 30;
    pick = []; let sum = 0;
    for (const x of safe) { if (sum >= want) break; pick.push(x); sum += x.size; }
    $('#fxOut').innerHTML = pick.length ? `<table class="kv-table">${pick.map(x => `<tr><td>${t('cl.item.' + x.id)}</td><td class="num">${fmtSize(x.size)}</td></tr>`).join('')}</table>
      <p><b>${t(sum >= want ? 'fx.enough' : 'fx.short', { size: fmtSize(sum) })}</b></p>` : `<p class="hint">${t('fx.none')}</p>`;
    $('#fxApply').disabled = !pick.length;
  };
  $('#fxGo').click();
  $('#fxApply').onclick = () => {
    S.cleanPick = new Set(pick.map(x => x.id)); closeModal(); renderList(); renderCleanOverview();
    notify(t('fx.ticked', { n: pick.length }));
  };
}

/* M2-27: a file path on the clipboard (only when switched on): offer its history; nothing is kept */
async function clipboardHint() {
  if (!P.clipboard_hint || document.hidden) return;
  const r = await get('/api/clipboard-path').catch(() => null);
  if (!r || !r.path || r.path === S.clipSeen) return;
  S.clipSeen = r.path;
  notifyAction(t('clip.found', { name: `<span class="mono">${esc(basename(r.path))}</span>` }), t('clip.show'), () => { setMode('files'); openFileByPath(r.path); }, 12000);
}
window.addEventListener('focus', clipboardHint);
document.addEventListener('visibilitychange', clipboardHint);

/* M2-30: a removable drive taken out while Clean up shows it: back to the system drive, no error page */
const _esB3 = connect;
connect = function () {
  _esB3();
  S.es.addEventListener('message', m => {
    let msg; try { msg = JSON.parse(m.data); } catch { return; }
    if (msg.type === 'drive-gone') {
      S.cleanDrives = (S.cleanDrives || []).filter(x => x.drive !== msg.drive);
      if (S.cleanDrive === msg.drive) { S.cleanDrive = null; S.clean = null; S.cleanFolder = null; S.cleanSel = null; S.cleanDrives = null; if (S.mode === 'clean') loadClean(); }
      notify(t('usb.gone', { d: esc(msg.drive.slice(0, 2)) }));
    }
    if (msg.type === 'lowdisk') notify(t('low.inWindow', { free: fmtSize(msg.free || 0) }), true);
  });
};
if (S.es) {  // already connected before this file loaded: listen on the open stream too
  S.es.addEventListener('message', m => {
    let msg; try { msg = JSON.parse(m.data); } catch { return; }
    if (msg.type === 'drive-gone' && S.cleanDrive === msg.drive) { S.cleanDrive = null; S.clean = null; S.cleanDrives = null; if (S.mode === 'clean') loadClean(); notify(t('usb.gone', { d: esc(msg.drive.slice(0, 2)) })); }
  });
}

/* restore by a single click also plays the sound (M1-19) */
const _postB3 = post;
post = async function (path, body) {
  const r = await _postB3(path, body);
  if (r && r.ok && (path === '/api/restore' || path === '/api/mass-restore')) sound();
  return r;
};

/* ================================================================ DeepSeek's proposal (F1–F12), inside the four entry points */

/* Settings › "Trust and history": overview (F2), retention preview (F3), activity (F1), weekly report (F5),
   restore from a backup folder (F4), mass-change alert (F6), per-folder limits (F10), scheduled cleanup (F11) */
const _openSettingsF = openSettings;
openSettings = async function () {
  await _openSettingsF();
  const anchor = $('#prefBox'); if (!anchor) return;
  anchor.insertAdjacentHTML('beforebegin', `<details class="diag adv" id="trustBox" open><summary>${t('tr.title')}</summary>
    <div id="ovCard">${loadingHTML()}</div>
    <div class="row tr-btns">
      <button class="btn sm" id="rpvBtn">${svg('clock')}${t('rpv.btn')}</button>
      <button class="btn sm" id="actBtn">${svg('note')}${t('al.btn')}</button>
      <button class="btn sm" id="wkBtn">${svg('chart')}${t('wk.btn')}</button>
      <button class="btn sm" id="bkrBtn">${svg('restore')}${t('bkr.btn')}</button></div>
    <div class="quit-row"><span><b>${t('ms6.title')}</b><span class="hint">${t('ms6.hint')}</span></span>
      <span class="row"><input type="number" id="massN" min="20" max="5000" value="${P.mass_n}" style="width:76px"> ${t('ms6.in')}
      <input type="number" id="massW" min="5" max="600" value="${P.mass_window}" style="width:64px"> ${t('ms6.sec')}</span></div>
    <div class="quit-row"><span><b>${t('ms6.quiet')}</b><span class="hint">${t('ms6.quietHint')}</span></span>
      <span class="seg">${[600, 3600, 86400].map(v => `<button data-pref="mass_quiet" data-v="${v}" class="${P.mass_quiet === v ? 'on' : ''}">${t('ms6.q' + v)}</button>`).join('')}</span></div>
    <label class="switch-row"><input type="checkbox" data-pref="weekly_report" ${P.weekly_report !== false ? 'checked' : ''}><span class="switch"></span>
      <span><b>${t('wk.note')}</b><span class="hint">${t('wk.noteHint')}</span></span></label>
    <div class="field"><label>${t('fr.title')}</label><div class="hint">${t('fr.hint')}</div><div id="frList"></div></div>
    <div class="field"><label>${t('ac.title')}</label><div class="hint">${t('ac.hint')}</div><div id="acBox"></div></div>
  </details>`);
  const s = await get('/api/settings');
  drawOverview(); drawFolderRules(s); drawAutoClean(s);
  const save = (k, v) => post('/api/settings', { [k]: v }).then(r => { if (r.ok) Object.assign(P, r.settings); return r; });
  $('#massN').onchange = ev => save('mass_n', +ev.target.value).then(r => { ev.target.value = r.settings.mass_n; });
  $('#massW').onchange = ev => save('mass_window', +ev.target.value).then(r => { ev.target.value = r.settings.mass_window; });
  $('#rpvBtn').onclick = retentionPreview;
  $('#actBtn').onclick = activityDialog;
  $('#wkBtn').onclick = weekDialog;
  $('#bkrBtn').onclick = backupRestoreDialog;
};

async function drawOverview() {
  const o = await get('/api/overview').catch(() => null); const el = $('#ovCard'); if (!o || !el) return;
  const why = Object.entries(o.why).filter(([, n]) => n);
  el.innerHTML = `<div class="ov-card">
    <div class="ov-big"><b>${num(o.kept)}</b> / ${num(o.files)} <span class="hint">${t('ov.kept')}</span></div>
    <div class="ov-bar"><i style="width:${o.files ? (o.kept / o.files * 100).toFixed(1) : 0}%"></i></div>
    ${why.length ? `<div class="ov-why">${t('ov.whyNot')} ${why.map(([k, n]) => `<button class="chip" data-ov="${k}" title="${esc(t('prot.' + k + 'Why'))}">${t('ov.' + k)} <b>${num(n)}</b></button>`).join('')}</div>` : `<div class="hint">${t('ov.allKept')}</div>`}
    <div class="hint">${t('ov.excluded', { n: o.excluded_rules })}</div>
    <div class="ov-week">${t('ov.week')} ${['lowdisk', 'nocopy', 'locked', 'mass'].map(k => `<span class="${o.week[k] ? 'warn-text' : ''}">${t('ov.w.' + k, { n: num(o.week[k]) })}</span>`).join(' · ')}</div>
    <div class="hint">${o.last_clean ? t('ov.lastClean', { when: fmtFull(o.last_clean.ts) }) : t('ov.noClean')} · ${o.last_backup ? t('ov.lastBackup', { when: fmtFull(o.last_backup.ts) }) : `<span class="warn-text">${t('ov.noBackup')}</span>`}</div></div>`;
  el.onclick = async ev => {
    const b = ev.target.closest('[data-ov]'); if (!b) return;
    closeModal(); setMode('files');
    const r = await get('/api/files-by-protection', { kind: b.dataset.ov });
    S.files = r.files; S.fileTotal = r.total; S.protFilter = b.dataset.ov; renderList();
    notify(t('ov.showing', { what: t('ov.' + b.dataset.ov), n: num(r.total) }));
  };
}

async function retentionPreview() {
  const r = await get('/api/retention-preview', { days: 7 }).catch(() => null); if (!r) return;
  openModal(`<div class="m-head"><h3>${t('rpv.title')}</h3><button class="icon-btn" data-close>${svg('x')}</button></div>
    <div class="m-body">${r.forever ? `<p>${t('rpv.forever')}</p>` : `<p><b>${t('rpv.lead', { n: num(r.n), size: fmtSize(r.bytes) })}</b></p>
      <p class="hint">${t('rpv.policy', { d: r.policy.keep_days || '∞', g: r.policy.max_gb || '∞' })} ${Object.keys(r.policy.folders).length ? t('rpv.ownRules', { n: Object.keys(r.policy.folders).length }) : ''}</p>
      <p class="hint">${t('rpv.protected', { n: num(r.protected) })}</p>
      ${r.items.length ? `<table class="kv-table rpv">${r.items.slice(0, 200).map(x => `<tr><td>${kbadge(x.kind)}</td><td class="mono" title="${esc(x.path)}">${esc(x.name)}</td><td>${esc(fmtFull(x.ts))}</td><td>${t('rpv.goes', { when: new Date(x.goes_on * 1000).toLocaleDateString(loc()) })}</td><td class="num">${x.size ? fmtSize(x.size) : ''}</td></tr>`).join('')}</table>` : ''}`}</div>
    <div class="m-foot"><button class="btn left" id="rpvAdjust">${t('rpv.adjust')}</button><button class="btn" data-close>${t('btn.close')}</button>
      ${r.n ? `<button class="btn danger" id="rpvNow">${t('rpv.now')}</button>` : ''}</div>`, 'upd');
  $('#rpvAdjust').onclick = () => { closeModal(); openSettings().then(() => $('#keepDays')?.focus()); };
  if ($('#rpvNow')) $('#rpvNow').onclick = async () => {
    if (!await confirmBox(t('rpv.nowTitle'), esc(t('rpv.nowText')), t('rpv.now'), true)) return;
    const c = await post('/api/cleanup'); notify(t('clean.done', { n: num(c.events), size: fmtSize(c.freed) })); loadStats();
  };
}

async function activityDialog(filter = '') {
  const r = await get('/api/actions', { limit: 300, ...(filter ? { source: filter } : {}) }).catch(() => null); if (!r) return;
  openModal(`<div class="m-head"><h3>${t('al.title')}</h3><button class="icon-btn" data-close>${svg('x')}</button></div>
    <div class="m-body"><div class="row"><span class="seg small" id="alSeg">${['', 'user', 'auto'].map(v => `<button data-al="${v}" class="${filter === v ? 'on' : ''}">${t('al.src.' + (v || 'all'))}</button>`).join('')}</span>
      <span class="hint">${t('al.count', { n: num(r.total) })}</span></div>
      <table class="kv-table al">${r.items.map(x => `<tr><td>${esc(fmtFull(x.ts))}</td><td>${t('al.a.' + x.action) !== 'al.a.' + x.action ? t('al.a.' + x.action) : esc(x.action)}</td>
        <td class="mono" title="${esc(x.target)}">${esc(x.target.length > 70 ? '…' + x.target.slice(-70) : x.target)}</td><td class="${x.result === 'ok' ? '' : 'warn-text'}">${esc(x.result)}</td>
        <td>${x.size ? fmtSize(x.size) : ''}</td><td class="hint">${t('al.src.' + x.source)}</td></tr>`).join('') || `<tr><td>${t('al.none')}</td></tr>`}</table>
      <p class="hint">${t('al.hint')}</p></div>
    <div class="m-foot"><button class="btn left danger" id="alClear">${t('al.clear')}</button><a class="btn" href="/api/actions.csv" download>${svg('download')}${t('al.csv')}</a><button class="btn primary" data-close>${t('btn.close')}</button></div>`, 'upd');
  $('#alSeg').onclick = ev => { const b = ev.target.closest('[data-al]'); if (b) activityDialog(b.dataset.al); };
  $('#alClear').onclick = async () => { if (await confirmBox(t('al.clearTitle'), esc(t('al.clearText')), t('al.clear'), true)) { await post('/api/actions/clear'); activityDialog(); } else activityDialog(); };
}

async function weekDialog() {
  const r = await get('/api/report/week', { lang: LANG }).catch(() => null); if (!r) return;
  openModal(`<div class="m-head"><h3>${t('wk.title')}</h3><button class="icon-btn" data-close>${svg('x')}</button></div>
    <div class="m-body"><div class="wk-grid">${[['changes', r.changes], ['versions', r.versions], ['restores', r.restores], ['freed', fmtSize(r.freed)], ['unusual', r.unusual]]
      .map(([k, v]) => `<div><b>${typeof v === 'number' ? num(v) : v}</b><span class="hint">${t('wk.' + k)}</span></div>`).join('')}</div>
      <label>${t('wk.top')}</label>${r.top.map(x => `<div class="mono wk-top">${esc(x.folder)} — ${num(x.n)}</div>`).join('') || `<div class="hint">${t('wk.none')}</div>`}
      <p class="hint">${t('wk.local')}</p></div>
    <div class="m-foot"><button class="btn" id="wkMd">${svg('download')}${t('wk.md')}</button><button class="btn primary" data-close>${t('btn.close')}</button></div>`, 'upd');
  $('#wkMd').onclick = () => {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([r.markdown], { type: 'text/markdown' }));
    a.download = `DeskTrace ${new Date(r.to * 1000).toISOString().slice(0, 10)}.md`; a.click();
  };
}

async function backupRestoreDialog() {
  const c = await post('/api/backup-check').catch(() => ({}));
  if (c.code === 'cancelled') return;
  if (!c.ok) { notify(esc(t('bkr.err.' + (c.code || 'notBackup'), { v: c.needs || '' })), true); return; }
  openModal(`<div class="m-head"><h3>${t('bkr.title')}</h3><button class="icon-btn" data-close>${svg('x')}</button></div>
    <div class="m-body"><table class="kv-table"><tr><td>${t('bkr.where')}</td><td class="mono">${esc(c.root)}</td></tr>
      <tr><td>${t('bkr.made')}</td><td>${esc(fmtFull(c.made))}${c.made_by ? ' · DeskTrace ' + esc(c.made_by) : ''}</td></tr>
      <tr><td>${t('bkr.content')}</td><td>${t('bkr.counts', { e: num(c.events), s: num(c.snapshots), db: fmtSize(c.db_bytes) })}</td></tr>
      <tr><td>${t('bkr.span')}</td><td>${c.first ? `${esc(fmtFull(c.first))} → ${esc(fmtFull(c.last))}` : '—'}</td></tr>
      <tr><td>${t('bkr.check')}</td><td class="${c.bad ? 'warn-text' : ''}">${t(c.bad ? 'bkr.checkBad' : 'bkr.checkOk', { n: c.checked, bad: c.bad })}</td></tr></table>
      <label class="rp-opt"><input type="radio" name="bkMode" value="merge" checked> <span><b>${t('bkr.merge')}</b><br><span class="hint">${t('bkr.mergeWhy')}</span></span></label>
      <label class="rp-opt"><input type="radio" name="bkMode" value="replace"> <span><b>${t('bkr.replace')}</b><br><span class="hint">${t('bkr.replaceWhy')}</span></span></label></div>
    <div class="m-foot"><button class="btn" data-close>${t('btn.cancel')}</button><button class="btn primary" id="bkGo">${t('bkr.go')}</button></div>`, 'sm');
  $('#bkGo').onclick = async () => {
    const mode = $('input[name=bkMode]:checked').value;
    $('#bkGo').disabled = true; $('#bkGo').innerHTML = `<span class="spin"></span> ${t('bkr.working')}`;
    const r = await post('/api/backup-restore', { path: c.root, mode }).catch(() => ({}));
    if (!r.ok) { closeModal(); notify(esc(t('bkr.err.' + (r.code || 'mergeFailed'), { v: '' }) + (r.why ? ' ' + r.why : '')), true); return; }
    if (mode === 'merge') {
      openModal(`<div class="m-head"><h3>${t('bkr.doneTitle')}</h3></div><div class="m-body"><table class="kv-table">
        <tr><td>${t('bkr.added')}</td><td>${num(r.added)} (${t('bkr.notes', { n: r.notes })})</td></tr><tr><td>${t('bkr.copied')}</td><td>${num(r.copied)}</td></tr>
        <tr><td>${t('bkr.db')}</td><td>${r.report.database === 'ok' ? t('diag.dbOk') : esc(r.report.database)}</td></tr>
        <tr><td>${t('bkr.sample')}</td><td>${t('bkr.sampleV', { a: r.report.sample_ok, b: r.report.sample })}</td></tr>
        <tr><td>${t('bkr.aside')}</td><td class="mono">${esc(r.aside)}</td></tr></table></div>
        <div class="m-foot"><button class="btn primary" data-close>${t('btn.close')}</button></div>`, 'sm');
      loadEvents(); loadStats();
    } else {
      openModal(`<div class="m-head"><h3>${t('bkr.stagedTitle')}</h3></div><div class="m-body"><p>${t('bkr.staged')}</p></div>
        <div class="m-foot"><button class="btn" data-close>${t('bkr.later')}</button><button class="btn primary" id="bkRestart">${t('bkr.restart')}</button></div>`, 'sm');
      $('#bkRestart').onclick = () => { post('/api/restart').catch(() => {}); openModal(`<div class="welcome" style="padding:36px 28px">${loadingHTML()}<p>${t('bkr.restarting')}</p></div>`, 'sm'); setTimeout(() => location.reload(), 9000); };
    }
  };
}

function drawFolderRules(s) {
  const el = $('#frList'); if (!el) return;
  const rules = s.folder_rules || {};
  el.innerHTML = s.roots.map(r => {
    const x = rules[r] || {};
    return `<div class="fr-row"><span class="mono" title="${esc(r)}">${esc(basename(r) || r)}</span>
      <label>${t('fr.days')} <input type="number" min="0" step="1" data-fr="${esc(r)}" data-k="keep_days" value="${x.keep_days ?? ''}" placeholder="${s.keep_days} (${t('fr.inherit')})"></label>
      <label>${t('fr.gb')} <input type="number" min="0" step="0.5" data-fr="${esc(r)}" data-k="max_gb" value="${x.max_gb ?? ''}" placeholder="${t('fr.inherit')}"></label>
      <span class="hint">${t('fr.now', { d: x.keep_days ?? s.keep_days ?? '∞', own: x.keep_days != null ? t('fr.own') : t('fr.global') })}</span></div>`;
  }).join('');
  el.onchange = async () => {
    const out = {};
    $$('[data-fr]', el).forEach(i => { if (i.value !== '') (out[i.dataset.fr] = out[i.dataset.fr] || {})[i.dataset.k] = +i.value; });
    const r = await post('/api/settings', { folder_rules: out });
    if (r.ok) { drawFolderRules(r.settings); notify(t('fr.saved')); }
  };
}

const SAFE_AUTO = ['temp', 'wintemp', 'edge', 'chrome', 'firefox', 'otherbrowsers', 'thumbs', 'crash', 'shaders'];
function drawAutoClean(s) {
  const el = $('#acBox'); if (!el) return;
  const a = s.auto_clean || { on: false, every: 'week', items: [] };
  el.innerHTML = a.on ? `<div class="ac-on">${svg('check')} ${t('ac.on', { every: t('ac.every.' + a.every), items: a.items.map(i => t('cl.item.' + i)).join(', ') })}
      ${a.last ? `<span class="hint">${t('ac.last', { when: fmtFull(a.last) })}</span>` : ''}</div>
      <div class="row"><button class="btn sm" id="acNow">${t('ac.now')}</button><button class="btn sm" id="acOff">${t('ac.off')}</button></div>`
    : `<button class="btn sm" id="acSetup">${t('ac.setup')}</button>`;
  if ($('#acOff')) $('#acOff').onclick = async () => { const r = await post('/api/settings', { auto_clean: { on: false } }); drawAutoClean(r.settings); notify(t('ac.offDone')); };
  if ($('#acNow')) $('#acNow').onclick = async () => { const r = await post('/api/autoclean-now'); notify(r.ok ? t('cl.cleaned', { size: fmtSize(r.freed) }) : esc(errText(r)), !r.ok); };
  if ($('#acSetup')) $('#acSetup').onclick = () => autoCleanSetup(s);
}
function autoCleanSetup(s) {  // F11: chosen items, a second confirmation, safe places only
  openModal(`<div class="m-head"><h3>${t('ac.title')}</h3><button class="icon-btn" data-close>${svg('x')}</button></div>
    <div class="m-body"><p>${t('ac.lead')}</p>${SAFE_AUTO.map(i => `<label class="chk"><input type="checkbox" data-aci="${i}" ${['temp', 'thumbs', 'crash'].includes(i) ? 'checked' : ''}> ${t('cl.item.' + i)}</label>`).join('')}
      <div class="row" style="margin-top:8px"><span class="seg" id="acEvery"><button data-every="week" class="on">${t('ac.every.week')}</button><button data-every="month">${t('ac.every.month')}</button></span></div>
      <label class="chk" style="margin-top:10px"><input type="checkbox" id="acSure"> ${t('ac.sure')}</label></div>
    <div class="m-foot"><button class="btn" data-close>${t('btn.cancel')}</button><button class="btn primary" id="acGo" disabled>${t('ac.turnOn')}</button></div>`, 'sm');
  let every = 'week';
  $('#acEvery').onclick = ev => { const b = ev.target.closest('[data-every]'); if (!b) return; every = b.dataset.every; $$('#acEvery button').forEach(x => x.classList.toggle('on', x === b)); };
  $('#acSure').onchange = ev => { $('#acGo').disabled = !ev.target.checked; };
  $('#acGo').onclick = async () => {
    const items = $$('[data-aci]:checked').map(x => x.dataset.aci);
    const r = await post('/api/settings', { auto_clean: { on: true, confirmed: true, every, items } });
    closeModal(); notify(r.ok && r.settings.auto_clean.on ? t('ac.onDone') : t('ac.none'), !(r.ok && r.settings.auto_clean.on));
  };
}

/* F7: replacing never needs a copy that is already there — the current content is kept first; when that is not possible,
   the choice is the user's */
const _showRestoreF = showRestore;
showRestore = async function (e, version, preferReplace) {
  await _showRestoreF(e, version, preferReplace);
  const opt = $('input[name=rpMode][value=replace]'); if (!opt) return;
  opt.closest('.rp-opt').querySelector('.hint')?.insertAdjacentHTML('beforeend', ` ${t('f7.kept')}`);
  const go = $('#rpGo');
  go.onclick = async () => {
    const replace = !!$('input[name=rpMode][value=replace]:checked');
    closeModal();
    let r = await post('/api/restore', { id: e.id, version, replace, lang: LANG });
    if (!r.ok && ['tooBigToKeep', 'noSpaceToKeep', 'cannotRead'].includes(r.code)) {
      const choice = await f7Choice(r.code); if (choice !== 'force') { if (choice === 'clean') setMode('clean'); return; }
      r = await post('/api/restore', { id: e.id, version, replace, force: true, lang: LANG });
    }
    if (!r.ok) { notify(esc(errText(r)), true); return; }
    const mono = x => `<span class="mono">${esc(x)}</span>`;
    notify(r.replaced ? t('rp.doneReplaced', { path: mono(r.path) }) + ' ' + t('f7.undo') : t('restore.done', { path: mono(r.path) }));
  };
};
function f7Choice(code) {
  return new Promise(res => {
    openModal(`<div class="m-head"><h3>${t('f7.title')}</h3></div><div class="m-body"><p>${t('f7.' + code)}</p><p class="hint">${t('f7.why')}</p></div>
      <div class="m-foot"><button class="btn left danger" data-f7="force">${t('f7.force')}</button><button class="btn" data-f7="cancel">${t('btn.cancel')}</button>
      ${code === 'noSpaceToKeep' ? `<button class="btn primary" data-f7="clean">${t('f7.clean')}</button>` : ''}</div>`, 'sm');
    $('#modal').onclick = ev => { const b = ev.target.closest('[data-f7]'); if (!b) return; $('#modal').onclick = null; closeModal(); res(b.dataset.f7); };
  });
}

/* F8: with a folder filter on, what happened in it between two dates — counts per kind and net size, each a click-through */
const _renderListF = renderList;
renderList = function (prepended) {
  _renderListF(prepended);
  if (S.mode !== 'changes' || !S.folder || S.goneOnly) return;
  const lead = $('#folderAtBtn')?.closest('.gone-lead'); if (!lead || $('#sliceBox')) return;
  const sl = S.slice && S.slice.folder === S.folder ? S.slice : null;
  lead.insertAdjacentHTML('afterend', `<div class="slice" id="sliceBox"><div class="row"><b>${t('sl.title')}</b>
    <input type="date" id="slFrom" value="${S.sliceFrom || new Date(Date.now() - 30 * 864e5).toISOString().slice(0, 10)}"> → <input type="date" id="slTo" value="${S.sliceTo || new Date().toISOString().slice(0, 10)}">
    <button class="btn sm" id="slBundle">${svg('download')}${t('vb.folder')}</button></div>
    <div id="slBody">${sl ? sliceHTML(sl) : loadingHTML()}</div></div>`);
  if (!sl) loadSlice();
};
const sliceHTML = sl => !sl.total ? `<div class="hint">${t('sl.none')}</div>` : `<div class="sl-kinds">${Object.entries(sl.kinds).map(([k, n]) =>
  `<button class="chip" data-sl-kind="${k}" ${n ? '' : 'disabled'}>${t('kind.' + k)} <b>${num(n)}</b></button>`).join('')}
  <span class="hint">${t('sl.net', { d: (sl.net >= 0 ? '+' : '−') + fmtSize(Math.abs(sl.net)) })}</span></div>
  ${sl.subfolders.length > 1 ? `<div class="sl-subs">${sl.subfolders.map(x => `<button class="chip" data-folder-filter="${esc(x.path)}">${esc(x.name === '.' ? t('sl.here') : x.name)} <b>${num(x.n)}</b></button>`).join('')}</div>` : ''}`;
async function loadSlice() {
  const from = new Date(($('#slFrom')?.value || '1970-01-01') + 'T00:00') / 1000, to = new Date(($('#slTo')?.value || '2999-01-01') + 'T00:00') / 1000 + 86400;
  const r = await get('/api/folder-slice', { folder: S.folder, since: from, until: to }).catch(() => null);
  if (!r || !r.ok) return;
  S.slice = r;
  if ($('#slBody')) $('#slBody').innerHTML = sliceHTML(r);
}
$('#list').addEventListener('change', ev => {
  if (ev.target.id === 'slFrom' || ev.target.id === 'slTo') { S.sliceFrom = $('#slFrom').value; S.sliceTo = $('#slTo').value; loadSlice(); }
});
$('#list').addEventListener('click', ev => {
  const k = ev.target.closest('[data-sl-kind]');
  if (k && S.slice) {
    ev.stopPropagation();
    S.kinds = new Set([k.dataset.slKind]);
    S.day = { since: S.slice.since, until: S.slice.until, label: `${$('#slFrom').value} → ${$('#slTo').value}` };
    applyFilters(); return;
  }
  if (ev.target.closest('#slBundle')) { ev.stopPropagation(); bundleDialog2([S.folder], S.slice ? S.slice.since : 0, S.slice ? S.slice.until : 0); }
}, true);

/* F9: saved searches, in the View menu */
const _viewMenuHTML = viewMenuHTML;
viewMenuHTML = function () {
  const saved = P.saved_searches || [];
  return _viewMenuHTML() + `<hr><div class="vm-head">${t('ss9.title')}</div>${saved.map((x, i) => `<div class="vm-saved"><button data-vs="${i}">${svg('star')}<span>${esc(x.name)}</span></button>
    <button class="icon-btn sm" data-vs-ren="${i}" title="${esc(t('ss9.rename'))}">${svg('edit')}</button><button class="icon-btn sm" data-vs-del="${i}" title="${esc(t('ss9.delete'))}">${svg('x')}</button></div>`).join('')}
    <button data-vs-save>${svg('plus')}<span>${t('ss9.save')}</span></button>`;
};
const curFilters = () => ({ kinds: [...S.kinds], cats: [...S.cats], q: S.q, range: S.range, day: S.day, folder: S.folder || '', starred: !!S.starOnly,
  noted: !!S.notedOnly, gone: !!S.goneOnly, sort: S.esort, big: !!S.bigOnly, where: S.where });
function applySaved(f) {
  S.kinds = new Set(f.kinds || []); S.cats = new Set(f.cats || []); S.q = f.q || ''; $('#q').value = S.q; S.nlSeen = S.q;
  S.range = f.range || 'all'; S.day = f.day || null; S.folder = f.folder || null; S.starOnly = !!f.starred; S.notedOnly = !!f.noted;
  S.goneOnly = !!f.gone; S.esort = f.sort || 'time'; S.bigOnly = !!f.big; S.where = f.where || '';
  if (S.mode !== 'changes') setMode('changes');
  applyFilters();
}
document.addEventListener('click', async ev => {
  const m = ev.target.closest('#viewMenu'); if (!m) return;
  const saved = [...(P.saved_searches || [])];
  const put = async list => { const r = await post('/api/settings', { saved_searches: list }); if (r.ok) P.saved_searches = r.settings.saved_searches; m.innerHTML = viewMenuHTML(); };
  const use = ev.target.closest('[data-vs]'), ren = ev.target.closest('[data-vs-ren]'), del = ev.target.closest('[data-vs-del]');
  if (use) { ev.stopPropagation(); m.hidden = true; applySaved(saved[+use.dataset.vs].filters); }
  else if (ev.target.closest('[data-vs-save]')) { ev.stopPropagation(); const name = prompt(t('ss9.name'), S.q || t('ss9.default')); if (name && name.trim()) put([...saved, { name: name.trim(), v: 1, filters: curFilters() }]); }
  else if (ren) { ev.stopPropagation(); const x = saved[+ren.dataset.vsRen]; const name = prompt(t('ss9.name'), x.name); if (name && name.trim()) { x.name = name.trim(); put(saved); } }
  else if (del) { ev.stopPropagation(); m.hidden = true; if (await confirmBox(t('ss9.delTitle'), esc(saved[+del.dataset.vsDel].name), t('ss9.delete'), true)) { saved.splice(+del.dataset.vsDel, 1); put(saved); } }
}, true);

/* F12: all versions of a file (or a folder) into a folder, with manifest.csv; size first, resumable */
const _moreMenuF = moreMenuHTML;
moreMenuHTML = function (items) {
  const e = currentItem();
  if (e && e.path) items = items.filter(Boolean).concat([`<button data-act="bundle">${svg('copy')}<span>${t('vb.file')}</span></button>`]);
  return _moreMenuF(items);
};
const _actF = act;
act = async function (name, e, btn) {
  if (name === 'bundle') return bundleDialog2([e.path]);
  return _actF(name, e, btn);
};
async function bundleDialog2(paths, since = 0, until = 0) {
  const est = await post('/api/restore-bundle', { paths, since, until, estimate: true }).catch(() => null);
  if (!est || !est.ok) { notify(esc(errText(est || {})), true); return; }
  if (!est.versions) { notify(t('vb.none')); return; }
  if (!await confirmBox(t('vb.title'), esc(t('vb.est', { v: num(est.versions), f: num(est.files), size: fmtSize(est.bytes) })), t('vb.go'))) return;
  const r = await post('/api/restore-bundle', { paths, since, until });
  if (!r.ok) { if (r.code !== 'cancelled') notify(esc(errText(r)), true); return; }
  const tick = async () => {
    const b = await get('/api/bundle').catch(() => ({}));
    if (b.state === 'running') return setTimeout(tick, 700);
    if (b.state === 'done') notifyAction(t('vb.done', { n: num(b.result.versions), path: `<span class="mono">${esc(b.dest)}</span>` }), t('act.reveal'), () => post('/api/clean/reveal', { path: b.dest }), 15000);
    else notify(esc(b.error || t('err.generic')), true);
  };
  tick();
}
