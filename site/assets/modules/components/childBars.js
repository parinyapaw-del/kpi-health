// Horizontal bar-chart panels: the 13 health regions (home page, not clickable) and the child areas
// of the current scope (sorted desc, click bar or name = drill when a dataset exists for the child).
import { vals, canDrill, CHILD_LEVEL, LEVEL_NAME } from '../data.js';
import { classify, esc, isNum } from '../format.js';
import { barChart, chartHeight } from '../charts.js';

/**
 * Bar items from a dataset. Pseudo rows are excluded; rows without data go last as "ไม่มีข้อมูล".
 * opts: {highlight: code, drillLevel: level|null}
 */
export function barItems(ctx, data, { highlight = null, drillLevel = null } = {}) {
  const { ind, groupKey, target, rules, route } = ctx;
  const h = ind.headline;
  const withData = [];
  const noData = [];
  for (const r of data.rows) {
    if (r.pseudo) continue;
    const v = vals(r, groupKey) ?? {};
    const value = r.hasData === false ? null : v[h.metric];
    const c = classify(value, v[h.den], target?.value, rules);
    const d = {
      code: String(r.code),
      name: r.name,
      value,
      num: v[h.num],
      den: v[h.den],
      status: c.status,
      small: c.small,
      highlight: highlight != null && String(r.code) === String(highlight),
      nodata: !isNum(value),
    };
    d.drill = !d.nodata && drillLevel ? canDrill(route.indicator, route.year, drillLevel, r.code) : false;
    d.childLevel = drillLevel;
    (d.nodata ? noData : withData).push(d);
  }
  withData.sort((a, b) => b.value - a.value);
  return [...withData, ...noData];
}

function legendHTML(ctx, items, { highlightLabel } = {}) {
  const { ind, target, rules } = ctx;
  const parts = [];
  if (ind.chart?.style === 'fill') {
    const baseTxt = ind.chart.baseLegend ?? 'เด็กพัฒนาการล่าช้าที่คาดประมาณจากอัตราความชุก';
    const fillTxt = ind.chart.fillLegend ?? ind.chart.fillLabel ?? '';
    parts.push(`<li><i class="sw sw-base"></i>แดง = ${esc(baseTxt)}</li>`);
    parts.push(`<li><i class="sw sw-fill"></i>เขียว = ${esc(fillTxt)}</li>`);
    if (!target) parts.push('<li>เป้าหมาย: ยังไม่กำหนด</li>');
  } else if (target) {
    parts.push('<li><i class="sw sw-ok"></i>✓ ถึงเป้า</li>');
    parts.push(`<li><i class="sw sw-warn"></i>! ต่ำกว่าเป้าไม่เกิน ${rules.warnBand} จุด</li>`);
    parts.push(`<li><i class="sw sw-bad"></i>✗ ต่ำกว่าเป้าเกิน ${rules.warnBand} จุด</li>`);
  } else {
    parts.push('<li><i class="sw sw-neutral"></i>เป้าหมาย: ยังไม่กำหนด (ไม่แบ่งสี)</li>');
  }
  if (items.some((d) => d.small)) parts.push(`<li><i class="sw sw-small"></i>n&lt;${rules.smallN} ตัวหารน้อย ไม่จัดอันดับ</li>`);
  if (highlightLabel && items.some((d) => d.highlight)) parts.push(`<li><span class="hl-key" aria-hidden="true"></span>${esc(highlightLabel)}</li>`);
  return `<ul class="status-key" aria-label="คำอธิบายสี">${parts.join('')}</ul>`;
}

/** Panel markup. id = canvas suffix; title/sub = heading text. */
export function barsPanelHTML(ctx, { id, title, sub, items, highlightLabel, note }) {
  const clickable = items.some((d) => d.drill);
  return `<section class="panel" id="panel-${id}">
    <header class="panel-hd">
      <h2>${esc(title)}</h2>
      <p class="panel-sub">${sub ? `${esc(sub)} · ` : ''}เรียงจากมากไปน้อย${clickable ? ' · คลิกแท่งหรือชื่อเพื่อเจาะลึก' : ''}</p>
    </header>
    <div class="chart-box" style="height:${chartHeight(items.length)}px"><canvas id="chart-${id}" role="img" aria-label="${esc(
      title,
    )} กราฟแท่งแนวนอน ${items.length} แถว (ตัวเลขทุกแถวอยู่ในตารางข้อมูลเต็ม)"></canvas></div>
    ${legendHTML(ctx, items, { highlightLabel })}
    ${note ? `<p class="panel-note">${note}</p>` : ''}
  </section>`;
}

export function mountBars(ctx, { id, items, onDrill }) {
  const canvas = document.getElementById(`chart-${id}`);
  if (!canvas) return;
  barChart(canvas, {
    id,
    items,
    style: ctx.ind.chart?.style === 'fill' ? 'fill' : 'status',
    target: ctx.target?.value,
    targetNote: ctx.target?.note,
    onPick: (d) => d.drill && onDrill?.(d),
  });
}

/** Child-area panel of the current scope. */
export function childBarsPanel(ctx) {
  const { data, route, groupLabel } = ctx;
  const childLevel = CHILD_LEVEL[route.level];
  const items = barItems(ctx, data, { drillLevel: childLevel });
  const html = barsPanelHTML(ctx, {
    id: 'child',
    title: `เทียบราย${LEVEL_NAME[childLevel]} ใน${data.scope.name}`,
    sub: groupLabel,
    items,
  });
  return { html, items };
}
