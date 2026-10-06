// Site header (§5.2): region-4 logo + site name, "จัดทำโดย" line with the org logo, indicator tabs,
// year switch (only with ≥ 2 years), theme toggle, full indicator name + "ข้อมูล ณ".
// On phones the header is sticky and condenses on scroll to the tabs + a one-line breadcrumb.
import { esc, fmtAsOf, orgLogoHTML } from '../format.js';
import { homeOf } from '../data.js';
import { toHash } from '../router.js';
import { getTheme } from '../state.js';
import { breadcrumbHTML } from './breadcrumb.js';

export function headerHTML(index, route, ds, trail) {
  const ind = index.indicators[route.indicator];
  const tabs = Object.values(index.indicators)
    .map((it) => {
      const on = it.id === route.indicator;
      return `<a class="seg-btn${on ? ' is-on' : ''}" href="${toHash({ ...route, indicator: it.id })}" title="${esc(it.name_th)}"${
        on ? ' aria-current="page"' : ''
      }>${esc(it.short ?? it.id)}</a>`;
    })
    .join('');
  const years =
    index.years.length >= 2
      ? `<nav class="seg" aria-label="ปีงบประมาณ">${index.years
          .map((y) => {
            const on = Number(y) === Number(route.year);
            return `<a class="seg-btn${on ? ' is-on' : ''}" href="${toHash({ ...route, year: Number(y) })}"${
              on ? ' aria-current="page"' : ''
            }>${y}</a>`;
          })
          .join('')}</nav>`
      : '';

  const src = ds ? index.sourceLabels?.[ds.source] ?? ds.source : null;
  const asOf = ds ? `ข้อมูล ณ ${fmtAsOf(ds.asOf)} · ${esc(src)}` : `ไม่มีข้อมูลระดับนี้ในปีงบ ${route.year}`;
  const dark = getTheme() === 'dark';
  const home = homeOf(index);
  const homeHref = toHash({ indicator: route.indicator, year: route.year, level: home.level, scope: home.code });

  return `
  <div class="wrap hdr-row">
    <a class="brand" href="${homeHref}">
      ${index.logo ? `<img class="brand-logo" src="${esc(index.logo)}" alt="ตราเขตสุขภาพที่ 4" width="800" height="806">` : ''}
      <span class="brand-text">
        <strong>${esc(index.name)}</strong>
        <span class="brand-org">${orgLogoHTML(index)}${esc(index.org ?? '')}</span>
      </span>
    </a>
    <div class="hdr-controls">
      <nav class="seg seg-ind" aria-label="ตัวชี้วัด">${tabs}</nav>
      ${years}
      <button type="button" class="theme-btn" id="theme-toggle" aria-pressed="${dark}">
        <span aria-hidden="true">${dark ? '☀' : '☾'}</span><span class="theme-txt">${dark ? 'โหมดสว่าง' : 'โหมดมืด'}</span>
      </button>
    </div>
  </div>
  <div class="wrap hdr-mini">${breadcrumbHTML(trail, route, 'crumbs crumbs-mini')}</div>
  <div class="wrap hdr-sub">
    <span class="ind-name">${esc(ind.name_th)}</span>
    <span class="asof"><span class="asof-dot" aria-hidden="true"></span>${asOf}</span>
  </div>`;
}
