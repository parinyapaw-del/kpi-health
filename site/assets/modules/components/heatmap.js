// Heatmap of child rows × columns from META.heatmap.columns (always every group, independent of the
// age-group tab). Target columns use ok/warn/bad; `useTarget:false` columns use a single-hue ramp 0–100.
import { vals, canDrill, CHILD_LEVEL, LEVEL_NAME } from '../data.js';
import { classify, esc, fmtPct, fmtND, isNum, STATUS_ICON } from '../format.js';
import { toHash } from '../router.js';
import { state } from '../state.js';

function cell(row, col, ctx) {
  const v = vals(row, col.group ?? 'total') ?? {};
  const value = row.hasData === false ? null : v[col.metric];
  const c = classify(value, v[col.den], col.useTarget ? ctx.target?.value : null, ctx.rules);
  const small = c.small ? ` · n<${ctx.rules.smallN}` : '';
  const title = `${row.name} · ${col.label}: ${fmtPct(value)} (${fmtND(v[col.num], v[col.den])})${small}`;
  if (c.status === 'na') {
    return `<td class="hm s-na" title="${esc(title)}"><span class="hm-v">ไม่มีข้อมูล</span></td>`;
  }
  const ramp = !col.useTarget;
  const cls = ramp ? 's-ramp' : `s-${c.status}`;
  const style = ramp ? ` style="--p:${Math.max(0, Math.min(100, value)).toFixed(1)}%"` : '';
  const icon = ramp ? '' : STATUS_ICON[c.status];
  return `<td class="hm ${cls}${c.small ? ' is-small' : ''}"${style} title="${esc(title)}">
    <span class="hm-v">${icon ? `<i aria-hidden="true">${icon}</i>` : ''}${fmtPct(value)}</span>
    <span class="hm-nd">${fmtND(v[col.num], v[col.den])}${c.small ? ` <b class="badge-small">n&lt;${ctx.rules.smallN}</b>` : ''}</span>
  </td>`;
}

/** Row order: area code (default, Q6) or first-column % desc; no-data rows then pseudo rows last. */
function orderRows(rows, cols, sort) {
  const col = cols[0];
  const valOf = (r) => (r.hasData === false ? null : vals(r, col.group ?? 'total')?.[col.metric]);
  const real = rows.filter((r) => !r.pseudo);
  const pseudo = rows.filter((r) => r.pseudo);
  const byCode = (a, b) => String(a.code).localeCompare(String(b.code), 'en', { numeric: true });
  if (sort === 'pct') {
    real.sort((a, b) => {
      const va = valOf(a);
      const vb = valOf(b);
      if (!isNum(va) && !isNum(vb)) return byCode(a, b);
      if (!isNum(va)) return 1;
      if (!isNum(vb)) return -1;
      return vb - va || byCode(a, b);
    });
  } else {
    real.sort(byCode);
  }
  return [...real, ...pseudo];
}

/**
 * Data-quality label for subdistrict rows (district pages, Q34/Q37):
 * verified → "ตรวจกับ HDC แล้ว" · year without any HDC file → "ยังไม่มีไฟล์ HDC ให้ตรวจสำหรับปีนี้"
 * (+ inferred-units count) · else inferredUnits > 0 → "[INFERRED] หน่วย n แห่งใช้การอนุมานที่ตั้ง".
 */
function subdistrictLabel(ctx) {
  const { index, route, data } = ctx;
  if (route.level !== 'district') return null;
  const n = Number(data.inferredUnits ?? 0) || 0;
  const verifiedList = index.verified?.[route.indicator];
  if (!verifiedList) {
    // No HDC subdistrict report exists for this indicator at all.
    return { kind: 'inferred', text: '[INFERRED] ไม่มีรายงาน HDC ระดับตำบลให้ตรวจสอบ', n };
  }
  const yearList = verifiedList[String(route.year)];
  const verified = data.verified === true || (yearList ?? []).map(String).includes(String(route.scope));
  if (verified) {
    return { kind: 'verified', text: `ตรวจกับ HDC แล้ว${n > 0 ? ` · หน่วย ${n} แห่งใช้การอนุมานที่ตั้ง` : ''}`, n };
  }
  if (!yearList) {
    // This fiscal year has no HDC Excel yet (e.g. a new year) → nothing to verify against.
    return { kind: 'inferred', text: `ยังไม่มีไฟล์ HDC ให้ตรวจสำหรับปีนี้${n > 0 ? ` · [INFERRED] หน่วย ${n} แห่งใช้การอนุมานที่ตั้ง` : ''}`, n };
  }
  if (n > 0) return { kind: 'inferred', text: `[INFERRED] หน่วย ${n} แห่งใช้การอนุมานที่ตั้ง`, n };
  return { kind: null, text: '', n };
}

