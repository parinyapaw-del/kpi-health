// Chart.js wrappers (Chart.js 4 + chartjs-plugin-annotation loaded as UMD globals).
// Every chart is a horizontal bar chart with a value label on every bar (no hover needed).
import { fmtPct, fmtND, isNum, STATUS_ICON } from './format.js';
import { reduceMotion, isMobile } from './state.js';

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
    accent: v('--accent'),
    accentInk: v('--accent-ink-text'),
    neutral: v('--series-1'),
    fillBase: v('--fill-base'),
    fillOn: v('--fill-on'),
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

/** Row pitch in px (desktop: name on the axis; mobile: name + label on a line above the bar). */
export const ROW_PX = { desktop: 34, mobile: 54 };
/** Chart box height for n rows: never squeezed — rows × pitch + axis/caption padding. */
export function chartHeight(n) {
  const m = isMobile();
  return Math.max(120, n * (m ? ROW_PX.mobile : ROW_PX.desktop) + (m ? 56 : 62));
}

function withAlpha(color, a) {
  const m = color.replace('#', '');
  if (m.length !== 6) return color;
  const n = parseInt(m, 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
}

/** Text with a surface-coloured plate behind it so it stays readable over grid/target lines. */
function plateText(ctx, text, x, y, t, plateH = 20) {
  const w = ctx.measureText(text).width;
  const align = ctx.textAlign;
  const left = align === 'center' ? x - w / 2 : align === 'right' ? x - w : x;
  const top = ctx.textBaseline === 'bottom' ? y - plateH + 2 : y - plateH / 2;
  const fill = ctx.fillStyle;
  ctx.save();
  ctx.fillStyle = t.surface;
  ctx.globalAlpha = 0.88;
  ctx.fillRect(left - 3, top, w + 6, plateH);
  ctx.restore();
  ctx.fillStyle = fill;
  ctx.fillText(text, x, y);
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

/**
 * Horizontal bar chart.
 * items: [{code, name, value, num, den, status, small, highlight, drill, nodata}]
 * style: 'status' (bar colour = ok/warn/bad, neutral without target)
 *        'fill'   (full-width light-red base = expected 100%, green overlay = value)
 */
export function barChart(canvas, { id, items, target, targetNote, style = 'status', onPick }) {
  const t = base();
  const mobile = isMobile();
  const fill = style === 'fill';
  const barPx = mobile ? 16 : 22;
  const maxV = Math.max(100, ...items.map((d) => (isNum(d.value) ? d.value : 0)));
  const xMax = maxV > 100 ? Math.ceil(maxV / 10) * 10 : 100;

  const mainColor = (d) => {
    const c = fill ? t.fillOn : t.status[d.status] ?? t.neutral;
    return d.small ? withAlpha(c, 0.32) : c;
  };
  const mainColors = items.map(mainColor);

  const datasets = [
    {
      label: 'value',
      data: items.map((d) => (isNum(d.value) ? d.value : null)),
      backgroundColor: mainColors,
      hoverBackgroundColor: mainColors,
      borderRadius: 4,
      borderSkipped: 'start',
      barThickness: barPx,
      grouped: false,
      order: 1,
    },
  ];
  if (fill) {
    const baseColors = items.map((d) => (d.nodata ? 'transparent' : withAlpha(t.fillBase, d.small ? 0.4 : 1)));
    datasets.push({
      label: 'base',
      data: items.map((d) => (d.nodata ? null : 100)),
      backgroundColor: baseColors,
      hoverBackgroundColor: baseColors,
      borderRadius: 4,
      borderSkipped: 'start',
      barThickness: barPx,
      grouped: false,
      order: 2,
    });
  }

  const labelText = (d, sep) => {
    if (d.nodata) return 'ไม่มีข้อมูล';
    const icon = !fill && STATUS_ICON[d.status] ? `${STATUS_ICON[d.status]} ` : '';
    const nd = sep === '·' ? ` · ${fmtND(d.num, d.den)}` : ` (${fmtND(d.num, d.den)})`;
    return `${icon}${fmtPct(d.value)}${nd}${d.small ? '  n<20' : ''}`;
  };

  // Value labels at the bar end (desktop) or on a line above the bar (mobile), plus the highlight frame.
  const labelPlugin = {
    id: 'valueLabels',
    afterDatasetsDraw(chart) {
      const { ctx, chartArea, scales } = chart;
      const x0 = scales.x.getPixelForValue(0);
      const pitch = items.length > 1 ? Math.abs(scales.y.getPixelForValue(1) - scales.y.getPixelForValue(0)) : chartArea.bottom - chartArea.top;
      ctx.save();
      items.forEach((d, i) => {
        const y = scales.y.getPixelForValue(i);
        if (d.highlight) {
          ctx.save();
          ctx.strokeStyle = t.accent;
          ctx.lineWidth = 2;
          const left = mobile ? chartArea.left - 4 : scales.y.left - 2;
          const h = pitch - 4;
          const top = mobile ? y - h + barPx / 2 + 4 : y - h / 2;
          roundRect(ctx, left, top, chart.width - left - 2, h, 6);
          ctx.stroke();
          ctx.restore();
        }
        ctx.font = `600 14px ${t.font}`;
        ctx.fillStyle = d.small || d.nodata ? t.muted : t.ink;
        if (mobile) {
          ctx.textBaseline = 'bottom';
          const ty = y - barPx / 2 - 3;
          ctx.textAlign = 'right';
          const lbl = labelText(d, '·');
          plateText(ctx, lbl, chartArea.right, ty, t);
          const lblW = ctx.measureText(lbl).width;
          ctx.textAlign = 'left';
          ctx.font = `${d.highlight ? 700 : 500} 14px ${t.font}`;
          ctx.fillStyle = d.highlight ? t.accentInk : t.ink2;
          let name = d.highlight ? `▸ ${d.name}` : d.name;
          const room = chartArea.right - chartArea.left - lblW - 12;
          while (name.length > 3 && ctx.measureText(name).width > room) name = `${name.slice(0, -2)}…`;
          plateText(ctx, name, chartArea.left, ty, t);
        } else {
          ctx.textBaseline = 'middle';
          ctx.textAlign = 'left';
          const end = fill && !d.nodata ? scales.x.getPixelForValue(Math.max(100, d.value ?? 0)) : scales.x.getPixelForValue(isNum(d.value) ? d.value : 0);
          plateText(ctx, labelText(d, '()'), (d.nodata ? x0 : end) + 6, y, t);
        }
      });
      ctx.restore();
    },
  };

  // Right gutter (desktop) = widest bar-end label, so labels never clip at 100%.
  let gutter = 190;
  if (!mobile) {
    const m = document.createElement('canvas').getContext('2d');
    m.font = `600 14px ${t.font}`;
    gutter = Math.ceil(Math.max(60, ...items.map((d) => m.measureText(labelText(d, '()')).width))) + 16;
  }

  const annotations = {};
  if (typeof target === 'number') {
    annotations.target = {
      type: 'line',
      xMin: target,
      xMax: target,
      borderColor: t.ink2,
      borderWidth: 2,
      borderDash: [6, 4],
      drawTime: 'afterDatasetsDraw',
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
      ctx.font = `700 13px ${t.font}`;
      ctx.fillStyle = t.ink;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'bottom';
      ctx.fillText(`เป้า ${target}%${targetNote ? '*' : ''}`, x, chartArea.top - (mobile ? 2 : 4));
      ctx.restore();
    },
  };

  // Whole row is the hit target (bar, area name and label) — Chart.js' own onClick only fires inside the plot area.
  const rowAt = (chart, e) => {
    const { chartArea, scales } = chart;
    const rect = chart.canvas.getBoundingClientRect();
    const y = e.clientY - rect.top;
    if (y < chartArea.top - 4 || y > chartArea.bottom + 4) return null;
    const i = Math.round(scales.y.getValueForPixel(y));
    return items[i] ?? null;
  };

  const ch = new Chart(canvas, {
    type: 'bar',
    data: { labels: items.map((d) => d.name), datasets },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      animation: reduceMotion() ? false : { duration: 400 },
      layout: { padding: mobile ? { top: 22, right: 2, left: 2 } : { right: gutter, top: 24 } },
      interaction: { mode: 'y', intersect: false },
      scales: {
        x: {
          min: 0,
          max: xMax,
          grid: { color: t.grid },
          border: { color: t.axis },
          ticks: { color: t.muted, stepSize: mobile ? 25 : 10, maxRotation: 0, autoSkip: true, autoSkipPadding: 8, callback: (v) => `${v}%` },
        },
        y: {
          display: !mobile,
          grid: { display: false },
          border: { color: t.axis },
          ticks: {
            autoSkip: false,
            color: (c) => (items[c.index]?.highlight ? t.accentInk : items[c.index]?.nodata ? t.muted : t.ink2),
            font: (c) => ({ weight: items[c.index]?.highlight ? '700' : '500', size: 14 }),
            callback: (v, i) => (items[i]?.highlight ? `▸ ${items[i].name}` : items[i]?.name),
          },
        },
      },
      plugins: {
        legend: { display: false },
        annotation: { annotations },
        tooltip: {
          backgroundColor: t.surface,
          titleColor: t.ink,
          bodyColor: t.ink2,
          footerColor: t.muted,
          borderColor: t.axis,
          borderWidth: 1,
          padding: 10,
          titleFont: { weight: '600', size: 15 },
          bodyFont: { size: 14 },
          footerFont: { weight: '400', size: 13 },
          displayColors: false,
          filter: (el) => el.datasetIndex === 0,
          callbacks: {
            title: (els) => items[els[0].dataIndex]?.name ?? '',
            label: (el) => labelText(items[el.dataIndex], '()'),
            footer: (els) => (items[els[0].dataIndex]?.drill ? 'คลิกเพื่อเจาะลึก' : ''),
          },
        },
      },
    },
    plugins: [labelPlugin, targetCaption],
  });
  canvas.addEventListener('click', (e) => {
    const d = rowAt(ch, e);
    if (d?.drill) onPick?.(d);
  });
  canvas.addEventListener('mousemove', (e) => {
    canvas.style.cursor = rowAt(ch, e)?.drill ? 'pointer' : 'default';
  });
  return keep(id, ch);
}
