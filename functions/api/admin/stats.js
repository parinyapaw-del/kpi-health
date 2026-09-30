// Usage stats for the admin page (§6, §8.2): GET /api/admin/stats?from=YYYY-MM-DD&to=YYYY-MM-DD (days in ICT).
import { json, todayICT, ensureSchema } from '../../_lib/http.js';

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const DAY_MS = 86_400_000;
const MAX_DAYS = 400;

/** YYYY-MM-DD → UTC ms, or NaN when not a real calendar date. */
function parseDay(s) {
  if (!DATE_RE.test(s)) return NaN;
  const t = Date.parse(`${s}T00:00:00Z`);
  return Number.isFinite(t) && new Date(t).toISOString().slice(0, 10) === s ? t : NaN;
}
const fmtDay = (t) => new Date(t).toISOString().slice(0, 10);

export async function onRequest({ request, env }) {
  if (request.method !== 'GET') return json({ error: 'method not allowed' }, 405, { allow: 'GET' });
  const db = env.DB;
  if (!db) return json({ error: 'no db' }, 503);

  const url = new URL(request.url);
  const today = todayICT();
  const to = url.searchParams.get('to') || today;
  const toT = parseDay(to);
  if (Number.isNaN(toT)) return json({ error: 'วันที่ to ไม่ถูกต้อง (YYYY-MM-DD)' }, 400);
  const from = url.searchParams.get('from') || fmtDay(toT - 29 * DAY_MS);
  const fromT = parseDay(from);
  if (Number.isNaN(fromT)) return json({ error: 'วันที่ from ไม่ถูกต้อง (YYYY-MM-DD)' }, 400);
  if (fromT > toT) return json({ error: 'วันเริ่มต้องไม่หลังวันสิ้นสุด' }, 400);
  if ((toT - fromT) / DAY_MS + 1 > MAX_DAYS) return json({ error: `ช่วงวันยาวเกิน ${MAX_DAYS} วัน` }, 400);

  try {
    await ensureSchema(db);
    const [tot, daily, pages, places] = await db.batch([
      db
        .prepare(
          `SELECT COALESCE(SUM(devices), 0) AS devices_all,
                  COALESCE(SUM(CASE WHEN day = ?1 THEN devices ELSE 0 END), 0) AS devices_today,
                  COALESCE(SUM(CASE WHEN day BETWEEN ?2 AND ?3 THEN views ELSE 0 END), 0) AS views_range,
                  COALESCE(SUM(CASE WHEN day BETWEEN ?2 AND ?3 THEN devices ELSE 0 END), 0) AS devices_range
           FROM hits`,
        )
        .bind(today, from, to),
      db
        .prepare('SELECT day, SUM(views) AS views, SUM(devices) AS devices FROM hits WHERE day BETWEEN ?1 AND ?2 GROUP BY day ORDER BY day ASC')
        .bind(from, to),
      db
        .prepare(
          'SELECT route, SUM(views) AS views, SUM(devices) AS devices FROM hits WHERE day BETWEEN ?1 AND ?2 GROUP BY route ORDER BY views DESC, route ASC LIMIT 50',
        )
        .bind(from, to),
      db
        .prepare(
          'SELECT region, city, SUM(views) AS views, SUM(devices) AS devices FROM hits WHERE day BETWEEN ?1 AND ?2 GROUP BY region, city ORDER BY views DESC, region ASC, city ASC LIMIT 50',
        )
        .bind(from, to),
    ]);
    const t = tot.results?.[0] ?? {};
    const num = (v) => Number(v ?? 0);
    return json({
      from,
      to,
      totals: {
        devices_all: num(t.devices_all),
        devices_today: num(t.devices_today),
        views_range: num(t.views_range),
        devices_range: num(t.devices_range),
      },
      daily: (daily.results ?? []).map((r) => ({ day: r.day, views: num(r.views), devices: num(r.devices) })),
      pages: (pages.results ?? []).map((r) => ({ route: r.route, views: num(r.views), devices: num(r.devices) })),
      places: (places.results ?? []).map((r) => ({ region: r.region ?? '', city: r.city ?? '', views: num(r.views), devices: num(r.devices) })),
    });
  } catch (e) {
    return json({ error: 'db error' }, 500);
  }
}