function sortToggle() {
  const b = (k, label) =>
    `<button type="button" class="sort-btn${state.heatSort === k ? ' is-on' : ''}" data-sort="${k}" aria-pressed="${state.heatSort === k}">${label}</button>`;
  return `<div class="sort-toggle" role="group" aria-label="เรียงแถว"><span>เรียง:</span>${b('code', 'รหัส')}${b('pct', '%')}</div>`;
}

export function heatmapHTML(ctx) {
  const { ind, data, route } = ctx;
  const cols = ind.heatmap.columns;
  const childLevel = CHILD_LEVEL[route.level];
  const label = subdistrictLabel(ctx);
  const head = `<tr><th scope="col" class="hm-name">${esc(LEVEL_NAME[childLevel])}</th>${cols
    .map((c) => `<th scope="col">${esc(c.label)}${c.useTarget ? '' : '<span class="hm-sub">ไม่มีเป้า</span>'}</th>`)
    .join('')}</tr>`;
  const body = orderRows(data.rows, cols, state.heatSort)
    .map((r) => {
      const drill = !r.pseudo && r.hasData !== false && canDrill(route.indicator, route.year, childLevel, r.code);
      const name = drill ? `<a href="${toHash({ ...route, level: childLevel, scope: r.code })}">${esc(r.name)}</a>` : esc(r.name);
      return `<tr${r.pseudo ? ' class="is-pseudo"' : ''}><th scope="row" class="hm-name">${name}</th>${cols
        .map((c) => cell(r, c, ctx))
        .join('')}</tr>`;
    })
    .join('');
  const totalName = `รวม ${data.scope.name}`;
  const total = `<tr class="hm-total"><th scope="row" class="hm-name">${esc(totalName)}</th>${cols
    .map((c) => cell({ ...data.total, name: totalName, hasData: data.total?.hasData !== false }, c, ctx))
    .join('')}</tr>`;
  const hasRamp = cols.some((c) => !c.useTarget);
  const noTarget = !ctx.target && cols.some((c) => c.useTarget); // year without a target: cells are neutral (no ok/warn/bad)
  const badge = label?.kind
    ? `<span class="dq-badge dq-${label.kind}" title="ตำบลของแต่ละหน่วยบริการยึดที่ตั้งตามทะเบียน MOPH GIS">${esc(label.text)}</span>`
    : '';
  return `<section class="panel" id="panel-heat">
    <header class="panel-hd panel-hd-row">
      <div>
        <h2>แผนที่ความร้อน ${esc(LEVEL_NAME[childLevel])} × ${ind.groups ? 'กลุ่มอายุ' : 'ตัวชี้วัด'} ${badge}</h2>
        <p class="panel-sub">ตัวเลขเล็ก = ตัวตั้ง/ตัวหาร${ind.groups ? ' · แสดงทุกกลุ่มอายุเสมอ' : ''}</p>
      </div>
      ${sortToggle()}
    </header>
    <p class="panel-note scroll-hint" aria-hidden="true">เลื่อนตารางซ้าย-ขวาเพื่อดูคอลัมน์อื่น ›</p>
    <div class="scroll-x heat-scroll" tabindex="0" aria-label="ตารางแผนที่ความร้อน เลื่อนซ้าย-ขวาได้"><table class="heat">${`<thead>${head}</thead><tbody>${body}${total}</tbody>`}</table></div>
    ${noTarget ? '<p class="panel-note">เป้าหมาย: ยังไม่กำหนด (ไม่แบ่งสี)</p>' : ''}
    ${
      hasRamp
        ? '<p class="panel-note ramp-key"><span class="ramp-sw" aria-hidden="true"></span>คอลัมน์ที่ไม่มีเป้า: สีอ่อน → เข้ม = 0 → 100%</p>'
        : ''
    }
  </section>`;
}
