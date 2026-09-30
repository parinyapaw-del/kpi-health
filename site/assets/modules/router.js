// Hash routing: #/<indicator>/<year>/<level>/<code>  (levels: region | province | district)
import { ROUTE_LEVELS, findTreeNode } from './data.js';

export function defaultRoute(index) {
  const indicator = index.indicators.dspm ? 'dspm' : Object.keys(index.indicators)[0];
  const home = index.home ?? { level: 'region', code: '4' };
  return { indicator, year: Number(index.currentYear), level: home.level, scope: String(home.code) };
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
