// Admin config override (§8.2): GET current KV `site` · PUT validated override · DELETE = back to repo defaults.
import { json } from '../../_lib/http.js';

const MAX_BODY = 20 * 1024;
const ID_RE = /^[a-z0-9_]{1,20}$/;
const YEAR_RE = /^\d{4}$/;
const MAX_CARDS = 6;

class Invalid extends Error {}
const bad = (msg) => {
  throw new Invalid(msg);
};
const isObj = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);

/** Trimmed string, or undefined when missing/empty; throws on wrong type or too long. */
function str(v, max, label) {
  if (v === undefined || v === null) return undefined;
  if (typeof v !== 'string') bad(`${label} ต้องเป็นข้อความ`);
  const s = v.trim();
  if (!s) return undefined;
  if (s.length > max) bad(`${label} ยาวเกิน ${max} ตัวอักษร`);
  return s;
}

function cleanIndicator(v, id) {
  if (!isObj(v)) bad(`indicators.${id} ต้องเป็น object`);
  const out = {};
  const name = str(v.name_th, 300, `ชื่อเต็มตัวชี้วัด ${id}`);
  const short = str(v.short, 40, `ชื่อย่อตัวชี้วัด ${id}`);
  if (name) out.name_th = name;
  if (short) out.short = short;
  if (v.cards !== undefined && v.cards !== null) {
    if (!Array.isArray(v.cards) || v.cards.length > MAX_CARDS) bad(`ป้ายการ์ด ${id} ต้องเป็นรายการไม่เกิน ${MAX_CARDS} ช่อง`);
    const cards = v.cards.map((c, i) => str(c, 80, `ป้ายการ์ด ${i + 1} ของ ${id}`) ?? null);
    while (cards.length && cards[cards.length - 1] === null) cards.pop();
    if (cards.length) out.cards = cards;
  }
  return Object.keys(out).length ? out : null;
}

function cleanTargets(v, id) {
  if (!isObj(v)) bad(`targets.${id} ต้องเป็น object`);
  const out = {};
  for (const [year, t] of Object.entries(v)) {
    if (!YEAR_RE.test(year)) bad(`ปีของเป้าหมาย ${id} ไม่ถูกต้อง (${year})`);
    if (!isObj(t) || !('value' in t)) bad(`เป้าหมาย ${id} ปี ${year} ต้องมี value`);
    const val = t.value;
    if (val !== null && !(typeof val === 'number' && Number.isFinite(val) && val >= 0 && val <= 100)) {
      bad(`เป้าหมาย ${id} ปี ${year} ต้องเป็นตัวเลข 0–100 หรือว่าง`);
    }
    out[year] = { value: val };
  }
  return Object.keys(out).length ? out : null;
}

/** Validate + sanitise an override (unknown keys and empty strings dropped). Throws Invalid with a Thai message. */
export function sanitize(body) {
  if (!isObj(body)) bad('ข้อมูลต้องเป็น JSON object');
  const out = {};
  const name = str(body.name, 200, 'ชื่อเว็บ');
  const org = str(body.org, 200, 'จัดทำโดย');
  const note = str(body.footerNote, 500, 'ข้อความท้ายหน้า');
  if (name) out.name = name;
  if (org) out.org = org;
  if (note) out.footerNote = note;
  if (body.currentYear !== undefined && body.currentYear !== null && body.currentYear !== '') {
    const y = body.currentYear;
    if (!Number.isInteger(y) || y < 2500 || y > 2700) bad('ปีปัจจุบันต้องเป็นปี พ.ศ. 2500–2700');
    out.currentYear = y;
  }
  for (const key of ['indicators', 'targets']) {
    const v = body[key];
    if (v === undefined || v === null) continue;
    if (!isObj(v)) bad(`${key} ต้องเป็น object`);
    const group = {};
    for (const [id, item] of Object.entries(v)) {
      if (!ID_RE.test(id)) bad(`รหัสตัวชี้วัดไม่ถูกต้อง (${id})`);
      const c = key === 'indicators' ? cleanIndicator(item, id) : cleanTargets(item, id);
      if (c) group[id] = c;
    }
    if (Object.keys(group).length) out[key] = group;
  }
  return out;
}

async function readOverride(env) {
  try {
    const v = await env.CONFIG.get('site', 'json');
    return isObj(v) ? v : {};
  } catch {
    return {};
  }
}

export async function onRequest({ request, env }) {
  if (request.method === 'GET') return json(await readOverride(env));

  if (request.method === 'DELETE') {
    await env.CONFIG.delete('site');
    return json({ ok: true });
  }

  if (request.method === 'PUT') {
    let body;
    try {
      const text = await request.text();
      if (new TextEncoder().encode(text).length > MAX_BODY) return json({ error: 'ข้อมูลใหญ่เกิน 20 KB' }, 413);
      body = JSON.parse(text);
    } catch {
      return json({ error: 'อ่าน JSON ไม่ได้' }, 400);
    }
    let clean;
    try {
      clean = sanitize(body);
    } catch (e) {
      if (e instanceof Invalid) return json({ error: e.message }, 400);
      throw e;
    }
    await env.CONFIG.put('site', JSON.stringify(clean));
    return json(clean);
  }

  return json({ error: 'method not allowed' }, 405, { allow: 'GET, PUT, DELETE' });
}
