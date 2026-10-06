// Admin page (web_spec_phase2.md §8.3): Google Sign-In → ① config + live preview ② stats ③ admins ④ spec.md ⑤ reset.
// Every /api/admin/* call sends `Authorization: Bearer <Google ID token>`; the server verifies it (functions/_lib/auth.js).
import { esc } from '../assets/modules/format.js';
import { getTheme, setTheme } from '../assets/modules/state.js';
import { todayICT } from '../assets/modules/hit.js';
import { setIndex, findTreeNode } from '../assets/modules/data.js';

const SESSION_KEY = 'kpiAdminSession';
const EXPIRED_MSG = 'หมดเวลา กรุณาเข้าสู่ระบบใหม่';
const SAVED_MSG = 'บันทึกแล้ว — หน้าเว็บสาธารณะเปลี่ยนภายใน 60 วินาที';
const EMAIL_RE = /^[^\s@<>"',;]{1,64}@[a-z0-9-]+(\.[a-z0-9-]+)+$/;
const MAX_CARDS = 6;
const DAY_MS = 86_400_000;
const nf = new Intl.NumberFormat('th-TH');
const dayFmt = new Intl.DateTimeFormat('th-TH', { day: 'numeric', month: 'short', timeZone: 'UTC' });
const dayLongFmt = new Intl.DateTimeFormat('th-TH', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
const stampFmt = new Intl.DateTimeFormat('th-TH', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Bangkok' });

const $ = (id) => document.getElementById(id);

let defaults = null; // site/data/angthong/index.json (repo values = placeholders)
let clientId = null;
let session = null; // {token, email, exp}
let gsiReady = false;
let admins = [];
let chart = null;
let lastStats = null;
let draftTimer = null;
let toastTimer = null;
let formBuilt = false;

/** Thrown after the session was dropped (401/403); callers stay silent because the sign-in view shows the reason. */
class AuthLost extends Error {}

// ── Session ────────────────────────────────────────────

/** Decode a JWT payload (base64url JSON) — display only; the server verifies the token. */
function decodeJwt(token) {
  const part = String(token).split('.')[1] ?? '';
  const b64 = part.replace(/-/g, '+').replace(/_/g, '/').padEnd(Math.ceil(part.length / 4) * 4, '=');
  const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
  return JSON.parse(new TextDecoder().decode(bytes));
}

function loadSession() {
  try {
    const s = JSON.parse(sessionStorage.getItem(SESSION_KEY));
    if (s && typeof s.token === 'string' && Number(s.exp) * 1000 > Date.now() + 30_000) return s;
  } catch {
    /* ignore */
  }
  clearSession();
  return null;
}

function saveSession(s) {
  try {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(s));
  } catch {
    /* storage blocked: session lives in memory only */
  }
}

function clearSession() {
  try {
    sessionStorage.removeItem(SESSION_KEY);
  } catch {
    /* ignore */
  }
}

// ── Views / messages ───────────────────────────────────

function show(view) {
  for (const id of ['boot', 'view-setup', 'view-signin', 'view-dash']) $(id).hidden = id !== view;
}

function setMsg(id, text, ok = false) {
  const el = $(id);
  el.textContent = text ?? '';
  el.classList.toggle('is-ok', ok);
}

function showErr(id, err) {
  if (err instanceof AuthLost) return;
  setMsg(id, err?.message ?? String(err));
}

function toast(text) {
  const el = $('toast');
  el.textContent = text;
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.hidden = true), 4000);
}

function setSignedInChrome(on) {
  $('user-email').hidden = !on;
  $('signout-btn').hidden = !on;
  if (!on) $('pipeline').hidden = true;
}

function showSignin(msg = '', denied = false) {
  setSignedInChrome(false);
  setMsg('signin-msg', msg);
  $('denied-signout').hidden = !denied;
  $('preview').src = 'about:blank';
  chart?.destroy();
  chart = null;
  show('view-signin');
  renderGsiButton();
}

function signOut(msg = '') {
  clearSession();
  session = null;
  try {
    window.google?.accounts?.id?.disableAutoSelect();
  } catch {
    /* GSI not loaded */
  }
  showSignin(msg);
}

// ── API ────────────────────────────────────────────────

