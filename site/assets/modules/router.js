// Hash routing: #/<indicator>/<year>/<level>/<code>  (levels: region | province | district)
import { ROUTE_LEVELS, findTreeNode, findDataset, homeOf } from './data.js';

/**
 * Landing route: the first indicator (dspm first) that has a dataset at the home level for currentYear,
 * else the latest year that has one — so the landing page is never the no-data box while any data exists.
 * Only when no home dataset exists at all does it return dspm/currentYear (the no-data page).
 */
export function defaultRoute(index) {
  const ids = Object.keys(index.indicators);
  if (index.indicators.dspm) ids.sort((a, b) => (b === 'dspm') - (a === 'dspm')); // stable: dspm first
  const home = homeOf(index);
  const cur = Number(index.currentYear);
  const years = [cur, ...index.years.map(Number).filter((y) => y !== cur).sort((a, b) => b - a)];
  const route = (indicator, year) => ({ indicator, year, level: home.level, scope: String(home.code) });
  for (const year of years) {
    for (const id of ids) if (findDataset(id, year, home.level, home.code)) return route(id, year);
  }
  return route(ids[0], cur);
}

/**
 * Parse the current hash. Returns null when invalid (unknown indicator/year/level, a country route,
 * or an area code that is not in the region-4 tree) → the caller redirects to the default route.
 */
export function parseHash(hash, index) {
  const parts = String(hash || '')
    .replace(/^#\/?/, '')
    .split('/')
    .filter(Boolean)
    .map((p) => {
      try {
        return decodeURIComponent(p);
      } catch {
        return '';
      }
    });
  if (parts.length !== 4) return null;
  const [indicator, yearStr, level, scope] = parts;
  const year = Number(yearStr);
  if (!Object.prototype.hasOwnProperty.call(index.indicators, indicator)) return null;
  if (!index.years.map(Number).includes(year)) return null;
  if (!ROUTE_LEVELS.includes(level)) return null;
  if (!/^[A-Za-z0-9]{1,10}$/.test(scope)) return null;
  if (!findTreeNode(level, scope)) return null;
  return { indicator, year, level, scope };
}

export function toHash(r) {
  return `#/${r.indicator}/${r.year}/${r.level}/${encodeURIComponent(r.scope)}`;
}

export function go(r) {
  const h = toHash(r);
  if (location.hash === h) window.dispatchEvent(new HashChangeEvent('hashchange'));
  else location.hash = h;
}

export function replace(r) {
  history.replaceState(null, '', toHash(r));
}
