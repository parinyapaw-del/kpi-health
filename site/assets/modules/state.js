// In-memory UI state + theme persistence.
const THEME_KEY = 'kpi-health-theme';

export const state = {
  groupKey: 'total', // DSPM age-group tab (not in the hash)
  heatSort: 'code', // heatmap order: 'code' (area code, Q6 default) | 'pct'
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

export const isMobile = () => window.matchMedia('(max-width: 600px)').matches;

export const reduceMotion = () => isMobile() || window.matchMedia('(prefers-reduced-motion: reduce)').matches;
