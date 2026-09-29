// In-memory UI state + theme persistence.
const THEME_KEY = 'kpi-health-theme';

export const state = {
  groupKey: 'total', // DSPM age-group tab (not in the hash)
  monthlyRow: '', // selected child row in the monthly chart ('' = whole scope)
  monthlyScope: '', // scope the monthlyRow belongs to
};

export function getTheme() {
  try {
    return localStorage.getItem(THEME_KEY) === 'dark' ? 'dark' : 'light';
  } catch {
    return 'light';
  }
}

export function setTheme(t) {
  document.documentElement.setAttribute('data-theme', t);
  try {
    localStorage.setItem(THEME_KEY, t);
  } catch {
    /* storage blocked: theme still applies for this visit */
  }
}

export const reduceMotion = () =>
  window.matchMedia('(max-width: 600px)').matches || window.matchMedia('(prefers-reduced-motion: reduce)').matches;
