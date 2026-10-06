// GET /api/admin/spec → Markdown download: latest web_spec_phase2.md + README §1, §3 + current KV override (§8.2).
// Never includes the admin allowlist.
import { json, methodNotAllowed } from '../../_lib/http.js';
import { REPO, readSiteOverride } from '../../_lib/config.js';

const RAW = `https://raw.githubusercontent.com/${REPO}/main/`;
const SITE_URL = 'https://kpi-health.pages.dev/';

async function fetchText(file) {
  const res = await fetch(RAW + file, { headers: { 'User-Agent': 'kpi-health-admin' } });
  if (!res.ok) throw new Error(`${file}: HTTP ${res.status}`);
  return res.text();
}

/** A "## <n>." section of a Markdown file: from its heading line up to the next "## " heading, or null. */
function section(md, n) {
  const lines = md.split('\n');
  const start = lines.findIndex((l) => l.startsWith(`## ${n}.`));
  if (start < 0) return null;
  let end = lines.findIndex((l, i) => i > start && l.startsWith('## '));
  if (end < 0) end = lines.length;
  return lines.slice(start, end).join('\n').trim();
}

function nowICT() {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Bangkok',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(new Date());
  const p = Object.fromEntries(parts.map((x) => [x.type, x.value]));
  return { day: `${p.year}-${p.month}-${p.day}`, time: `${p.hour}:${p.minute}` };
}

export async function onRequest({ request, env }) {
  if (request.method !== 'GET') return methodNotAllowed('GET');

  let spec;
  let readme;
  try {
    [spec, readme] = await Promise.all([fetchText('web_spec_phase2.md'), fetchText('README.md')]);
  } catch (e) {
    return json({ error: `ดึงไฟล์จาก GitHub ไม่สำเร็จ (${e.message})` }, 502);
  }

  const site = await readSiteOverride(env); // invalid JSON → {} → treated as none
  const override = Object.keys(site).length ? site : null;

  const { day, time } = nowICT();
  const s1 = section(readme, 1);
  const s3 = section(readme, 3);
  const readmePart = s1 && s3 ? `${s1}\n\n${s3}` : readme.trim();

  const md = [
    '# kpi-health — spec + config snapshot',
    '',
    `- สร้างเมื่อ: ${day} ${time} (ICT)`,
    `- เว็บไซต์: ${SITE_URL}`,
    '- แหล่ง: `web_spec_phase2.md` + `README.md` (branch main บน GitHub)',
    '',
    '## Config ปัจจุบัน (KV override)',
    '',
    override ? ['```json', JSON.stringify(override, null, 2), '```'].join('\n') : 'ไม่มี override — ใช้ค่าจาก repo',
    '',
    '---',
    '',
    spec.trim(),
    '',
    '---',
    '',
    '# README (ตัดตอน §1, §3)',
    '',
    readmePart,
    '',
  ].join('\n');

  return new Response(md, {
    headers: {
      'content-type': 'text/markdown; charset=utf-8',
      'content-disposition': `attachment; filename="kpi-health_spec_${day}.md"`,
      'cache-control': 'no-store',
    },
  });
}
