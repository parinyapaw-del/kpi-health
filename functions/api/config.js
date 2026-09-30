// Public site config (§8.2): GET /api/config → {override: KV `site` JSON or {}, googleClientId}.
// The web merges `override` over index.json before rendering (configOverride.js). Never fails on a missing KV.
import { json } from '../_lib/http.js';

export async function onRequest({ request, env }) {
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    return json({ error: 'method not allowed' }, 405, { allow: 'GET' });
  }
  let override = {};
  try {
    const v = env.CONFIG ? await env.CONFIG.get('site', 'json') : null;
    if (v && typeof v === 'object' && !Array.isArray(v)) override = v;
  } catch {
    /* invalid JSON or KV error → repo defaults */
  }
  return json({ override, googleClientId: env.GOOGLE_CLIENT_ID ?? null }, 200, { 'cache-control': 'public, max-age=60' });
}