async function fetchJSON(url) {
  try {
    const res = await fetch(url, { cache: 'no-store' });
    return res.ok ? await res.json() : null;
  } catch {
    return null;
  }
}

/** Authenticated call to /api/admin/*. 401 → sign-in ("หมดเวลา…"), 403 → not an admin. Errors carry a Thai message. */
async function api(path, { method = 'GET', body, raw = false } = {}) {
  if (!session || Number(session.exp) * 1000 <= Date.now()) {
    signOut(EXPIRED_MSG);
    throw new AuthLost();
  }
  const headers = { authorization: `Bearer ${session.token}` };
  if (body !== undefined) headers['content-type'] = 'application/json';
  let res;
  try {
    res = await fetch(path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body), cache: 'no-store' });
  } catch {
    throw new Error('เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ ตรวจการเชื่อมต่ออินเทอร์เน็ต');
  }
  if (res.status === 401) {
    signOut(EXPIRED_MSG);
    throw new AuthLost();
  }
  if (res.status === 403) {
    const email = session?.email ?? '';
    clearSession();
    session = null;
    showSignin(`อีเมล ${email} ไม่อยู่ในรายชื่อผู้ดูแล`, true);
    throw new AuthLost();
  }
  if (raw && res.ok) return res;
  let j = null;
  try {
    j = await res.json();
  } catch {
    /* non-JSON error body */
  }
  if (!res.ok) {
    if (res.status === 503) throw new Error(`ระบบฝั่งเซิร์ฟเวอร์ยังไม่พร้อม (${j?.error ?? 'HTTP 503'}) — ตรวจ binding ใน Cloudflare Pages`);
    throw new Error(j?.error ? String(j.error) : `เกิดข้อผิดพลาด (HTTP ${res.status})`);
  }
  return j;
}

// ── Google Identity Services ───────────────────────────

function waitForGsi(ms = 10_000) {
  return new Promise((resolve, reject) => {
    const t0 = Date.now();
    (function poll() {
      if (window.google?.accounts?.id) resolve(window.google.accounts.id);
      else if (Date.now() - t0 > ms) reject(new Error('timeout'));
      else setTimeout(poll, 100);
    })();
  });
}

async function initGsi(promptNow) {
  let gid;
  try {
    gid = await waitForGsi();
  } catch {
    setMsg('signin-msg', 'โหลด Google Sign-In ไม่สำเร็จ ตรวจการเชื่อมต่ออินเทอร์เน็ตหรือปิดตัวบล็อกโฆษณาแล้วโหลดหน้าใหม่');
    return;
  }
  gid.initialize({ client_id: clientId, callback: onCredential, auto_select: true });
  gsiReady = true;
  renderGsiButton();
  if (promptNow) gid.prompt();
}

function renderGsiButton() {
  if (!gsiReady || $('view-signin').hidden) return;
  const el = $('gsi-btn');
  el.innerHTML = '';
  window.google.accounts.id.renderButton(el, { theme: 'outline', size: 'large', text: 'signin_with', locale: 'th', width: 280 });
}

function onCredential(resp) {
  try {
    const p = decodeJwt(resp.credential);
    session = { token: resp.credential, email: String(p.email ?? '').toLowerCase(), exp: Number(p.exp) };
  } catch {
    showSignin('อ่านข้อมูลการเข้าสู่ระบบไม่ได้ ลองใหม่อีกครั้ง');
    return;
  }
  saveSession(session);
  enter();
}

async function enter() {
  let r;
  try {
    r = await api('/api/admin/admins');
  } catch (e) {
    if (!(e instanceof AuthLost)) showSignin(e.message);
    return;
  }
  session.email = r.you;
  saveSession(session);
  admins = Array.isArray(r.admins) ? r.admins : [];
  $('user-email').textContent = r.you;
  setSignedInChrome(true);
  show('view-dash');
  renderAdmins();
  buildForm();
  $('preview').src = '/';
  loadConfig();
  loadStats();
  loadPipeline();
}

// ── Pipeline status ────────────────────────────────────

