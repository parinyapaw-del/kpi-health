// Chart.js wrappers (Chart.js 4 + chartjs-plugin-annotation loaded as UMD globals).
import { fmtPct, fmtFrac, STATUS_ICON } from './format.js';
import { reduceMotion } from './state.js';

const Chart = window.Chart;
if (Chart && window['chartjs-plugin-annotation']) {
  Chart.register(window['chartjs-plugin-annotation']);
}

const registry = new Map();

export function destroyCharts(prefix = '') {
  for (const [id, ch] of registry) {
    if (id.startsWith(prefix)) {
      ch.destroy();
      registry.delete(id);
    }
  }
}

function keep(id, ch) {
  registry.get(id)?.destroy();
  registry.set(id, ch);
  return ch;
}

/** Read theme tokens from CSS so charts follow light/dark. */
export function theme() {
  const cs = getComputedStyle(document.documentElement);
  const v = (n) => cs.getPropertyValue(n).trim();
  return {
    surface: v('--surface'),
    ink: v('--ink'),
    ink2: v('--ink-2'),
    muted: v('--muted'),
    grid: v('--grid'),
    axis: v('--axis'),
    accentInk: v('--accent-ink-text'),
    s1: v('--series-1'),
    s2: v('--series-2'),
    parent: v('--series-parent'),
    status: { ok: v('--ok'), warn: v('--warn'), bad: v('--bad'), neutral: v('--series-1'), na: v('--muted') },
    font: v('--font-body') || 'Sarabun, sans-serif',
  };
}

function base() {
  const t = theme();
  Chart.defaults.font.family = t.font;
  Chart.defaults.font.size = 14;
  Chart.defaults.color = t.muted;
  return t;
}

const animation = () => (reduceMotion() ? false : { duration: 450 });

function tooltipStyle(t) {
  return {
    backgroundColor: t.surface,
    titleColor: t.ink,
    bodyColor: t.ink2,
    borderColor: t.axis,
    borderWidth: 1,
    padding: 10,
    titleFont: { weight: '600', size: 15 },
    bodyFont: { size: 14 },
    displayColors: true,
    boxPadding: 4,
  };
}

/** Text with a surface-coloured plate behind it so it stays readable over lines. */
function plateText(ctx, text, x, y, t) {
  const w = ctx.measureText(text).width;
  const align = ctx.textAlign;
  const left = align === 'center' ? x - w / 2 : align === 'right' ? x - w : x;
  ctx.save();
  ctx.fillStyle = t.surface;
  ctx.globalAlpha = 0.85;
  ctx.fillRect(left - 3, y - 10, w + 6, 20);
  ctx.restore();
  ctx.fillText(text, x, y);
}

