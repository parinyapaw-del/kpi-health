// Entry point: routing → data → components.
import { loadIndex, getIndex, findDataset, loadFile, load, resolveTrail, targetFor, LEVEL_NAME } from './modules/data.js';
import { parseHash, defaultRoute, replace, go } from './modules/router.js';
import { state, getTheme, setTheme } from './modules/state.js';
import { destroyCharts } from './modules/charts.js';
import { esc } from './modules/format.js';
import { headerHTML } from './modules/components/header.js';
import { breadcrumbHTML } from './modules/components/breadcrumb.js';
import { shortcutsHTML } from './modules/components/shortcuts.js';
import { groupTabsHTML } from './modules/components/groupTabs.js';
import { headlineHTML, cardsHTML } from './modules/components/kpiCards.js';
import { childBarsHTML, mountChildBars } from './modules/components/childBars.js';
import { trendHTML, mountTrend } from './modules/components/trend.js';
import { monthlyHTML, mountMonthly, loadMonthly } from './modules/components/monthly.js';
import { heatmapHTML } from './modules/components/heatmap.js';
import { weaknessHTML } from './modules/components/weakness.js';
import { fullTableHTML, downloadCSV } from './modules/components/fullTable.js';
import { noDataHTML } from './modules/components/noData.js';

const $header = document.getElementById('site-header');
const $main = document.getElementById('main');
let token = 0;
let ctx = null;
let mdata = null;

function currentRoute(index) {
  const r = parseHash(location.hash, index);
  if (r) return r;
  const d = defaultRoute(index);
  replace(d);
  return d;
}

let lastScopeKey = null;

async function render() {
  const my = ++token;
  const stale = () => my !== token;
  const index = getIndex();
  const route = currentRoute(index);
  const ind = index.indicators[route.indicator];

  if (ind.groups) {
    if (!ind.groups.some((g) => g.key === state.groupKey)) state.groupKey = ind.groups[0].key;
  }
  const groupKey = ind.groups ? state.groupKey : null;
  const groupLabel = ind.groups ? ind.groups.find((g) => g.key === groupKey)?.label : '';
  if (state.monthlyScope !== `${route.level}/${route.scope}`) {
    state.monthlyScope = `${route.level}/${route.scope}`;
    state.monthlyRow = '';
  }

  // Drill / breadcrumb (level or scope changed) → start the new page at the top (Q12: projector use)
  const scopeKey = `${route.level}/${route.scope}`;
  if (lastScopeKey && lastScopeKey !== scopeKey) window.scrollTo({ top: 0, behavior: 'auto' });
  lastScopeKey = scopeKey;

  const ds = findDataset(route.indicator, route.year, route.level, route.scope);
  const [data, trail] = await Promise.all([ds ? loadFile(ds.file) : null, resolveTrail(route.indicator, route.year, route.level, route.scope)]);
  if (stale()) return;

  $header.innerHTML = headerHTML(index, route, data ? ds : null);
  document.title = `${trail[trail.length - 1]?.name ?? ''} · ${ind.short} ${route.year} · ${index.name}`;

  const shortcuts = route.level === 'country' ? await shortcutsHTML(index, route) : '';
  if (stale()) return;

  const here = trail[trail.length - 1];
  const scopeHead = `<div class="scope-head">
      <p class="eyebrow">ระดับ${esc(LEVEL_NAME[route.level])} · ปีงบ ${route.year}</p>
      <h1>${esc(data?.scope?.name ?? here?.name ?? route.scope)}</h1>
      <p class="scope-ind">${esc(ind.name_th)}</p>
    </div>`;

  // Keep page height while swapping content so the scroll position does not jump.
  $main.style.minHeight = `${$main.offsetHeight}px`;
  destroyCharts();

  if (!data) {
    ctx = null;
    $main.innerHTML = breadcrumbHTML(trail, route) + scopeHead + shortcuts + noDataHTML(index, route, trail);
    $main.style.minHeight = '';
    return;
  }

  const parentRef = data.scope.parent;
  const [parentData, prevData, monthly] = await Promise.all([
    parentRef ? load(route.indicator, route.year, parentRef.level, parentRef.code) : null,
    load(route.indicator, route.year - 1, route.level, route.scope),
    loadMonthly({ ind, route }),
  ]);
  if (stale()) return;

  ctx = {
    index,
    route,
    ind,
    data,
    groupKey: groupKey ?? 'total',
    groupLabel,
    target: targetFor(ind, route.year),
    rules: { warnBand: index.colorRules?.warnBand ?? 5, smallN: index.colorRules?.smallN ?? 20 },
    parentData,
    prevData,
  };
  mdata = monthly;

  $main.innerHTML = `
    ${breadcrumbHTML(trail, route)}
    ${scopeHead}
    ${shortcuts}
    ${groupTabsHTML(ind, groupKey)}
    <div class="grid-top">${headlineHTML(ctx)}${cardsHTML(ctx)}</div>
    <div class="grid-2">${childBarsHTML(ctx)}${trendHTML(ctx)}</div>
    ${mdata ? monthlyHTML(ctx, mdata) : ''}
    <div class="grid-heat">${heatmapHTML(ctx)}${weaknessHTML(ctx)}</div>
    ${fullTableHTML(ctx)}`;
  $main.style.minHeight = '';

  const leafCodes = new Set((mdata?.rows ?? []).map((r) => String(r.code)));
  mountChildBars(ctx, {
    leafCodes,
    onDrill: (d) => go({ ...route, level: d.childLevel, scope: d.code }),
    onPickLeaf: (d) => {
      state.monthlyRow = d.code;
      const sel = document.getElementById('monthly-row');
      if (sel) sel.value = d.code;
      destroyCharts('monthly');
      mountMonthly(ctx, mdata);
      document.getElementById('panel-monthly')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    },
  });
  if (mdata) mountMonthly(ctx, mdata);
  await mountTrend(ctx, stale);
}

function bindEvents() {
  window.addEventListener('hashchange', () => render().catch(showError));
  document.addEventListener('click', (e) => {
    const t = e.target.closest('#theme-toggle, .gtab, #csv-btn');
    if (!t) return;
    if (t.id === 'theme-toggle') {
      setTheme(getTheme() === 'dark' ? 'light' : 'dark');
      render().catch(showError);
    } else if (t.classList.contains('gtab')) {
      state.groupKey = t.dataset.group;
      render().catch(showError);
    } else if (t.id === 'csv-btn' && ctx) {
      downloadCSV(ctx);
    }
  });
  document.addEventListener('change', (e) => {
    if (e.target.id === 'monthly-row' && ctx && mdata) {
      state.monthlyRow = e.target.value;
      destroyCharts('monthly');
      mountMonthly(ctx, mdata);
    }
  });
}

function showError(err) {
  console.error(err);
  $main.innerHTML = `<section class="nodata" role="alert"><h2>โหลดข้อมูลไม่สำเร็จ</h2><p>${esc(
    err?.message ?? err,
  )}</p><p>ลองโหลดหน้าใหม่อีกครั้ง</p></section>`;
}

(async function start() {
  setTheme(getTheme());
  if (!window.Chart) {
    showError(new Error('โหลด Chart.js จาก cdnjs ไม่สำเร็จ ตรวจการเชื่อมต่ออินเทอร์เน็ต'));
    return;
  }
  try {
    await loadIndex();
    bindEvents();
    await render();
  } catch (err) {
    showError(err);
  }
})();
