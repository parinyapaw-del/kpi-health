// Guards every /api/admin/* request: Google ID token (Authorization: Bearer) + allowlist (§8.1).
// On success: data.email = signed-in admin, data.admins = current allowlist.
import { json } from '../../_lib/http.js';
import { verifyIdToken, getAdmins, isAdmin } from '../../_lib/auth.js';

export async function onRequest({ request, env, data, next }) {
  if (!env.CONFIG) return json({ error: 'no kv' }, 503);
  if (!env.GOOGLE_CLIENT_ID) return json({ error: 'no client id' }, 503);

  const m = /^Bearer\s+(\S+)$/i.exec(request.headers.get('authorization') ?? '');
  if (!m) return json({ error: 'unauthorized' }, 401);

  let email;
  try {
    ({ email } = await verifyIdToken(m[1], env));
  } catch (e) {
    return json({ error: 'unauthorized', detail: e?.message ?? 'invalid token' }, 401);
  }

  const admins = await getAdmins(env);
  if (!isAdmin(email, admins)) return json({ error: 'forbidden', email }, 403);

  data.email = email;
  data.admins = admins;
  return next();
}