async function loadPipeline() {
  const el = $('pipeline');
  try {
    const p = await api('/api/admin/pipeline');
    let cls = 'is-bad';
    let label = 'ล้มเหลว ✗';
    if (p.status !== 'completed') [cls, label] = ['is-run', 'กำลังรัน …'];
    else if (p.conclusion === 'success') [cls, label] = ['is-ok', 'สำเร็จ ✓'];
    const t = Date.parse(p.updated_at ?? p.created_at ?? '');
    const when = Number.isFinite(t) ? `${stampFmt.format(t)} น.` : '–';
    const inner = `<span class="${cls}">${label}</span> · ${esc(when)}`;
    const url = typeof p.html_url === 'string' && p.html_url.startsWith('https://github.com/') ? p.html_url : null;
    el.innerHTML = `อัปเดตข้อมูลล่าสุด: ${url ? `<a href="${esc(url)}" target="_blank" rel="noopener">${inner}</a>` : inner}`;
  } catch (e) {
    if (e instanceof AuthLost) return;
    el.textContent = `อัปเดตข้อมูลล่าสุด: ดึงสถานะไม่ได้ (${e.message})`;
  }
  el.hidden = false;
}

// ── ① Config form + live preview ───────────────────────

const ph = (v, fallback = '') => esc(v == null || v === '' ? fallback : v);

function buildForm() {
  if (formBuilt) return;
  const box = $('config-fields');
  if (!defaults) {
    box.innerHTML = '<p class="adm-msg" role="alert">โหลดค่าเริ่มต้นจาก index.json ไม่สำเร็จ — โหลดหน้าใหม่อีกครั้ง</p>';
    $('save-config').disabled = true;
    return;
  }
  const d = defaults;
  const years = (d.years ?? []).map(Number);
  let html = `
    <label class="fld">ชื่อเว็บ<input type="text" data-k="name" maxlength="200" placeholder="${ph(d.name)}"></label>
    <label class="fld">จัดทำโดย<input type="text" data-k="org" maxlength="200" placeholder="${ph(d.org)}"></label>
    <label class="fld">ข้อความท้ายหน้า <span class="fld-hint">(ไม่บังคับ แสดงใต้ footer)</span>
      <textarea data-k="footerNote" maxlength="500" rows="2" placeholder="${ph(d.footerNote, 'ไม่มี')}"></textarea></label>
    <label class="fld">ปีปัจจุบัน<select data-k="currentYear"><option value="">ค่าจาก repo (${esc(d.currentYear)})</option>${years
      .map((y) => `<option value="${y}">${y}</option>`)
      .join('')}</select></label>
    <p class="adm-msg adm-warn" id="year-warn" role="status"></p>`;
  for (const [id, ind] of Object.entries(d.indicators ?? {})) {
    const tkey = ind.targets_key ?? id;
    const short = ind.short ?? id;
    const cards = (ind.cards ?? []).slice(0, MAX_CARDS);
    const targets = years
      .map((y) => {
        const t = d.targets?.[tkey]?.[String(y)]?.value;
        return `<div class="fld"><span>เป้าหมาย ปี ${y} (%)</span><span class="tgt">
          <input type="number" min="0" max="100" step="0.1" inputmode="decimal" data-year="${y}"
            aria-label="เป้าหมาย ${esc(short)} ปี ${y}" placeholder="${typeof t === 'number' ? t : 'ยังไม่กำหนด'}">
          <label class="tgt-none"><input type="checkbox" data-none="${y}"> ยังไม่กำหนด</label></span></div>`;
      })
      .join('');
    html += `<fieldset data-ind="${esc(id)}" data-tkey="${esc(tkey)}"><legend>${esc(short)}</legend>
      <label class="fld">ชื่อเต็ม<input type="text" data-f="name_th" maxlength="300" placeholder="${ph(ind.name_th)}"></label>
      <label class="fld">ชื่อย่อ<input type="text" data-f="short" maxlength="40" placeholder="${ph(ind.short)}"></label>
      <div class="fld-row">${cards
        .map(
          (c, i) =>
            `<label class="fld">ป้ายการ์ด ${i + 1}<input type="text" data-card="${i}" maxlength="80" placeholder="${ph(c?.label)}"></label>`,
        )
        .join('')}</div>
      <div class="fld-row">${targets}</div>
    </fieldset>`;
  }
  box.innerHTML = html;
  formBuilt = true;
}

