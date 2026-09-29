// Site header: logo, title, indicator tabs, year switch, theme toggle, "ข้อมูล ณ" line.
import { esc, fmtAsOf } from '../format.js';
import { toHash } from '../router.js';
import { getTheme } from '../state.js';

export function headerHTML(index, route, ds) {
  const inds = Object.values(index.indicators);
  const tabs = inds
    .map((ind) => {
      const on = ind.id === route.indicator;
      const href = toHash({ ...route, indicator: ind.id });
      return `<a class="seg-btn${on ? ' is-on' : ''}" href="${href}" title="${esc(ind.name_th)}"${
        on ? ' aria-current="page"' : ''
      }>${esc(ind.short ?? ind.id)}</a>`;
    })
    .join('');
  const years = index.years
    .map((y) => {
      const on = Number(y) === Number(route.year);
      const cur = Number(y) === Number(index.currentYear);
      return `<a class="seg-btn${on ? ' is-on' : ''}" href="${toHash({ ...route, year: y })}"${
        on ? ' aria-current="page"' : ''
      }>${y}${cur ? '<span class="cur-badge">ปีงบปัจจุบัน</span>' : ''}</a>`;
    })
    .join('');

  let asOf = null;
  if (ds) {
    const src = index.sourceLabels?.[ds.source] ?? ds.source;
    asOf = `ข้อมูล ณ ${fmtAsOf(ds.asOf)} · ${esc(src)}`;
  }
  const dark = getTheme() === 'dark';
  const home = toHash({ indicator: route.indicator, year: route.year, level: index.home.path[0].level, scope: index.home.path[0].code });

  return `
  <div class="wrap hdr-row">
    <a class="brand" href="${home}">
      <span class="logo-plate"><img src="../assets/logo-angthong.png" alt="ตราโรงพยาบาลอ่างทอง" width="800" height="220"></span>
      <span class="brand-text"><strong>${esc(index.name)}</strong><span>${esc(index.org)}</span></span>
    </a>
    <div class="hdr-controls">
      <nav class="seg" aria-label="ตัวชี้วัด">${tabs}</nav>
      <nav class="seg" aria-label="ปีงบประมาณ">${years}</nav>
      <button type="button" class="theme-btn" id="theme-toggle" aria-pressed="${dark}">
        <span aria-hidden="true">${dark ? '☀' : '☾'}</span>${dark ? 'โหมดสว่าง' : 'โหมดมืด'}
      </button>
    </div>
  </div>
  <div class="wrap asof"><span class="asof-dot" aria-hidden="true"></span>${asOf ?? `ไม่มีข้อมูลระดับนี้ในปีงบ ${route.year}`}</div>`;
}
