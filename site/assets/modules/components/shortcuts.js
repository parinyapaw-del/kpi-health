// Country view: three shortcut cards along the home path (เขต 4 · อ่างทอง · เมืองอ่างทอง).
import { load, vals, targetFor, LEVEL_NAME } from '../data.js';
import { classify, esc, fmtPct, fmtFrac, STATUS_ICON, STATUS_TEXT } from '../format.js';
import { toHash } from '../router.js';

export async function shortcutsHTML(index, route) {
  const ind = index.indicators[route.indicator];
  const h = ind.headline;
  const tgt = targetFor(ind, route.year);
  const stops = index.home.path.slice(1);
  const cards = await Promise.all(
    stops.map(async (p) => {
      const data = await load(route.indicator, route.year, p.level, p.code);
      const v = data ? vals(data.total, 'total') : null;
      const value = v?.[h.metric] ?? null;
      const c = classify(value, v?.[h.den], tgt?.value, index.colorRules);
      const href = toHash({ ...route, level: p.level, scope: p.code });
      return `<a class="shortcut s-${c.status}" href="${href}">
        <span class="sc-level">${esc(LEVEL_NAME[p.level])}</span>
        <span class="sc-name">${esc(p.name)}</span>
        <span class="sc-value">${
          value == null
            ? '<span class="sc-na">ไม่มีข้อมูลปีนี้</span>'
            : `<i class="st-icon" aria-hidden="true">${STATUS_ICON[c.status]}</i>${fmtPct(value)}`
        }</span>
        <span class="sc-meta">${value == null ? '' : `${fmtFrac(v[h.num], v[h.den])} · ${STATUS_TEXT[c.status]}`}</span>
        <span class="sc-go" aria-hidden="true">→</span>
      </a>`;
    }),
  );
  return `<section class="shortcuts" aria-label="เส้นทางลัด">
    <h2 class="eyebrow">เส้นทางลัด · ปีงบ ${route.year}</h2>
    <div class="sc-grid">${cards.join('')}</div>
  </section>`;
}
