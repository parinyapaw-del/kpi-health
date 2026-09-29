// Item 6: heatmap of child rows × columns.
// Columns: every group (headline metric per group) when the indicator has groups;
// otherwise the headline metric + the first card metric.
import { vals, shortLabel, canDrill, homeCodeAt, CHILD_LEVEL, LEVEL_NAME } from '../data.js';
import { classify, esc, fmtPct, fmtInt, STATUS_ICON } from '../format.js';
import { toHash } from '../router.js';

export function heatColumns(ind) {
  const h = ind.headline;
  if (ind.groups) {
    return ind.groups.map((g) => ({
      key: g.key,
      group: g.key,
      label: g.label,
      metric: h.metric,
      num: h.num,
      den: h.den,
      useTarget: true,
    }));
  }
  const cols = [{ key: h.metric, group: null, label: shortLabel(ind, h.metric), ...h, useTarget: true }];
  const c0 = ind.cards?.[0];
  if (c0) cols.push({ key: c0.metric, group: null, label: c0.label, metric: c0.metric, num: c0.num, den: c0.den, useTarget: false });
  return cols;
}

function cell(row, col, ctx) {
  const v = vals(row, col.group ?? 'total') ?? {};
  const value = row.hasData ? v[col.metric] : null;
  const c = classify(value, v[col.den], col.useTarget ? ctx.target?.value : null, ctx.rules);
  const icon = STATUS_ICON[c.status];
  const title = `${row.name} · ${col.label}: ${fmtPct(value)} (${fmtInt(v[col.num])} / ${fmtInt(v[col.den])})${c.small ? ' · n<20' : ''}`;
  if (c.status === 'na') {
    return `<td class="hm s-na" title="${esc(title)}"><span class="hm-v">ไม่มีข้อมูล</span></td>`;
  }
  return `<td class="hm s-${c.status}${c.small ? ' is-small' : ''}" title="${esc(title)}">
    <span class="hm-v">${icon ? `<i aria-hidden="true">${icon}</i>` : ''}${fmtPct(value)}</span>
    <span class="hm-nd">${fmtInt(v[col.num])}/${fmtInt(v[col.den])}${c.small ? ' <b class="badge-small">n&lt;20</b>' : ''}</span>
  </td>`;
}

export function heatmapHTML(ctx) {
  const { ind, data, route } = ctx;
  const cols = heatColumns(ind);
  const childLevel = CHILD_LEVEL[route.level];
  const home = homeCodeAt(childLevel);
  const head = `<tr><th scope="col" class="hm-name">${esc(LEVEL_NAME[childLevel])}</th>${cols
    .map((c) => `<th scope="col">${esc(c.label)}${c.useTarget ? '' : '<span class="hm-sub">ไม่มีเป้า</span>'}</th>`)
    .join('')}</tr>`;
  const body = data.rows
    .map((r) => {
      const isHome = home != null && String(r.code) === String(home);
      const drill = r.hasData && canDrill(route.indicator, route.year, childLevel, r.code);
      const name = drill
        ? `<a href="${toHash({ ...route, level: childLevel, scope: r.code })}">${esc(r.name)}</a>`
        : esc(r.name);
      return `<tr class="${isHome ? 'is-home' : ''}"><th scope="row" class="hm-name">${isHome ? '▸ ' : ''}${name}</th>${cols
        .map((c) => cell(r, c, ctx))
        .join('')}</tr>`;
    })
    .join('');
  const total = `<tr class="hm-total"><th scope="row" class="hm-name">รวม ${esc(data.scope.name)}</th>${cols
    .map((c) => cell({ ...data.total, name: `รวม ${data.scope.name}`, hasData: data.total.hasData !== false }, c, ctx))
    .join('')}</tr>`;
  return `<section class="panel" id="panel-heat">
    <header class="panel-hd">
      <h2>แผนที่ความร้อน ${esc(LEVEL_NAME[childLevel])} × ${ind.groups ? 'กลุ่มอายุ' : 'ตัวชี้วัด'}</h2>
      <p class="panel-sub">${esc(shortLabel(ind, ind.headline.metric))} · ตัวเลขเล็ก = ตัวตั้ง/ตัวหาร</p>
    </header>
    <div class="scroll-x"><table class="heat">${`<thead>${head}</thead><tbody>${body}${total}</tbody>`}</table></div>
  </section>`;
}
