// Admin auth (web_spec_phase2.md §8.1): Google ID token → tokeninfo check → allowlist in KV `admins`.
// No route: this file exports no onRequest* handler.

const TOKENINFO = 'https://oauth2.googleapis.com/tokeninfo?id_token=';
const MAX_CACHE = 200;
const tokenCache = new Map(); // token -> {email, exp}

const fail = (message) => {
  throw { status: 401, message };
};

function evict(now) {
  for (const [k, v] of tokenCache) if (Number(v.exp) * 1000 <= now) tokenCache.delete(k);
  while (tokenCache.size > MAX_CACHE) tokenCache.delete(tokenCache.keys().next().value); // oldest first
}

/** Verify a Google ID token with Google's tokeninfo endpoint; returns {email, exp} or throws {status: 401, message}. */
export async function verifyIdToken(token, env) {
  const now = Date.now();
  if (typeof token !== 'string' || token.length < 20 || token.length > 4096) fail('invalid token');
  const hit = tokenCache.get(token);
  if (hit) {
    if (Number(hit.exp) * 1000 > now) return hit;
    tokenCache.delete(token);
  }

  let res;
  try {
    res = await fetch(TOKENINFO + encodeURIComponent(token));
  } catch {
    fail('tokeninfo unreachable');
  }
  if (res.status !== 200) fail('token rejected');
  let info;
  try {
    info = await res.json();
  } catch {
    fail('tokeninfo invalid json');
  }
  if (!env.GOOGLE_CLIENT_ID || info.aud !== env.GOOGLE_CLIENT_ID) fail('wrong audience');
  if (String(info.email_verified) !== 'true') fail('email not verified');
  if (!(Number(info.exp) * 1000 > now)) fail('token expired');
  if (typeof info.email !== 'string' || !info.email) fail('no email');

  const out = { email: info.email.toLowerCase(), exp: Number(info.exp) };
  tokenCache.set(token, out);
  if (tokenCache.size > MAX_CACHE) evict(now);
  return out;
}

const normList = (arr) => arr.filter((e) => typeof e === 'string' && e.trim()).map((e) => e.trim().toLowerCase());

/** Admin allowlist: KV `admins` (JSON array) → env ADMIN_EMAILS (comma-separated) → []. */
export async function getAdmins(env) {
  try {
    const list = env.CONFIG ? await env.CONFIG.get('admins', 'json') : null;
    if (Array.isArray(list)) {
      const clean = normList(list);
      if (clean.length) return clean;
    }
  } catch {
    /* invalid JSON in KV → fall back */
  }
  if (typeof env.ADMIN_EMAILS === 'string' && env.ADMIN_EMAILS.trim()) return normList(env.ADMIN_EMAILS.split(','));
  return [];
}

export function isAdmin(email, admins) {
  return typeof email === 'string' && Array.isArray(admins) && admins.includes(email.toLowerCase());
}
