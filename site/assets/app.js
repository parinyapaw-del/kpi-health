// Entry point: routing → data → components.
import { loadIndex, getIndex, setIndex, findDataset, loadFile, load, trailFor, targetFor, latestAsOf, homeOf, LEVEL_NAME } from './modules/data.js';
import { parseHash, defaultRoute, replace, go } from './modules/router.js';
import { state, getTheme, setTheme, isMobile } from './modules/state.js';
import { destroyCharts } from './modules/charts.js';
import { esc } from './modules/format.js';
import { applyOverride, loadOverride, listenDraft } from './modules/configOverride.js';
import { trackRoute, onCounts, getCounts } from './modules/hit.js';
import { headerHTML } from './modules/components/header.js';
import { footerHTML, countsText } from './modules/components/footer.js';
import { breadcrumbHTML } from './modules/components/breadcrumb.js';
import { groupTabsHTML } from './modules/components/groupTabs.js';
import { headlineHTML, cardsHTML } from './modules/components/kpiCards.js';
import { barItems, barsPanelHTML, mountBars, childBarsPanel } from './modules/components/childBars.js';
import { heatmapHTML } from './modules/components/heatmap.js';
import { fullTableHTML, downloadCSV } from './modules/components/fullTable.js';
import { noDataHTML } from './modules/components/noData.js';

const $header = document.getElementById('site-header');
const $main = document.getElementById('main');
const $footer = document.getElementById('site-footer');
let token = 0;
let ctx = null;
let lastScopeKey = null;

function currentRoute(index) {
  const r = parseHash(location.hash, index);
  if (r) return r;
  const d = defaultRoute(index); // invalid route or a country route → region 4
  replace(d);
  return d;
}

/** Page heading shared by the no-data box and every level: eyebrow (level · fiscal year) + area name. */
function scopeHeadHTML(route, name) {
  const eyebrow = `ระดับ${LEVEL_NAME[route.level]} · ปีงบ ${route.year}`;
  return `<div class="scope-head"><p class="eyebrow">${esc(eyebrow)}</p><h1>${esc(name)}</h1></div>`;
}

async function render() {
  const my = ++token;
  const stale = () => my !== token;
  const index = getIndex();
  const route = currentRoute(index);
  const ind = index.indicators[route.indicator];

  if (ind.groups && !ind.groups.some((g) => g.key === state.groupKey)) state.groupKey = ind.groups[0].key;
  const groupKey = ind.groups ? state.groupKey : null;
  const groupLabel = ind.groups ? ind.groups.find((g) => g.key === groupKey)?.label : '';

  // Drill / breadcrumb (level or scope changed) → start the new page at the top.
  const scopeKey = `${route.level}/${route.scope}`;
  if (lastScopeKey && lastScopeKey !== scopeKey) window.scrollTo({ top: 0, behavior: 'auto' });
  lastScopeKey = scopeKey;

  const ds = findDataset(route.indicator, route.year, route.level, route.scope);
  const trail = trailFor(route.level, route.scope);
  const here = trail[trail.length - 1];
  const data = ds ? await loadFile(ds.file) : null;
  if (stale()) return;

  $header.innerHTML = headerHTML(index, route, data ? ds : null, trail);
  $footer.innerHTML = footerHTML(index, data ? ds.asOf : latestAsOf(route.year), getCounts());
  document.title = `${here?.name ?? ''} · ${ind.short ?? ind.id} ${route.year} · ${index.name}`;
  if (window.self === window.top) trackRoute(`${route.indicator}/${route.level}/${route.scope}`); // not the admin preview

  // Keep page height while swapping content so the scroll position does not jump.
  $main.style.minHeight = `${$main.offsetHeight}px`;
  destroyCharts();

  if (!data) {
    ctx = null;
    $main.innerHTML = `${breadcrumbHTML(trail, route)}
      ${scopeHeadHTML(route, here?.name ?? route.scope)}
      ${noDataHTML(index, route, trail)}`;
    $main.style.minHeight = '';
    return;
  }

  const parentRef = data.scope.parent;
  const parentData = parentRef ? await load(route.indicator, route.year, parentRef.level, parentRef.code) : null;
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
  };

  const child = childBarsPanel(ctx);
  const onDrill = (d) => go({ ...route, level: d.childLevel, scope: d.code });

  if (route.level === homeOf(index).level) {
    // Home page = region 4: headline + cards → 13 regions → 8 provinces → heatmap → table.
    const regionItems = parentData ? barItems(ctx, parentData, { highlight: route.scope }) : [];
    const regionPanel = parentData
      ? barsPanelHTML(ctx, {
          id: 'regions',
          title: `เทียบ ${regionItems.length} เขตสุขภาพทั่วประเทศ`,
          sub: groupLabel,
          items: regionItems,
          highlightLabel: `กรอบ = ${data.scope.name}`,
        })
      : '';
    $main.innerHTML = `
      ${breadcrumbHTML(trail, route)}
      ${scopeHeadHTML(route, data.scope.name)}
      ${groupTabsHTML(ind, groupKey)}
      <div class="grid-top">${headlineHTML(ctx)}${cardsHTML(ctx)}</div>
      <div class="grid-2">${regionPanel}${child.html}</div>
      ${heatmapHTML(ctx)}
      ${fullTableHTML(ctx)}`;
    $main.style.minHeight = '';
    if (parentData) mountBars(ctx, { id: 'regions', items: regionItems });
    mountBars(ctx, { id: 'child', items: child.items, onDrill });
    return;
  }

  // Province / district: same head as the home page (headline card + cards) → heatmap → child bars → table.
  $main.innerHTML = `
    ${breadcrumbHTML(trail, route)}
    ${scopeHeadHTML(route, data.scope.name)}
    ${groupTabsHTML(ind, groupKey)}
    <div class="grid-top">${headlineHTML(ctx)}${cardsHTML(ctx)}</div>
    ${heatmapHTML(ctx)}
    ${child.html}
    ${fullTableHTML(ctx)}`;
  $main.style.minHeight = '';
  mountBars(ctx, { id: 'child', items: child.items, onDrill });
}

