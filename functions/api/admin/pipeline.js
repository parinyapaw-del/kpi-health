// GET /api/admin/pipeline → latest GitHub Actions run of the repo (public API, cached 60 s per isolate).
import { json } from '../../_lib/http.js';

const API = 'https://api.github.com/repos/parinyapaw-del/kpi-health/actions/runs?per_page=1';
const CACHE_MS = 60_000;
let cache = null; // {at, body}

export async function onRequest({ request }) {
  if (request.method !== 'GET') return json({ error: 'method not allowed' }, 405, { allow: 'GET' });
  const now = Date.now();
  if (cache && now - cache.at < CACHE_MS) return json(cache.body);
  try {
    const res = await fetch(API, { headers: { 'User-Agent': 'kpi-health-admin', Accept: 'application/vnd.github+json' } });
    if (!res.ok) throw new Error(`GitHub HTTP ${res.status}`);
    const run = (await res.json())?.workflow_runs?.[0];
    if (!run) throw new Error('ยังไม่มี workflow run');
    const body = {
      name: run.name ?? null,
      status: run.status ?? null,
      conclusion: run.conclusion ?? null,
      created_at: run.created_at ?? null,
      updated_at: run.updated_at ?? null,
      html_url: run.html_url ?? null,
    };
    cache = { at: now, body };
    return json(body);
  } catch (e) {
    return json({ error: e?.message ?? 'github error' }, 502);
  }
}
