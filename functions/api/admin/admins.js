// Admin allowlist (§8.2): GET {admins, you} · PUT {admins:[...]} (1–20 emails, must keep your own).
import { json, methodNotAllowed, readJsonBody } from '../../_lib/http.js';

const EMAIL_RE = /^[^\s@<>"',;]{1,64}@[a-z0-9-]+(\.[a-z0-9-]+)+$/;
const MAX_BODY = 4096;

export async function onRequest({ request, env, data }) {
  const you = data.email;
  if (request.method === 'GET') return json({ admins: data.admins, you });
  if (request.method !== 'PUT') return methodNotAllowed('GET, PUT');

  const { body, error } = await readJsonBody(request, MAX_BODY, { tooLarge: 'ข้อมูลใหญ่เกินไป', invalid: 'อ่าน JSON ไม่ได้' });
  if (error) return error;
  if (!Array.isArray(body?.admins)) return json({ error: 'ต้องส่ง admins เป็นรายการอีเมล' }, 400);

  const list = [];
  for (const raw of body.admins) {
    if (typeof raw !== 'string') return json({ error: 'อีเมลต้องเป็นข้อความ' }, 400);
    const e = raw.trim().toLowerCase();
    if (!e) continue;
    if (e.length > 254 || !EMAIL_RE.test(e)) return json({ error: `อีเมลไม่ถูกต้อง: ${e.slice(0, 80)}` }, 400);
    if (!list.includes(e)) list.push(e);
  }
  if (list.length < 1 || list.length > 20) return json({ error: 'ต้องมีผู้ดูแล 1–20 คน' }, 400);
  if (!list.includes(you)) return json({ error: 'ห้ามลบอีเมลของตัวเอง' }, 400);

  await env.CONFIG.put('admins', JSON.stringify(list));
  return json({ admins: list, you });
}
