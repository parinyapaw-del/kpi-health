// Breadcrumb: ประเทศ › เขตสุขภาพที่ 4 › อ่างทอง › เมืองอ่างทอง
import { esc } from '../format.js';
import { toHash } from '../router.js';

export function breadcrumbHTML(trail, route) {
  const items = trail.map((t, i) => {
    const last = i === trail.length - 1;
    if (last) return `<li><span aria-current="page">${esc(t.name)}</span></li>`;
    const href = toHash({ indicator: route.indicator, year: route.year, level: t.level, scope: t.code });
    return `<li><a href="${href}">${esc(t.name)}</a></li>`;
  });
  return `<nav class="crumbs" aria-label="ลำดับพื้นที่"><ol>${items.join('')}</ol></nav>`;
}