/** Form → override object (empty inputs omitted → repo values). `invalid` = a target outside 0–100. */
function buildDraft() {
  const form = $('config-form');
  const cfg = {};
  let invalid = false;
  for (const el of form.querySelectorAll('[data-k]')) {
    const v = el.value.trim();
    if (v) cfg[el.dataset.k] = el.dataset.k === 'currentYear' ? Number(v) : v;
  }
  for (const fs of form.querySelectorAll('fieldset[data-ind]')) {
    const ind = {};
    for (const el of fs.querySelectorAll('[data-f]')) {
      const v = el.value.trim();
      if (v) ind[el.dataset.f] = v;
    }
    const cards = [...fs.querySelectorAll('[data-card]')].map((el) => el.value.trim() || null);
    while (cards.length && cards[cards.length - 1] === null) cards.pop();
    if (cards.length) ind.cards = cards;
    if (Object.keys(ind).length) (cfg.indicators ??= {})[fs.dataset.ind] = ind;

    const tg = {};
    for (const el of fs.querySelectorAll('input[data-year]')) {
      const y = el.dataset.year;
      const none = fs.querySelector(`input[data-none="${y}"]`)?.checked;
      el.disabled = Boolean(none);
      el.removeAttribute('aria-invalid');
      if (none) {
        tg[y] = { value: null };
        continue;
      }
      if (el.value === '' && !el.validity.badInput) continue;
      const n = Number(el.value);
      if (el.validity.badInput || !Number.isFinite(n) || n < 0 || n > 100) {
        el.setAttribute('aria-invalid', 'true');
        invalid = true;
        continue;
      }
      tg[y] = { value: n };
    }
    if (Object.keys(tg).length) (cfg.targets ??= {})[fs.dataset.tkey] = tg;
  }
  return { cfg, invalid };
}

/** Override object → form (missing keys → empty input = repo value). */
function fillForm(ov = {}) {
  const form = $('config-form');
  // A pinned currentYear (≠ repo) stops the site from moving to a new year by itself → keep it visible.
  const pinned = ov.currentYear != null && defaults && Number(ov.currentYear) !== Number(defaults.currentYear);
  const warn = $('year-warn');
  if (warn) {
    warn.textContent = pinned
      ? `ค่าปีปัจจุบันถูกแก้ทับไว้ (repo = ${defaults.currentYear}) — เว็บจะไม่เปลี่ยนปีเองจนกว่าจะกดคืนค่าเริ่มต้น`
      : '';
  }
  for (const el of form.querySelectorAll('[data-k]')) {
    const v = ov[el.dataset.k];
    el.value = v == null ? '' : String(v);
  }
  for (const fs of form.querySelectorAll('fieldset[data-ind]')) {
    const o = ov.indicators?.[fs.dataset.ind] ?? {};
    for (const el of fs.querySelectorAll('[data-f]')) el.value = typeof o[el.dataset.f] === 'string' ? o[el.dataset.f] : '';
    for (const el of fs.querySelectorAll('[data-card]')) el.value = o.cards?.[Number(el.dataset.card)] ?? '';
    for (const el of fs.querySelectorAll('input[data-year]')) {
      const t = ov.targets?.[fs.dataset.tkey]?.[el.dataset.year];
      const none = fs.querySelector(`input[data-none="${el.dataset.year}"]`);
      if (none) none.checked = Boolean(t && t.value === null);
      el.value = typeof t?.value === 'number' ? String(t.value) : '';
      el.disabled = Boolean(none?.checked);
      el.removeAttribute('aria-invalid');
    }
  }
  sendDraft();
}

function sendDraft() {
  const w = $('preview').contentWindow;
  if (!w || !formBuilt) return;
  try {
    w.postMessage({ type: 'kpi-config-draft', config: buildDraft().cfg }, location.origin);
  } catch {
    /* preview not on this origin yet */
  }
}

function queueDraft() {
  clearTimeout(draftTimer);
  draftTimer = setTimeout(sendDraft, 400);
}

async function loadConfig(announce = false) {
  try {
    fillForm(await api('/api/admin/config'));
    setMsg('config-msg', announce ? 'โหลดค่าที่บันทึกไว้แล้ว' : '', true);
  } catch (e) {
    showErr('config-msg', e);
  }
}

