// Formatting + colour-rule helpers. No indicator-specific knowledge lives here.

const nfCache = new Map();
function nf(min, max) {
  const k = `${min}-${max}`;
  if (!nfCache.has(k)) {
    nfCache.set(k, new Intl.NumberFormat('th-TH', { minimumFractionDigits: min, maximumFractionDigits: max }));
  }
  return nfCache.get(k);
}

export const isNum = (v) => typeof v === 'number' && Number.isFinite(v);

/** Integer with thousands separators ("4,748"); null → "–". */
export function fmtInt(v) {
  return isNum(v) ? nf(0, 0).format(v) : '–';
}

/** Plain number with fixed decimals; null → "–". */
export function fmtNum(v, d = 1) {
  return isNum(v) ? nf(d, d).format(v) : '–';
}

/** Percentage ("83.6%"); null → "–". */
export function fmtPct(v, d = 1) {
  return isNum(v) ? `${nf(d, d).format(v)}%` : '–';
}

/** "n / d" with thousands separators. */
export function fmtFrac(n, d) {
  return `${fmtInt(n)} / ${fmtInt(d)}`;
}

/** Compact "n/d" (bar labels, heatmap cells). */
export function fmtND(n, d) {
  return `${fmtInt(n)}/${fmtInt(d)}`;
}

const TH_MONTH_ABBR = ['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.'];

/**
 * asOf is a Buddhist-year ISO string: "2569-09-29T09:08" or "2569-09-29".
 * → "29 ก.ย. 2569 09:08 น." (time only when present).
 */
export function fmtAsOf(asOf) {
  if (!asOf || typeof asOf !== 'string') return '–';
  const m = asOf.match(/^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2}))?/);
  if (!m) return asOf;
  const [, y, mo, d, hh, mm] = m;
  const date = `${Number(d)} ${TH_MONTH_ABBR[Number(mo) - 1] ?? mo} ${y}`;
  return hh ? `${date} ${hh}:${mm} น.` : date;
}

export function esc(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/** Organisation logo plate (header + footer); '' when index.json has no `orgLogo`. */
export function orgLogoHTML(index) {
  return index.orgLogo ? `<span class="org-plate"><img src="${esc(index.orgLogo)}" alt="" width="800" height="220"></span>` : '';
}

/**
 * Colour rule (§4).
 * status: ok | warn | bad | neutral (no target) | na (no value)
 * small:  denominator below colorRules.smallN
 */
export function classify(value, den, target, rules) {
  const small = isNum(den) && den < (rules?.smallN ?? 20);
  if (!isNum(value)) return { status: 'na', small: false };
  if (!isNum(target)) return { status: 'neutral', small };
  const band = rules?.warnBand ?? 5;
  let status = 'bad';
  if (value >= target) status = 'ok';
  else if (value >= target - band) status = 'warn';
  return { status, small };
}

export const STATUS_ICON = { ok: '✓', warn: '!', bad: '✗', na: '–', neutral: '' };
export const STATUS_TEXT = {
  ok: 'ถึงเป้า',
  warn: 'ใกล้เป้า',
  bad: 'ต่ำกว่าเป้า',
  na: 'ไม่มีข้อมูล',
  neutral: 'เป้าหมาย: ยังไม่กำหนด',
};
