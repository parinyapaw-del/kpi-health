// Age-group tabs (only for indicators whose metadata has groups).
import { esc } from '../format.js';

export function groupTabsHTML(ind, groupKey) {
  if (!ind.groups) return '';
  const btns = ind.groups
    .map(
      (g) =>
        `<button type="button" role="tab" class="gtab${g.key === groupKey ? ' is-on' : ''}" data-group="${esc(
          g.key,
        )}" aria-selected="${g.key === groupKey}">${esc(g.label)}</button>`,
    )
    .join('');
  return `<div class="gtabs" role="tablist" aria-label="กลุ่มอายุ">${btns}</div>`;
}
