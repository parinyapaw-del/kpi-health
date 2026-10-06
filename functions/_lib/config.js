// Shared config helpers for Pages Functions (no route: this file exports no onRequest* handler).

/** GitHub repo slug (owner/name) used by the admin pipeline-status and spec endpoints. */
export const REPO = 'parinyapaw-del/kpi-health';

/**
 * The admin's site override (KV `site`): always a plain object, `{}` when KV is unbound, the key is
 * missing, the value is not an object, or KV/JSON fails → callers fall back to repo defaults.
 */
export async function readSiteOverride(env) {
  try {
    const v = env.CONFIG ? await env.CONFIG.get('site', 'json') : null;
    return v !== null && typeof v === 'object' && !Array.isArray(v) ? v : {};
  } catch {
    return {};
  }
}