async function saveConfig(e) {
  e.preventDefault();
  const { cfg, invalid } = buildDraft();
  if (invalid) {
    setMsg('config-msg', 'เป้าหมายต้องเป็นตัวเลข 0–100 (หรือเว้นว่าง / ติ๊ก "ยังไม่กำหนด")');
    return;
  }
  const btn = $('save-config');
  btn.disabled = true;
  try {
    fillForm(await api('/api/admin/config', { method: 'PUT', body: cfg }));
    setMsg('config-msg', SAVED_MSG, true);
    toast(SAVED_MSG);
  } catch (err) {
    showErr('config-msg', err);
  } finally {
    btn.disabled = false;
  }
}

// ── ② Stats ────────────────────────────────────────────

const addDays = (day, n) => new Date(Date.parse(`${day}T00:00:00Z`) + n * DAY_MS).toISOString().slice(0, 10);
const fmtN = (v) => nf.format(Number(v ?? 0));

/** "dspm/province/15" → "สมวัย · อ่างทอง" (null when not in index.json). */
function routeName(route) {
  const [id, level, code] = String(route).split('/');
  const ind = defaults?.indicators?.[id];
  const node = findTreeNode(level, code)?.node; // data.js tree lookup (index set in init)
  return ind && node ? `${ind.short ?? id} · ${node.name}` : null;
}

async function loadStats() {
  const from = $('stats-from').value;
  const to = $('stats-to').value;
  if (!from || !to) {
    setMsg('stats-msg', 'กรุณาเลือกช่วงวันที่');
    return;
  }
  if (from > to) {
    setMsg('stats-msg', 'วันเริ่มต้องไม่หลังวันสิ้นสุด');
    return;
  }
  try {
    const s = await api(`/api/admin/stats?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`);
    setMsg('stats-msg', '');
    lastStats = s;
    renderStats(s);
  } catch (e) {
    showErr('stats-msg', e);
  }
}

function renderStats(s) {
  const range = `${dayLongFmt.format(Date.parse(s.from))} – ${dayLongFmt.format(Date.parse(s.to))}`;
  const cards = [
    ['ผู้ใช้ทั้งหมด', s.totals.devices_all, 'อุปกรณ์ไม่ซ้ำรายวัน รวมตั้งแต่เริ่มเก็บ'],
    ['วันนี้', s.totals.devices_today, 'ผู้ใช้ (อุปกรณ์) วันนี้'],
    ['ผู้ใช้ในช่วงที่เลือก', s.totals.devices_range, range],
    ['เปิดหน้าในช่วงที่เลือก', s.totals.views_range, range],
  ];
  $('stats-cards').innerHTML = cards
    .map(
      ([label, v, cap]) =>
        `<div class="card2"><div class="c2-label">${esc(label)}</div><div class="c2-value num">${fmtN(v)}</div><div class="c2-cap">${esc(cap)}</div></div>`,
    )
    .join('');
  drawChart(s);

  $('stats-pages').innerHTML = s.pages.length
    ? `<table class="adm-table"><thead><tr><th scope="col">หน้า</th><th scope="col">เปิดหน้า</th><th scope="col">ผู้ใช้</th></tr></thead><tbody>${s.pages
        .map((r) => {
          const name = routeName(r.route);
          const cell = name ? `${esc(name)}<div class="raw">${esc(r.route)}</div>` : esc(r.route);
          return `<tr><td>${cell}</td><td class="num">${fmtN(r.views)}</td><td class="num">${fmtN(r.devices)}</td></tr>`;
        })
        .join('')}</tbody></table>`
    : '<p class="adm-empty">ไม่มีข้อมูลในช่วงนี้</p>';

  $('stats-places').innerHTML = s.places.length
    ? `<table class="adm-table"><thead><tr><th scope="col">ภูมิภาค · เมือง</th><th scope="col">เปิดหน้า</th><th scope="col">ผู้ใช้</th></tr></thead><tbody>${s.places
        .map(
          (r) =>
            `<tr><td>${esc(r.region || 'ไม่ทราบ')} · ${esc(r.city || 'ไม่ทราบ')}</td><td class="num">${fmtN(r.views)}</td><td class="num">${fmtN(
              r.devices,
            )}</td></tr>`,
        )
        .join('')}</tbody></table>`
    : '<p class="adm-empty">ไม่มีข้อมูลในช่วงนี้</p>';
}

