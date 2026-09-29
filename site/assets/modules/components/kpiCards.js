// Item 1 (headline card) + item 2 (secondary cards from metadata `cards[]`).
import { vals, shortLabel } from '../data.js';
import { classify, esc, fmtPct, fmtFrac, fmtSigned, isNum, STATUS_ICON, STATUS_TEXT } from '../format.js';

const NOTE_TIP = 'เป้าหมายอ้างอิง ยังไม่ยืนยัน';

export function targetText(target) {
  if (!target) return 'ไม่มีเป้าหมาย';
  const star = target.note ? `<sup class="t-note" title="${esc(target.note || NOTE_TIP)}" tabindex="0">*</sup>` : '';
  return `≥ ${target.value}%${star}`;
}

/** Rank of the scope among its parent's rows (excluding hasData:false and small-n). */
export function rankOf(ctx) {
  const { parentData, data, ind, groupKey, rules } = ctx;
  if (!parentData) return null;
  const h = ind.headline;
  const list = parentData.rows
    .filter((r) => r.hasData)
    .map((r) => ({ code: String(r.code), v: vals(r, groupKey) }))
    .filter((x) => x.v && isNum(x.v[h.metric]) && isNum(x.v[h.den]) && x.v[h.den] >= rules.smallN)
    .sort((a, b) => b.v[h.metric] - a.v[h.metric]);
  const k = list.findIndex((x) => x.code === String(data.scope.code));
  return { k: k >= 0 ? k + 1 : null, n: list.length, parentName: parentData.scope.name };
}

export function headlineHTML(ctx) {
  const { ind, data, groupKey, target, rules, prevData, route, groupLabel } = ctx;
  const h = ind.headline;
  const v = vals(data.total, groupKey) ?? {};
  const value = v[h.metric];
  const c = classify(value, v[h.den], target?.value, rules);

  const rank = rankOf(ctx);
  let rankTxt = '';
  if (rank) {
    rankTxt =
      rank.k != null
        ? `<b>${rank.k}</b>/${rank.n} ใน${esc(rank.parentName)}`
        : `ไม่จัดอันดับ${c.small ? ' (n<20)' : ''}`;
  }

  let deltaTxt = '';
  if (prevData) {
    const pv = vals(prevData.total, groupKey)?.[h.metric];
    if (isNum(pv) && isNum(value)) {
      const d = value - pv;
      const dir = Math.abs(d) < 0.05 ? 'flat' : d > 0 ? 'up' : 'down';
      const arrow = dir === 'up' ? '▲' : dir === 'down' ? '▼' : '■';
      deltaTxt = `<span class="delta d-${dir}"><span aria-hidden="true">${arrow}</span> ${fmtSigned(d)} จุด</span>`;
    }
  }

  const meta = [
    `<div><dt>${esc(shortLabel(ind, h.num))} / ${esc(shortLabel(ind, h.den))}</dt><dd class="num">${fmtFrac(
      v[h.num],
      v[h.den],
    )}</dd></div>`,
    `<div><dt>เป้าหมายปี ${route.year}</dt><dd>${targetText(target)}</dd></div>`,
    rank ? `<div><dt>อันดับ</dt><dd>${rankTxt}</dd></div>` : '',
    deltaTxt ? `<div><dt>เทียบปี ${route.year - 1}</dt><dd>${deltaTxt}</dd></div>` : '',
  ].join('');

  return `<section class="headline s-${c.status}${c.small ? ' is-small' : ''}" aria-label="ตัวชี้วัดหลัก">
    <div class="hl-label">${esc(shortLabel(ind, h.metric))}${groupLabel ? ` · ${esc(groupLabel)}` : ''}</div>
    <div class="hl-main">
      ${c.status !== 'neutral' ? `<span class="hl-icon" aria-hidden="true">${STATUS_ICON[c.status]}</span>` : ''}
      <span class="hl-value">${fmtPct(value)}</span>
      ${c.small ? '<span class="badge-small">n&lt;20</span>' : ''}
    </div>
    <div class="hl-status">${STATUS_TEXT[c.status]}</div>
    <dl class="hl-meta">${meta}</dl>
  </section>`;
}

export function cardsHTML(ctx) {
  const { ind, data, groupKey } = ctx;
  const v = vals(data.total, groupKey) ?? {};
  const cards = (ind.cards ?? [])
    .map(
      (cd) => `<div class="card2">
      <div class="c2-label">${esc(cd.label)}</div>
      <div class="c2-value">${fmtPct(v[cd.metric])}</div>
      <div class="c2-frac num">${fmtFrac(v[cd.num], v[cd.den])}</div>
      <div class="c2-cap">${esc(shortLabel(ind, cd.num))} / ${esc(shortLabel(ind, cd.den))}</div>
    </div>`,
    )
    .join('');
  return `<section class="cards2" aria-label="ตัวชี้วัดรอง">${cards}</section>`;
}
