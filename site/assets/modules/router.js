// Hash routing: #/<indicator>/<year>/<level>/<scopeCode>
import { LEVELS } from './data.js';

export function defaultRoute(index) {
  const first = index.home?.path?.[0];
  const indicator = index.indicators.dspm ? 'dspm' : Object.keys(index.indicators)[0];
  return { indicator, year: index.currentYear, level: first?.level ?? 'country', scope: first?.code ?? 'TH' };
}

/** Parse the current hash; returns null when structurally invalid (unknown indicator/year/level). */
export function parseHash(hash, index) {
  const parts = String(hash || '')
    .replace(/^#\/?/, '')
    .split('/')
    .filter(Boolean)
    .map(decodeURIComponent);
  if (parts.length !== 4) return null;
  const [indicator, yearStr, level, scope] = parts;
  const year = Number(yearStr);
  if (!index.indicators[indicator]) return null;
  if (!index.years.includes(year)) return null;
  if (!LEVELS.includes(level)) return null;
  if (!/^[A-Za-z0-9]{1,10}$/.test(scope)) return null;
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