function drawChart(s) {
  chart?.destroy();
  chart = null;
  if (!window.Chart) {
    setMsg('stats-msg', 'โหลด Chart.js จาก cdnjs ไม่สำเร็จ — แสดงเฉพาะตาราง');
    return;
  }
  const days = [];
  for (let d = s.from; d <= s.to && days.length <= 400; d = addDays(d, 1)) days.push(d);
  const byDay = new Map(s.daily.map((r) => [r.day, r]));
  const css = getComputedStyle(document.documentElement);
  const tok = (n) => css.getPropertyValue(n).trim();
  window.Chart.defaults.font.family = tok('--font-body');
  const muted = tok('--muted');
  chart = new window.Chart($('stats-chart'), {
    data: {
      labels: days.map((d) => dayFmt.format(Date.parse(d))),
      datasets: [
        {
          type: 'line',
          label: 'ผู้ใช้ (อุปกรณ์)',
          data: days.map((d) => byDay.get(d)?.devices ?? 0),
          borderColor: tok('--series-2'),
          backgroundColor: tok('--series-2'),
          borderWidth: 2,
          pointRadius: days.length > 60 ? 0 : 2,
          tension: 0.25,
          order: 1,
        },
        {
          type: 'bar',
          label: 'เปิดหน้า',
          data: days.map((d) => byDay.get(d)?.views ?? 0),
          backgroundColor: tok('--series-1'),
          borderRadius: 3,
          order: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { labels: { color: tok('--ink-2'), boxWidth: 14 } },
        tooltip: {
          callbacks: {
            title: (items) => dayLongFmt.format(Date.parse(days[items[0].dataIndex])),
            label: (c) => `${c.dataset.label}: ${fmtN(c.parsed.y)}`,
          },
        },
      },
      scales: {
        x: { ticks: { color: muted, maxRotation: 0, autoSkip: true, autoSkipPadding: 12 }, grid: { display: false } },
        y: { beginAtZero: true, ticks: { color: muted, precision: 0, callback: (v) => fmtN(v) }, grid: { color: tok('--grid') } },
      },
    },
  });
}

// ── ③ Admins ───────────────────────────────────────────

function renderAdmins() {
  const you = session?.email;
  $('admin-list').innerHTML = admins
    .map((e, i) => {
      const own = e === you;
      return `<li><span class="em">${esc(e)}${own ? ' <span class="you">(คุณ)</span>' : ''}</span><button type="button" class="btn btn-ghost" data-rm="${i}"${
        own ? ' disabled title="ห้ามลบอีเมลของตัวเอง"' : ''
      }>ลบ</button></li>`;
    })
    .join('');
}

function addAdmin(e) {
  e.preventDefault();
  const input = $('admin-new');
  const v = input.value.trim().toLowerCase();
  if (!EMAIL_RE.test(v)) return setMsg('admins-msg', 'รูปแบบอีเมลไม่ถูกต้อง');
  if (admins.includes(v)) return setMsg('admins-msg', 'มีอีเมลนี้ในรายชื่อแล้ว');
  if (admins.length >= 20) return setMsg('admins-msg', 'ผู้ดูแลได้ไม่เกิน 20 คน');
  admins.push(v);
  input.value = '';
  renderAdmins();
  setMsg('admins-msg', 'เพิ่มในรายการแล้ว — กด "บันทึกรายชื่อ" เพื่อใช้งานจริง', true);
}

function removeAdmin(e) {
  const btn = e.target.closest('button[data-rm]');
  if (!btn || btn.disabled) return;
  admins.splice(Number(btn.dataset.rm), 1);
  renderAdmins();
  setMsg('admins-msg', 'ลบออกจากรายการแล้ว — กด "บันทึกรายชื่อ" เพื่อใช้งานจริง', true);
}

async function saveAdmins() {
  const btn = $('save-admins');
  btn.disabled = true;
  try {
    const r = await api('/api/admin/admins', { method: 'PUT', body: { admins } });
    admins = r.admins;
    renderAdmins();
    setMsg('admins-msg', 'บันทึกรายชื่อแล้ว', true);
  } catch (err) {
    showErr('admins-msg', err);
  } finally {
    btn.disabled = false;
  }
}

// ── ④ spec.md · ⑤ reset ───────────────────────────────

async function downloadSpec() {
  const btn = $('spec-btn');
  btn.disabled = true;
  setMsg('spec-msg', 'กำลังรวมไฟล์…', true);
  try {
    const res = await api('/api/admin/spec', { raw: true });
    const blob = await res.blob();
    const m = /filename="?([^";]+)"?/i.exec(res.headers.get('content-disposition') ?? '');
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = m?.[1] ?? 'kpi-health_spec.md';
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    setMsg('spec-msg', `ดาวน์โหลด ${a.download} แล้ว`, true);
  } catch (err) {
    showErr('spec-msg', err);
  } finally {
    btn.disabled = false;
  }
}

