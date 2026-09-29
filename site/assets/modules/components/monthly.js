// Item 5: cumulative fiscal-year progress from the `monthly` dataset.
// Series are derived generically: every key in `cum` other than the headline denominator,
// each divided by the annual denominator (last available cum value) × 100.
import { findDataset, loadFile, shortLabel } from '../data.js';
import { esc } from '../format.js';
import { monthlyChart } from '../charts.js';
import { state } from '../state.js';

export function monthlyDataset(ctx) {
  const { ind, route } = ctx;
  if (!ind.monthly) return null;
  return findDataset(route.indicator, route.year, route.level, route.scope, 'monthly');
}

export function monthlyHTML(ctx, mdata) {
  const { data } = ctx;
  const rows = mdata.rows ?? [];
  const sel = state.monthlyRow;
  const opts = [`<option value="">ทั้ง${esc(data.scope.name)}</option>`]
    .concat(rows.map((r) => `<option value="${esc(r.code)}"${String(r.code) === sel ? ' selected' : ''}>${esc(r.name)}</option>`))
    .join('');
  return `<section class="panel" id="panel-monthly">
    <header class="panel-hd panel-hd-row">
      <div>
        <h2>ความคืบหน้ารายเดือน ปีงบ ${ctx.route.year}</h2>
        <p class="panel-sub">สะสม ต.ค. → ก.ย. เทียบเป้าหมายทั้งปี · ทุกกลุ่มอายุรวมกัน</p>
      </div>
      ${
        rows.length
          ? `<label class="select-wrap" for="monthly-row">พื้นที่ <select id="monthly-row">${opts}</select></label>`
          : ''
      }
    </header>
    <div class="chart-box" style="height:340px"><canvas id="chart-monthly" role="img" aria-label="กราฟความคืบหน้าสะสมรายเดือน"></canvas></div>
    <p class="panel-note" id="monthly-note"></p>
  </section>`;
}

export function mountMonthly(ctx, mdata) {
  const { ind, target } = ctx;
  const den = ind.headline.den;
  const src = state.monthlyRow ? mdata.rows?.find((r) => String(r.code) === state.monthlyRow) : null;
  const months = (src ?? mdata).months ?? [];
  const cumKeys = Object.keys(months.find((m) => m.cum)?.cum ?? {}).filter((k) => k !== den);
  let annual = null;
  for (const m of months) if (m.cum && typeof m.cum[den] === 'number') annual = m.cum[den];
  let latestIdx = -1;
  months.forEach((m, i) => {
    if (m.hasData) latestIdx = i;
  });
  const series = cumKeys.map((k, i) => {
    const vals = months.map((m) => (annual && m.cum && typeof m.cum[k] === 'number' ? (m.cum[k] / annual) * 100 : null));
    const nd = months.map((m) => ({ num: m.cum?.[k] ?? null, den: annual }));
    return {
      label: `${shortLabel(ind, k)}สะสม / ${shortLabel(ind, den)}ทั้งปี`,
      values: vals,
      nd,
      colorKey: i === 0 ? 's1' : 's2',
    };
  });
  const canvas = document.getElementById('chart-monthly');
  if (!canvas) return;
  monthlyChart(canvas, {
    id: 'monthly',
    labels: months.map((m) => m.label),
    series,
    target: target?.value,
    targetNote: target?.note,
    latestIdx,
  });
  const note = document.getElementById('monthly-note');
  if (note) {
    const name = src ? src.name : ctx.data.scope.name;
    const gaps = months.filter((m) => !m.hasData).map((m) => m.label);
    note.textContent =
      `${name}: ${shortLabel(ind, den)}ทั้งปี ${annual != null ? annual.toLocaleString('th-TH') : '–'} คน` +
      (latestIdx >= 0 ? ` · ข้อมูลล่าสุดเดือน ${months[latestIdx].label}` : '') +
      (gaps.length ? ` · ไม่มีรายงานเดือน ${gaps.join(', ')}` : '');
  }
}

export async function loadMonthly(ctx) {
  const ds = monthlyDataset(ctx);
  return ds ? loadFile(ds.file) : null;
}