function withAlpha(hex, a) {
  const m = hex.replace('#', '');
  if (m.length !== 6) return hex;
  const n = parseInt(m, 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
}

/**
 * Horizontal bar chart of child areas.
 * items: [{code, name, value, num, den, status, small, home, drill}]
 */
export function barChart(canvas, { items, target, targetNote, onPick, id }) {
  const t = base();
  const colors = items.map((d) => {
    const c = t.status[d.status] ?? t.s1;
    return d.small ? withAlpha(c, 0.3) : c;
  });
  const maxV = Math.max(...items.map((d) => d.value ?? 0), target ?? 0);
  const niceMax = maxV > 100 ? Math.ceil(maxV / 10) * 10 : Math.min(100, Math.ceil((maxV * 1.08) / 10) * 10 || 10);

  const labelPlugin = {
    id: 'valueLabels',
    afterDatasetsDraw(chart) {
      const { ctx } = chart;
      const meta = chart.getDatasetMeta(0);
      ctx.save();
      ctx.textBaseline = 'middle';
      meta.data.forEach((bar, i) => {
        const d = items[i];
        const icon = STATUS_ICON[d.status] ?? '';
        let text = `${icon ? icon + ' ' : ''}${fmtPct(d.value)}`;
        if (d.small) text += '  n<20';
        ctx.font = `600 14px ${t.font}`;
        ctx.fillStyle = d.small ? t.muted : t.ink;
        plateText(ctx, text, bar.x + 6, bar.y, t);
      });
      ctx.restore();
    },
  };

  const annotations = {};
  if (typeof target === 'number') {
    annotations.target = {
      type: 'line',
      xMin: target,
      xMax: target,
      borderColor: t.ink2,
      borderWidth: 2,
      borderDash: [6, 4],
    };
  }
  // Target caption drawn above the plot area so it never collides with bar labels.
  const targetCaption = {
    id: 'targetCaption',
    afterDraw(chart) {
      if (typeof target !== 'number') return;
      const { ctx, chartArea, scales } = chart;
      const x = scales.x.getPixelForValue(target);
      ctx.save();
      ctx.font = `600 13px ${t.font}`;
      ctx.fillStyle = t.ink;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'bottom';
      ctx.fillText(`เป้า ${target}%${targetNote ? '*' : ''}`, x, chartArea.top - 4);
      ctx.restore();
    },
  };

  const ch = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: items.map((d) => d.name),
      datasets: [
        {
          data: items.map((d) => d.value),
          backgroundColor: colors,
          hoverBackgroundColor: colors,
          borderRadius: 4,
          borderSkipped: 'start',
          maxBarThickness: 24,
          barPercentage: 0.8,
          categoryPercentage: 0.9,
        },
      ],
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      animation: animation(),
      layout: { padding: { right: 110, top: 22 } },
      interaction: { mode: 'y', intersect: false },
      scales: {
        x: {
          min: 0,
          max: niceMax,
          grid: { color: t.grid },
          border: { color: t.axis },
          ticks: { color: t.muted, callback: (v) => `${v}%` },
        },
        y: {
          grid: { display: false },
          border: { color: t.axis },
          ticks: {
            autoSkip: false,
            color: (c) => (items[c.index]?.home ? t.accentInk : t.ink2),
            font: (c) => ({ weight: items[c.index]?.home ? '700' : '400', size: 14 }),
            callback: (v, i) => (items[i]?.home ? `▸ ${items[i].name}` : items[i]?.name),
          },
        },
      },
      plugins: {
        legend: { display: false },
        annotation: { annotations },
        tooltip: {
          ...tooltipStyle(t),
          displayColors: false,
          callbacks: {
            title: (els) => items[els[0].dataIndex]?.name ?? '',
            label: (el) => {
              const d = items[el.dataIndex];
              return `${fmtPct(d.value)}  (${fmtFrac(d.num, d.den)})${d.small ? '  · n<20' : ''}`;
            },
            footer: (els) => {
              const d = items[els[0].dataIndex];
              return d.drill ? 'คลิกเพื่อเจาะลึก' : d.pickHint || 'ไม่มีข้อมูลเจาะลึก';
            },
          },
          footerColor: t.muted,
          footerFont: { weight: '400', size: 13 },
        },
      },
      onHover: (evt, els) => {
        const d = els[0] ? items[els[0].index] : null;
        evt.native.target.style.cursor = d && (d.drill || d.pickHint) ? 'pointer' : 'default';
      },
      onClick: (evt, els) => {
        if (els[0]) onPick?.(items[els[0].index]);
      },
    },
    plugins: [labelPlugin, targetCaption],
  });
  return keep(id, ch);
}

/**
 * Line chart over years. series: [{label, values, nd:[{num,den}], kind:'scope'|'parent'|'target'}]
 */
export function trendChart(canvas, { labels, series, id }) {
  const t = base();
  const all = series.flatMap((s) => s.values).filter((v) => typeof v === 'number');
  const lo = Math.min(...all);
  const hi = Math.max(...all);
  const pad = Math.max(2, (hi - lo) * 0.25);
  const style = {
    scope: { color: t.s1, width: 2, dash: [], radius: 5, alpha: 1 },
    parent: { color: t.parent, width: 2, dash: [], radius: 4, alpha: 1 },
    target: { color: t.ink2, width: 2, dash: [6, 4], radius: 0, alpha: 1 },
  };
  const datasets = series.map((s) => {
    const st = style[s.kind];
    return {
      label: s.label,
      data: s.values,
      borderColor: st.color,
      backgroundColor: st.color,
      borderWidth: st.width,
      borderDash: st.dash,
      pointRadius: st.radius,
      pointHoverRadius: st.radius + 2,
      pointBorderColor: t.surface,
      pointBorderWidth: 2,
      pointStyle: s.kind === 'target' ? 'line' : 'circle',
      tension: 0,
      spanGaps: false,
      _nd: s.nd,
      _kind: s.kind,
    };
  });

  const scopeIdx = series.findIndex((s) => s.kind === 'scope');
  const labelPlugin = {
    id: 'scopeLabels',
    afterDatasetsDraw(chart) {
      if (scopeIdx < 0) return;
      const { ctx } = chart;
      const meta = chart.getDatasetMeta(scopeIdx);
      ctx.save();
      ctx.font = `600 14px ${t.font}`;
      ctx.fillStyle = t.ink;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      meta.data.forEach((pt, i) => {
        const v = series[scopeIdx].values[i];
        if (typeof v === 'number') plateText(ctx, fmtPct(v), pt.x, pt.y - 16, t);
      });
      ctx.restore();
    },
  };

  const ch = new Chart(canvas, {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: animation(),
      layout: { padding: { top: 18, left: 8, right: 16 } },
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: { grid: { display: false }, border: { color: t.axis }, ticks: { color: t.ink2, font: { size: 14 } }, offset: true },
        y: {
          suggestedMin: Math.max(0, Math.floor(lo - pad)),
          suggestedMax: Math.min(100, Math.ceil(hi + pad)),
          grid: { color: t.grid },
          border: { display: false },
          ticks: { color: t.muted, callback: (v) => `${v}%` },
        },
      },
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: t.ink2, boxWidth: 24, boxHeight: 3, padding: 16, font: { size: 14 } },
        },
        tooltip: {
          ...tooltipStyle(t),
          callbacks: {
            label: (el) => {
              const ds = el.dataset;
              const nd = ds._nd?.[el.dataIndex];
              const frac = nd && nd.den != null ? `  (${fmtFrac(nd.num, nd.den)})` : '';
              return `${ds.label}: ${fmtPct(el.raw)}${frac}`;
            },
          },
        },
      },
    },
    plugins: [labelPlugin],
  });
  return keep(id, ch);
}

