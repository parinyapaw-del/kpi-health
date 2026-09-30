// Headline (big card, every level) + secondary cards from metadata `cards[]`.
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

/** "อันดับในประเทศ" on the home page, "อันดับในเขต 4" / "อันดับในสระบุรี" below it. */
function rankTitle(ctx) {
  const p = ctx.parentData;
  const plevel = p?.level ?? p?.scope?.level;
  return plevel === 'country' ? 'อันดับในประเทศ' : `อันดับใน${shortArea(p?.scope?.name)}`;
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
    rank ? `<div><dt>${esc(rankTitle(ctx))}</dt><dd>${rankHTML(rank, c.small)}</dd></div>` : '',
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
