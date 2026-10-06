// Public site config (§8.2): GET /api/config → {override: KV `site` JSON or {}, googleClientId}.
// The web merges `override` over index.json before rendering (configOverride.js). Never fails on a missing KV.
import { json, methodNotAllowed } from '../_lib/http.js';
import { readSiteOverride } from '../_lib/config.js';

export async function onRequest({ request, env }) {
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    return methodNotAllowed('GET');
  }
  const override = await readSiteOverride(env); // invalid JSON or KV error → {} (repo defaults)
  return json({ override, googleClientId: env.GOOGLE_CLIENT_ID ?? null }, 200, { 'cache-control': 'public, max-age=60' });
}
