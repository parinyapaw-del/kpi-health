// Data layer: fetches index.json + dataset files (relative to the page) and caches them in memory.
// Everything indicator-specific comes from index.json metadata.

const BASE = '../data/angthong/';
let index = null;
const fileCache = new Map(); // file -> Promise<json|null>

export const LEVELS = ['country', 'region', 'province', 'district'];
export const CHILD_LEVEL = { country: 'region', region: 'province', province: 'district', district: 'subdistrict' };
export const LEVEL_NAME = {
  country: 'ประเทศ',
  region: 'เขตสุขภาพ',
  province: 'จังหวัด',
  district: 'อำเภอ',
  subdistrict: 'ตำบล',
};
/** Prefix used when a child row name is put into a sentence. Regions already carry "เขตสุขภาพที่". */
export const ROW_PREFIX = { region: '', province: 'จังหวัด', district: 'อำเภอ', subdistrict: 'ตำบล' };

export async function loadIndex() {
  const res = await fetch(`${BASE}index.json`, { cache: 'no-cache' });
  if (!res.ok) throw new Error(`โหลด index.json ไม่สำเร็จ (HTTP ${res.status})`);
  index = await res.json();
  return index;
}

export const getIndex = () => index;

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
  if (row.groups) return row.groups[groupKey] ?? row.groups.total ?? null;
  return row.metrics ?? null;
}

export function targetFor(ind, year) {
  const key = ind.targets_key ?? ind.id;
  const t = index?.targets?.[key]?.[String(year)];
  return t && typeof t.value === 'number' ? t : null;
}

export function tableLabel(ind, key) {
  return ind.table?.find((c) => c.key === key)?.label ?? key;
}

/** Table label up to its first "(" — e.g. "อัตราการเข้าถึงบริการ ปีงบประมาณปัจจุบัน". */
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

export function findTreeNode(level, code) {
  return walk(index?.tree, (n) => n.level === level && String(n.code) === String(code));
}

/** A child row can be drilled into when the tree has it with children, or a dataset exists for it. */
export function canDrill(indicator, year, level, code) {
  if (!LEVELS.includes(level)) return false;
  if (findDataset(indicator, year, level, code)) return true;
  const hit = findTreeNode(level, code);
  return Boolean(hit && hit.node.children && hit.node.children.length);
}

/** Home-path code at a level (e.g. region → "4"), or null. */
export function homeCodeAt(level) {
  return index?.home?.path?.find((p) => p.level === level)?.code ?? null;
}

/**
 * Breadcrumb trail for a scope: [{level, code, name}] from country down to the scope.
 * Uses home.path first; off-path scopes are resolved through the parent level's datasets.
 */
export async function resolveTrail(indicator, year, level, code, depth = 0) {
  const path = index.home.path;
  const li = LEVELS.indexOf(level);
  if (li < 0) return [];
  const onPath = path[li] && path[li].level === level && String(path[li].code) === String(code);
  if (onPath) return path.slice(0, li + 1).map((p) => ({ ...p }));
  if (li === 0 || depth > 4) return [{ level, code, name: String(code) }];

  const parentLevel = LEVELS[li - 1];
  // Prefer datasets of the current indicator/year, then any indicator/year.
  const cands = index.datasets
    .filter((d) => d.level === parentLevel && (d.kind ?? 'level') === 'level')
    .sort((a, b) => score(b) - score(a));
  function score(d) {
    return (d.indicator === indicator ? 2 : 0) + (Number(d.year) === Number(year) ? 1 : 0);
  }
  for (const d of cands) {
    const json = await loadFile(d.file);
    const row = json?.rows?.find((r) => String(r.code) === String(code));
    if (row) {
      const up = await resolveTrail(indicator, year, parentLevel, d.scope, depth + 1);
      return [...up, { level, code, name: row.name }];
    }
  }
  const up = path.slice(0, li).map((p) => ({ ...p }));
  return [...up, { level, code, name: String(code) }];
}
