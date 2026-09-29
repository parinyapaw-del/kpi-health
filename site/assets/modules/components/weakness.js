// Item 7: "จุดควรพัฒนา" — the 3 (row × column) cells furthest below the year's target.
import { vals, shortLabel, CHILD_LEVEL, ROW_PREFIX } from '../data.js';
import { esc, fmtPct, fmtInt, fmtNum, isNum } from '../format.js';
import { heatColumns } from './heatmap.js';

export function weaknessHTML(ctx) {
  const { ind, data, target, rules, route } = ctx;
  const head = `<header class="panel-hd"><h2>จุดควรพัฒนา</h2><p class="panel-sub">3 จุดที่ต่ำกว่าเป้ามากที่สุด · ไม่นับ n&lt;20</p></header>`;
  if (!target) {
    return `<section class="panel weak" id="panel-weak">${head}<p class="weak-empty">ปีงบ ${route.year} ไม่มีเป้าหมาย จึงไม่จัดจุดควรพัฒนา</p></section>`;
  }
  const prefix = ROW_PREFIX[CHILD_LEVEL[route.level]] ?? '';
  const cols = heatColumns(ind).filter((c) => c.useTarget);
  const metricLabel = shortLabel(ind, ind.headline.metric);
  const cands = [];
  for (const r of data.rows) {
    if (!r.hasData) continue;
    for (const c of cols) {
      const v = vals(r, c.group ?? 'total') ?? {};
      const val = v[c.metric];
      const den = v[c.den];
      if (!isNum(val) || !isNum(den) || den < rules.smallN) continue;
      if (val >= target.value) continue;
      cands.push({ r, c, v, val, gap: target.value - val });
    }
  }
  cands.sort((a, b) => b.gap - a.gap);
  const top = cands.slice(0, 3);
  if (!top.length) {
    return `<section class="panel weak" id="panel-weak">${head}<p class="weak-empty"><span class="ok-mark" aria-hidden="true">✓</span> ทุกพื้นที่${
      ind.groups ? 'และทุกกลุ่มอายุ' : ''
    }ที่มีตัวหารตั้งแต่ ${rules.smallN} ขึ้นไป ถึงเป้า ${target.value}%</p></section>`;
  }
  const items = top
    .map((x, i) => {
      const grp = ind.groups ? ` · ${esc(x.c.label)}` : '';
      const metric = ind.groups ? metricLabel : x.c.label;
      return `<li class="${x.gap > rules.warnBand ? 's-bad' : 's-warn'}">
        <span class="weak-rank">${i + 1}</span>
        <span class="weak-text"><b>${esc(prefix + x.r.name)}</b>${grp} · ${esc(metric)} ${fmtPct(x.val)} (${fmtInt(
        x.v[x.c.num],
      )}/${fmtInt(x.v[x.c.den])}) <span class="weak-gap">ต่ำกว่าเป้า ${fmtNum(x.gap)} จุด</span></span>
      </li>`;
    })
    .join('');
  return `<section class="panel weak" id="panel-weak">${head}<ol class="weak-list">${items}</ol>
    <p class="panel-note">เทียบกับเป้า ${target.value}%${target.note ? '*' : ''} ของปีงบ ${route.year}${
    ind.groups ? ' (ใช้เป้าเดียวกันทุกกลุ่มอายุ)' : ''
  } · พบต่ำกว่าเป้าทั้งหมด ${cands.length} จุด</p></section>`;
}
