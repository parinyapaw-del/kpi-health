// Cloudflare Pages Function: anonymous page-view counter (web_spec_phase2.md §6).
//   POST /api/hit          body {"route":"dspm/province/19","newDevice":true}
//   GET  /api/hit?summary=1
// Both respond {total_devices, today_devices}. Binding: env.DB (D1).
// Stores per (day ICT, route, cf.region, cf.city): views, devices. Never reads or stores IP / user-agent.

import { json, todayICT, ensureSchema } from '../_lib/http.js';

const ROUTE_RE = /^[a-z]+\/[a-z]+\/[A-Za-z0-9]{1,10}$/;
const CACHE_MS = 60_000;
const MAX_BODY = 1024;

let cache = null; // {at, day, total, today}

async function summary(db, day) {
  const now = Date.now();
  if (cache && cache.day === day && now - cache.at < CACHE_MS) return cache;
  const row = await db
    .prepare('SELECT COALESCE(SUM(devices), 0) AS total, COALESCE(SUM(CASE WHEN day = ?1 THEN devices ELSE 0 END), 0) AS today FROM hits')
    .bind(day)
    .first();
  cache = { at: now, day, total: Number(row?.total ?? 0), today: Number(row?.today ?? 0) };
  return cache;
}

const out = (s) => json({ total_devices: s.total, today_devices: s.today });

function clean(v) {
  return typeof v === 'string' ? v.slice(0, 64) : '';
}

export async function onRequestPost({ request, env }) {
  const db = env.DB;
  if (!db) return json({ error: 'no db' }, 503);

  const len = Number(request.headers.get('content-length') ?? 0);
  if (len > MAX_BODY) return json({ error: 'body too large' }, 413);
  let body;
  try {
    const text = await request.text();
    if (text.length > MAX_BODY) return json({ error: 'body too large' }, 413);
    body = JSON.parse(text);
  } catch {
    return json({ error: 'invalid json' }, 400);
  }
  const route = body?.route;
  const newDevice = body?.newDevice;
  if (typeof route !== 'string' || !ROUTE_RE.test(route) || typeof newDevice !== 'boolean') {
    return json({ error: 'invalid body' }, 400);
  }

  const day = todayICT();
  const region = clean(request.cf?.region);
  const city = clean(request.cf?.city);
  try {
    await ensureSchema(db);
    await db
      .prepare(
        `INSERT INTO hits(day, route, region, city, views, devices) VALUES (?1, ?2, ?3, ?4, 1, ?5)
         ON CONFLICT(day, route, region, city) DO UPDATE SET views = views + 1, devices = devices + excluded.devices`,
      )
      .bind(day, route, region, city, newDevice ? 1 : 0)
      .run();
    const fresh = !cache || cache.day !== day || Date.now() - cache.at >= CACHE_MS;
    const s = await summary(db, day);
    // Within the cache window, count this device in the cached totals so the visitor sees themself.
    if (!fresh && newDevice) {
      s.total += 1;
      s.today += 1;
    }
    return out(s);
  } catch (e) {
    return json({ error: 'db error' }, 500);
  }
}

export async function onRequestGet({ request, env }) {
  const db = env.DB;
  if (!db) return json({ error: 'no db' }, 503);
  const url = new URL(request.url);
  if (url.searchParams.get('summary') !== '1') return json({ error: 'use ?summary=1' }, 400);
  try {
    await ensureSchema(db);
    return out(await summary(db, todayICT()));
  } catch (e) {
    return json({ error: 'db error' }, 500);
  }
}
