// Headline (big card on the region home page, one-line compact on province/district pages)
// + secondary cards from metadata `cards[]`.
import { vals, shortLabel } from '../data.js';
import { classify, esc, fmtPct, fmtFrac, fmtInt, isNum, STATUS_ICON, STATUS_TEXT } from '../format.js';

const NOTE_TIP = 'เป้าหมายอ้างอิง ยังไม่ยืนยัน';

export function targetText(target) {
  if (!target) return 'ยังไม่กำหนด';
  const star = target.note ? `<sup class="t-note" title="${esc(target.note || NOTE_TIP)}" tabindex="0">*</sup>` : '';
  return `≥ ${target.value}%${star}`;
}

/** "เขตสุขภาพที่ 4" → "เขต 4" (short form used in rank sentences). */
function shortArea(name) {
  return String(name ?? '').replace(/^เขตสุขภาพที่\s*/, 'เขต ');
}

/**
 * Rank of the scope among its parent's rows (excluding hasData:false, pseudo rows and den < smallN).
 * → {k, n, text}
 */
export function rankOf(ctx) {
  const { parentData, data, ind, groupKey, rules } = ctx;
  if (!parentData) return null;
  const h = ind.headline;
  const list = parentData.rows
    .filter((r) => r.hasData !== false && !r.pseudo)
    .map((r) => ({ code: String(r.code), v: vals(r, groupKey) }))
    .filter((x) => x.v && isNum(x.v[h.metric]) && isNum(x.v[h.den]) && x.v[h.den] >= rules.smallN)
    .sort((a, b) => b.v[h.metric] - a.v[h.metric]);
  const i = list.findIndex((x) => x.code === String(data.scope.code));
  const k = i >= 0 ? i + 1 : null;
  const plevel = parentData.level ?? parentData.scope?.level;
  const where = plevel === 'country' ? 'เขต' : `ใน${shortArea(parentData.scope.name)}`;
  return { k, n: list.length, where };
}

function rankHTML(rank, small) {
  if (!rank) return '';
  if (rank.k == null) return `ไม่จัดอันดับ${small ? ' (n&lt;20)' : ''}`;
  return `อันดับ <b>${rank.k}</b>/${rank.n} ${esc(rank.where)}`;
}

function subLine(ind, v) {
  const sub = ind.headline.sub;
  if (!sub) return '';
  return `${esc(sub.label)} ${fmtInt(v[sub.num])} คน (${fmtPct(v[sub.metric])})`;
}

/** Big headline card (region home page). */
export function headlineHTML(ctx) {
  const { ind, data, groupKey, target, rules, route, groupLabel } = ctx;
  const h = ind.headline;
  const v = vals(data.total, groupKey) ?? {};
  const value = v[h.metric];
  const c = classify(value, v[h.den], target?.value, rules);
  const rank = rankOf(ctx);
  const sub = subLine(ind, v);

  const meta = [
    `<div><dt>${esc(shortLabel(ind, h.num))} / ${esc(shortLabel(ind, h.den))}</dt><dd class="num">${fmtFrac(
      v[h.num],
      v[h.den],
    )}</dd></div>`,
    `<div><dt>เป้าหมายปี ${route.year}</dt><dd>${targetText(target)}</dd></div>`,
    rank ? `<div><dt>อันดับในประเทศ</dt><dd>${rankHTML(rank, c.small)}</dd></div>` : '',
  ].join('');

  return `<section class="headline s-${c.status}${c.small ? ' is-small' : ''}" aria-label="ตัวชี้วัดหลัก">
    <div class="hl-label">${esc(shortLabel(ind, h.metric))}${groupLabel ? ` · ${esc(groupLabel)}` : ''}</div>
    <div class="hl-main">
      ${STATUS_ICON[c.status] ? `<span class="hl-icon" aria-hidden="true">${STATUS_ICON[c.status]}</span>` : ''}
      <span class="hl-value">${fmtPct(value)}</span>
      ${c.small ? '<span class="badge-small">n&lt;20</span>' : ''}
    </div>
    <div class="hl-status">${STATUS_TEXT[c.status]}</div>
    ${sub ? `<div class="hl-sub">${sub}</div>` : ''}
    <dl class="hl-meta">${meta}</dl>
  </section>`;
}

/** One-line headline for province / district pages (the area name is the page's h1). */
export function compactHeadlineHTML(ctx, eyebrow) {
  const { ind, data, groupKey, target, rules, groupLabel } = ctx;
  const h = ind.headline;
  const v = vals(data.total, groupKey) ?? {};
  const value = v[h.metric];
  const c = classify(value, v[h.den], target?.value, rules);
  const rank = rankOf(ctx);
  const sub = subLine(ind, v);
  const icon = STATUS_ICON[c.status];
  const cards = (ind.cards ?? [])
    .map((cd) => `<span>${esc(cd.label)} <b class="num">${fmtPct(v[cd.metric])}</b></span>`)
    .join('');

  return `<section class="hl-compact s-${c.status}${c.small ? ' is-small' : ''}" aria-label="ตัวชี้วัดหลัก">
    <p class="eyebrow">${esc(eyebrow)}${groupLabel ? ` · ${esc(groupLabel)}` : ''}</p>
    <div class="hlc-row">
      <h1>${esc(data.scope.name)}</h1>
      <span class="hlc-value" title="${esc(STATUS_TEXT[c.status])}">${icon ? `<i aria-hidden="true">${icon}</i>` : ''}${fmtPct(value)}<span class="sr-only"> ${esc(STATUS_TEXT[c.status])}</span></span>
      ${c.small ? '<span class="badge-small">n&lt;20</span>' : ''}
      <span class="hlc-item num">${fmtFrac(v[h.num], v[h.den])}</span>
      <span class="hlc-item">เป้า ${targetText(target)}</span>
      ${rank ? `<span class="hlc-item">${rankHTML(rank, c.small)}</span>` : ''}
      ${sub ? `<span class="hlc-item">${sub}</span>` : ''}
    </div>
    ${cards ? `<p class="hlc-cards">${cards}</p>` : ''}
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