/**
 * Monthly cumulative progress. series: [{label, values, nd, colorKey}]
 */
export function monthlyChart(canvas, { labels, series, target, targetNote, latestIdx, id }) {
  const t = base();
  const colors = { s1: t.s1, s2: t.s2 };
  const datasets = series.map((s) => ({
    label: s.label,
    data: s.values,
    borderColor: colors[s.colorKey],
    backgroundColor: colors[s.colorKey],
    borderWidth: 2,
    pointRadius: s.values.map((_, i) => (i === latestIdx ? 6 : 3)),
    pointHoverRadius: 7,
    pointBorderColor: t.surface,
    pointBorderWidth: 2,
    tension: 0,
    spanGaps: true,
    _nd: s.nd,
  }));
  const hi = Math.max(100, ...series.flatMap((s) => s.values).filter((v) => typeof v === 'number'));

  const annotations = {};
  if (typeof target === 'number') {
    annotations.target = {
      type: 'line',
      yMin: target,
      yMax: target,
      borderColor: t.ink2,
      borderWidth: 2,
      borderDash: [6, 4],
      label: {
        display: true,
        content: `เป้า ${target}%${targetNote ? '*' : ''}`,
        position: 'start',
        backgroundColor: t.surface,
        color: t.ink,
        font: { weight: '600', size: 13 },
        padding: 4,
      },
    };
  }
  if (latestIdx >= 0) {
    annotations.latest = {
      type: 'line',
      xMin: latestIdx,
      xMax: latestIdx,
      borderColor: t.axis,
      borderWidth: 1,
      label: {
        display: true,
        content: `ล่าสุด ${labels[latestIdx]}`,
        position: 'start',
        backgroundColor: t.surface,
        color: t.ink2,
        font: { size: 13 },
        padding: 4,
      },
    };
  }

  const endLabels = {
    id: 'endLabels',
    afterDatasetsDraw(chart) {
      if (latestIdx < 0) return;
      const { ctx } = chart;
      ctx.save();
      ctx.font = `600 14px ${t.font}`;
      ctx.fillStyle = t.ink;
      ctx.textAlign = 'right';
      ctx.textBaseline = 'middle';
      const pts = series.map((s, i) => ({ v: s.values[latestIdx], pt: chart.getDatasetMeta(i).data[latestIdx] }));
      pts.forEach(({ v, pt }, i) => {
        if (typeof v !== 'number' || !pt) return;
        const other = pts[1 - i];
        const below = other && typeof other.v === 'number' && other.v > v;
        plateText(ctx, fmtPct(v), pt.x - 10, pt.y + (below ? 16 : -16), t);
      });
      ctx.restore();
    },
  };

  const ch = new Chart(canvas, {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: animation(),
      layout: { padding: { top: 24, right: 12 } },
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: { grid: { display: false }, border: { color: t.axis }, ticks: { color: t.ink2 } },
        y: {
          min: 0,
          max: Math.ceil(hi / 10) * 10,
          grid: { color: t.grid },
          border: { display: false },
          ticks: { color: t.muted, callback: (v) => `${v}%` },
        },
      },
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: t.ink2, usePointStyle: true, boxWidth: 18, padding: 16, font: { size: 14 } },
        },
        annotation: { annotations },
        tooltip: {
          ...tooltipStyle(t),
          callbacks: {
            label: (el) => {
              const nd = el.dataset._nd?.[el.dataIndex];
              const frac = nd && nd.den != null ? `  (${fmtFrac(nd.num, nd.den)})` : '';
              return `${el.dataset.label}: ${fmtPct(el.raw)}${frac}`;
            },
          },
        },
      },
    },
    plugins: [endLabels],
  });
  return keep(id, ch);
}
