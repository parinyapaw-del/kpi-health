// Item 3: horizontal bar chart of child areas (sorted desc, target line, home-path highlight, click = drill).
import { vals, canDrill, homeCodeAt, CHILD_LEVEL, LEVEL_NAME } from '../data.js';
import { classify, esc, isNum } from '../format.js';
import { barChart } from '../charts.js';

export function childItems(ctx) {
  const { ind, data, groupKey, target, rules, route } = ctx;
  const h = ind.headline;
  const childLevel = CHILD_LEVEL[route.level];
  const home = homeCodeAt(childLevel);
  return data.rows
    .filter((r) => r.hasData)
    .map((r) => {
      const v = vals(r, groupKey) ?? {};
      const c = classify(v[h.metric], v[h.den], target?.value, rules);
      return {
        code: String(r.code),
        name: r.name,
        value: v[h.metric],
        num: v[h.num],
        den: v[h.den],
        status: c.status,
        small: c.small,
        home: home != null && String(r.code) === String(home),
        drill: canDrill(route.indicator, route.year, childLevel, r.code),
        childLevel,
      };
    })
    .filter((d) => isNum(d.value))
    .sort((a, b) => b.value - a.value);
}

export function childBarsHTML(ctx) {
  const { data, route, groupLabel } = ctx;
  const childLevel = CHILD_LEVEL[route.level];
  const items = childItems(ctx);
  const missing = data.rows.filter((r) => !r.hasData).map((r) => r.name);
  const height = Math.max(180, items.length * 34 + 70);
  return `<section class="panel" id="panel-bars">
    <header class="panel-hd">
      <h2>เทียบราย${esc(LEVEL_NAME[childLevel])}</h2>
      <p class="panel-sub">${groupLabel ? `${esc(groupLabel)} · ` : ''}เรียงจากมากไปน้อย${
    items.some((d) => d.drill) ? ' · คลิกแท่งเพื่อเจาะลึก' : ''
  }</p>
    </header>
    <div class="chart-box" style="height:${height}px"><canvas id="chart-bars" role="img" aria-label="กราฟแท่งเทียบราย${esc(
    LEVEL_NAME[childLevel],
  )}"></canvas></div>
    <ul class="status-key" aria-label="คำอธิบายสี">
      ${
        ctx.target
          ? `<li><i class="sw sw-ok"></i>✓ ถึงเป้า</li>
      <li><i class="sw sw-warn"></i>! ต่ำกว่าเป้าไม่เกิน ${ctx.rules.warnBand} จุด</li>
      <li><i class="sw sw-bad"></i>✗ ต่ำกว่าเป้าเกิน ${ctx.rules.warnBand} จุด</li>`
          : `<li>ปีงบ ${route.year} ไม่มีเป้าหมาย จึงไม่แบ่งสี</li>`
      }
      <li><i class="sw sw-small"></i>n&lt;20 ตัวหารน้อย ไม่จัดอันดับ</li>
      <li><span class="home-key">▸</span> พื้นที่ของ รพ.</li>
    </ul>
    ${missing.length ? `<p class="panel-note">ไม่มีข้อมูล (ไม่นับในกราฟและอันดับ): ${missing.map(esc).join(', ')}</p>` : ''}
  </section>`;
}

export function mountChildBars(ctx, { onDrill, onPickLeaf, leafCodes }) {
  const canvas = document.getElementById('chart-bars');
  if (!canvas) return;
  const items = childItems(ctx).map((d) =>
    !d.drill && leafCodes?.has(d.code) ? { ...d, pickHint: 'คลิกเพื่อดูกราฟรายเดือน' } : d,
  );
  barChart(canvas, {
    id: 'bars',
    items,
    target: ctx.target?.value,
    targetNote: ctx.target?.note,
    onPick: (d) => {
      if (d.drill) onDrill(d);
      else if (d.pickHint) onPickLeaf(d);
    },
  });
}