async function resetConfig() {
  if (!confirm('ลบค่าที่ตั้งไว้ทั้งหมดและกลับไปใช้ค่าจาก repo?')) return;
  const btn = $('reset-btn');
  btn.disabled = true;
  try {
    await api('/api/admin/config', { method: 'DELETE' });
    fillForm({});
    setMsg('reset-msg', 'คืนค่าเริ่มต้นแล้ว — หน้าเว็บสาธารณะกลับไปใช้ค่าจาก repo ภายใน 60 วินาที', true);
    setMsg('config-msg', '');
    toast('คืนค่าเริ่มต้นแล้ว');
  } catch (err) {
    showErr('reset-msg', err);
  } finally {
    btn.disabled = false;
  }
}

// ── Theme + wiring ─────────────────────────────────────

function syncThemeBtn() {
  const dark = getTheme() === 'dark';
  $('theme-toggle').setAttribute('aria-pressed', String(dark));
  $('theme-icon').textContent = dark ? '☀' : '☾';
  $('theme-txt').textContent = dark ? 'โหมดสว่าง' : 'โหมดมืด';
}

function bindEvents() {
  $('theme-toggle').addEventListener('click', () => {
    setTheme(getTheme() === 'dark' ? 'light' : 'dark');
    syncThemeBtn();
    if (lastStats && !$('view-dash').hidden) drawChart(lastStats);
    const w = $('preview').contentWindow;
    if (!$('view-dash').hidden && w && w.location.href !== 'about:blank') w.location.reload(); // preview reads the theme on load
  });
  $('signout-btn').addEventListener('click', () => signOut());
  $('denied-signout').addEventListener('click', () => signOut());

  const form = $('config-form');
  form.addEventListener('submit', saveConfig);
  form.addEventListener('input', queueDraft);
  form.addEventListener('change', queueDraft);
  $('reload-config').addEventListener('click', () => loadConfig(true));
  // The preview (site/index.html) says when its draft listener is ready → send the current draft.
  window.addEventListener('message', (e) => {
    if (e.origin === location.origin && e.source === $('preview').contentWindow && e.data?.type === 'kpi-config-ready') sendDraft();
  });

  $('stats-form').addEventListener('submit', (e) => {
    e.preventDefault();
    loadStats();
  });
  $('admin-add').addEventListener('submit', addAdmin);
  $('admin-list').addEventListener('click', removeAdmin);
  $('save-admins').addEventListener('click', saveAdmins);
  $('spec-btn').addEventListener('click', downloadSpec);
  $('reset-btn').addEventListener('click', resetConfig);
}

(async function init() {
  syncThemeBtn();
  bindEvents();
  const to = todayICT();
  $('stats-to').value = to;
  $('stats-from').value = addDays(to, -29);

  const [cfg, idx] = await Promise.all([fetchJSON('/api/config'), fetchJSON('../data/angthong/index.json')]);
  defaults = idx;
  if (idx) setIndex(idx); // lets data.js findTreeNode resolve route names for the stats table
  if (idx?.name) {
    $('site-name').textContent = idx.name;
    document.title = `ผู้ดูแลระบบ · ${idx.name}`;
  }
  if (typeof cfg?.googleClientId !== 'string' || !cfg.googleClientId) {
    show('view-setup');
    return;
  }
  clientId = cfg.googleClientId;
  session = loadSession();
  initGsi(!session);
  if (session) enter();
  else showSignin();
})();
