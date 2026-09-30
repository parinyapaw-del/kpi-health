// "ไม่มีข้อมูลระดับนี้ในปี …" box, with links to other years that have data and back to the parent.
import { findDataset, LEVEL_NAME } from '../data.js';
import { esc } from '../format.js';
import { toHash } from '../router.js';

export function noDataHTML(index, route, trail) {
  const ind = index.indicators[route.indicator];
  const here = trail[trail.length - 1];
  const otherYears = index.years.filter((y) => Number(y) !== route.year && findDataset(route.indicator, y, route.level, route.scope));
  const parent = trail.length > 1 ? trail[trail.length - 2] : null;
  const links = [
    parent
      ? `<a class="btn" href="${toHash({ ...route, level: parent.level, scope: parent.code })}">‹ กลับไป${esc(parent.name)}</a>`
      : '',
    ...otherYears.map((y) => `<a class="btn btn-ghost" href="${toHash({ ...route, year: Number(y) })}">ดูปีงบ ${y}</a>`),
  ].join('');
  return `<section class="nodata" role="status">
    <h2>ไม่มีข้อมูลระดับนี้ในปี ${route.year}</h2>
    <p>ตัวชี้วัด “${esc(ind.short ?? ind.id)}” ไม่มีข้อมูลระดับ${esc(LEVEL_NAME[route.level])} (${esc(
      here?.name ?? route.scope,
    )}) ในปีงบ ${route.year}</p>
    ${links ? `<div class="nodata-links">${links}</div>` : ''}
  </section>`;
}
