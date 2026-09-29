// Item 4: 3-year line for this scope (headline metric, active group) + per-year target + parent line.
import { load, vals, targetFor } from '../data.js';
import { esc } from '../format.js';
import { trendChart } from '../charts.js';

export function trendHTML(ctx) {
  return `<section class="panel" id="panel-trend">
    <header class="panel-hd">
      <h2>แนวโน้ม ${ctx.index.years.length} ปี</h2>
      <p class="panel-sub">${esc(ctx.data.scope.name)}${ctx.groupLabel ? ` · ${esc(ctx.groupLabel)}` : ''}</p>
    </header>
    <div class="chart-box" style="height:320px"><canvas id="chart-trend" role="img" aria-label="กราฟเส้นแนวโน้มรายปี"></canvas></div>
  </section>`;
}

export async function mountTrend(ctx, isStale) {
  const { index, ind, route, groupKey, data } = ctx;
  const h = ind.headline;
  const years = index.years;
  const parentRef = data.scope.parent;
  const own = await Promise.all(years.map((y) => load(route.indicator, y, route.level, route.scope)));
  const par = parentRef
    ? await Promise.all(years.map((y) => load(route.indicator, y, parentRef.level, parentRef.code)))
    : [];
  if (isStale()) return;
  const pick = (d) => {
    const v = d ? vals(d.total, groupKey) : null;
    return { value: v?.[h.metric] ?? null, num: v?.[h.num] ?? null, den: v?.[h.den] ?? null };
  };
  const ownP = own.map(pick);
  const series = [{ label: data.scope.name, kind: 'scope', values: ownP.map((p) => p.value), nd: ownP }];
  if (par.some(Boolean)) {
    const parP = par.map(pick);
    const pName = par.find(Boolean)?.scope?.name ?? '';
    series.push({ label: pName, kind: 'parent', values: parP.map((p) => p.value), nd: parP });
  }
  const tv = years.map((y) => targetFor(ind, y)?.value ?? null);
  if (tv.some((v) => v != null)) series.push({ label: 'เป้าหมาย', kind: 'target', values: tv, nd: [] });
  const canvas = document.getElementById('chart-trend');
  if (canvas) trendChart(canvas, { id: 'trend', labels: years.map(String), series });
}
