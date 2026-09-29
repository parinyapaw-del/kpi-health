// "ไม่มีข้อมูลระดับนี้ในปี …" box, with links to years/levels that do have data.
import { findDataset, LEVEL_NAME } from '../data.js';
import { esc } from '../format.js';
import { toHash } from '../router.js';

export function noDataHTML(index, route, trail) {
  const ind = index.indicators[route.indicator];
  const here = trail[trail.length - 1];
  const otherYears = index.years.filter((y) => y !== route.year && findDataset(route.indicator, y, route.level, route.scope));
  const parent = trail.length > 1 ? trail[trail.length - 2] : null;
  const links = [
    ...otherYears.map((y) => `<a class="btn" href="${toHash({ ...route, year: y })}">ดูปีงบ ${y}</a>`),
    parent
      ? `<a class="btn" href="${toHash({ ...route, level: parent.level, scope: parent.code })}">กลับไป${esc(parent.name)}</a>`
      : '',
  ].join('');
  return `<section class="nodata" role="status">
    <h2>ไม่มีข้อมูลระดับนี้ในปี ${route.year}</h2>
    <p>${esc(ind.short)} ยังไม่มีข้อมูลระดับ${esc(LEVEL_NAME[route.level])} (${esc(here?.name ?? route.scope)}) ในปีงบ ${
    route.year
  } จึงแสดงกราฟและเจาะลึกต่อไม่ได้</p>
    ${links ? `<div class="nodata-links">${links}</div>` : ''}
  </section>`;
}
