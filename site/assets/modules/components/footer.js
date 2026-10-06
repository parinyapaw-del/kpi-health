// Footer (§5.6): org logo + "จัดทำโดย" · user counts from /api/hit · "ข้อมูล ณ" · GitHub repo link · admin link (2b)
// · optional footerNote (admin override).
import { esc, fmtAsOf, fmtInt, isNum, orgLogoHTML } from '../format.js';

/** counts: {total_devices, today_devices} | null (failed) | undefined (pending). */
export function countsText(counts) {
  if (counts === undefined) return 'ผู้ใช้งาน … คน · วันนี้ … · ไม่เก็บข้อมูลส่วนบุคคล';
  const n = (v) => (counts && isNum(v) ? fmtInt(v) : '–');
  return `ผู้ใช้งาน ${n(counts?.total_devices)} คน · วันนี้ ${n(counts?.today_devices)} · ไม่เก็บข้อมูลส่วนบุคคล`;
}

export function footerHTML(index, asOf, counts) {
  return `<div class="wrap ftr">
    <p class="ftr-org">${orgLogoHTML(index)}<span>${esc(index.org ?? '')}</span></p>
    <p class="ftr-meta">
      <span id="hit-counts" aria-live="polite">${countsText(counts)}</span>
      <span>ข้อมูล ณ ${esc(fmtAsOf(asOf))} · ${esc(index.sourceLabels?.api ?? 'MOPH Open Data API')}</span>
      ${index.repo ? `<a href="${esc(index.repo)}" rel="noopener" target="_blank">ซอร์สโค้ดและข้อมูลบน GitHub</a>` : ''}
      <a class="ftr-admin" href="/admin/">ผู้ดูแลระบบ</a>
    </p>
    ${index.footerNote ? `<p class="ftr-note">${esc(index.footerNote)}</p>` : ''}
  </div>`;
}