function rerender() {
  render().catch(showError);
}

/** Phones: condense the sticky header to tabs + one-line breadcrumb once the page scrolls (with hysteresis). */
function bindCondense() {
  let ticking = false;
  const update = () => {
    ticking = false;
    const y = window.scrollY;
    const on = $header.classList.contains('is-condensed');
    if (!isMobile()) {
      if (on) $header.classList.remove('is-condensed');
      return;
    }
    if (!on && y > 140) $header.classList.add('is-condensed');
    else if (on && y < 24) $header.classList.remove('is-condensed');
  };
  window.addEventListener(
    'scroll',
    () => {
      if (!ticking) {
        ticking = true;
        requestAnimationFrame(update);
      }
    },
    { passive: true },
  );
}

function bindEvents() {
  window.addEventListener('hashchange', rerender);
  document.addEventListener('click', (e) => {
    const t = e.target.closest('#theme-toggle, .gtab, #csv-btn, .sort-btn');
    if (!t) return;
    if (t.id === 'theme-toggle') {
      setTheme(getTheme() === 'dark' ? 'light' : 'dark');
      rerender();
    } else if (t.classList.contains('gtab')) {
      state.groupKey = t.dataset.group;
      rerender();
    } else if (t.classList.contains('sort-btn')) {
      if (!ctx || state.heatSort === t.dataset.sort) return;
      state.heatSort = t.dataset.sort;
      const panel = document.getElementById('panel-heat');
      if (panel) {
        panel.outerHTML = heatmapHTML(ctx);
        document.querySelector(`#panel-heat .sort-btn[data-sort="${state.heatSort}"]`)?.focus();
      }
    } else if (t.id === 'csv-btn' && ctx) {
      downloadCSV(ctx);
    }
  });
  // Chart layout differs on phones (label line above the bar) → re-render when crossing 600px.
  window.matchMedia('(max-width: 600px)').addEventListener('change', rerender);
  onCounts((c) => {
    const el = document.getElementById('hit-counts');
    if (el) el.textContent = countsText(c);
  });
  bindCondense();
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
    // index.json + the admin's KV override (§8.2) in parallel; a failed /api/config → repo values.
    const [pristine, { override }] = await Promise.all([loadIndex(), loadOverride()]);
    setIndex(applyOverride(pristine, override));
    listenDraft((draft) => {
      setIndex(applyOverride(pristine, draft));
      rerender();
    });
    bindEvents();
    await render();
  } catch (err) {
    showError(err);
  }
})();
