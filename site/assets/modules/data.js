// Data layer: fetches index.json + dataset files and caches them in memory.
// Everything indicator-specific comes from index.json metadata (schema 2).

const BASE = 'data/angthong/';
let index = null;
const fileCache = new Map(); // file -> Promise<json|null>

/** Home page = this area unless index.json provides `home` (single source for header, router and app). */
export const HOME_DEFAULT = { level: 'region', code: '4' };
export const homeOf = (idx) => idx?.home ?? HOME_DEFAULT;
/** Levels that have a page (country exists only as the 13-region dataset on the home page). */
export const ROUTE_LEVELS = ['region', 'province', 'district'];
export const CHILD_LEVEL = { country: 'region', region: 'province', province: 'district', district: 'subdistrict' };
export const LEVEL_NAME = {
  country: 'ประเทศ',
  region: 'เขตสุขภาพ',
  province: 'จังหวัด',
  district: 'อำเภอ',
  subdistrict: 'ตำบล',
};

export async function loadIndex() {
  const res = await fetch(`${BASE}index.json`, { cache: 'no-cache' });
  if (!res.ok) throw new Error(`โหลด index.json ไม่สำเร็จ (HTTP ${res.status})`);
  index = await res.json();
  return index;
}

export const getIndex = () => index;

/** Replace the in-memory index (index.json merged with the KV override, §8.2). */
export function setIndex(i) {
  index = i;
}

export function findDataset(indicator, year, level, scope, kind = 'level') {
  if (!index) return null;
  return (
    index.datasets.find(
      (d) =>
        d.indicator === indicator &&
        Number(d.year) === Number(year) &&
        d.level === level &&
        String(d.scope) === String(scope) &&
        (d.kind ?? 'level') === kind,
    ) ?? null
  );
}

export function loadFile(file) {
  if (!fileCache.has(file)) {
    const p = fetch(`${BASE}${file}`)
      .then((r) => (r.ok ? r.json() : null))
      .catch(() => null);
    fileCache.set(file, p);
  }
  return fileCache.get(file);
}

/** Load a dataset JSON by coordinates; resolves null when no dataset exists. */
export async function load(indicator, year, level, scope, kind = 'level') {
  const ds = findDataset(indicator, year, level, scope, kind);
  if (!ds) return null;
  return loadFile(ds.file);
}

/** The metric bag of a row for a group (DSPM) or the flat metrics (group-less indicators). */
export function vals(row, groupKey) {
  if (!row) return null;
  if (row.groups) return row.groups[groupKey ?? 'total'] ?? row.groups.total ?? null;
  return row.metrics ?? null;
}

/** Target for an indicator/year, or null when missing or `value: null` (Q33: "ยังไม่กำหนด"). */
export function targetFor(ind, year) {
  const key = ind.targets_key ?? ind.id;
  const t = index?.targets?.[key]?.[String(year)];
  return t && typeof t.value === 'number' ? t : null;
}

function tableLabel(ind, key) {
  return ind.table?.find((c) => c.key === key)?.label ?? key;
}

/** Table label up to its first "(" — e.g. "อัตราการเข้าถึงบริการ สะสม". */
export function shortLabel(ind, key) {
  const l = tableLabel(ind, key);
  const cut = l.indexOf('(');
  return (cut > 0 ? l.slice(0, cut) : l).trim();
}

function walk(node, fn, parents = []) {
  if (!node) return null;
  if (fn(node)) return { node, parents };
  for (const c of node.children ?? []) {
    const hit = walk(c, fn, [...parents, node]);
    if (hit) return hit;
  }
  return null;
}

/** Tree node (rooted at region 4) + its ancestors, or null. */
export function findTreeNode(level, code) {
  return walk(index?.tree, (n) => n.level === level && String(n.code) === String(code));
}

/** A child row is drillable only when a dataset exists for it (the tree alone is not enough). */
export function canDrill(indicator, year, level, code) {
  if (!ROUTE_LEVELS.includes(level)) return false;
  return Boolean(findDataset(indicator, year, level, code));
}

/** Breadcrumb trail [{level, code, name}] from region 4 down to the scope, from the tree. */
export function trailFor(level, code) {
  const hit = findTreeNode(level, code);
  if (!hit) return [];
  return [...hit.parents, hit.node].map((n) => ({ level: n.level, code: String(n.code), name: n.name }));
}

/** Latest asOf over all datasets of a year (footer fallback). */
export function latestAsOf(year) {
  const list = (index?.datasets ?? []).filter((d) => year == null || Number(d.year) === Number(year));
  return list.map((d) => d.asOf).filter(Boolean).sort().pop() ?? null;
}
