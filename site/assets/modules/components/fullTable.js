// Item 9: collapsed full table (all `table[]` keys, every row incl. total) + CSV download.
import { vals, LEVEL_NAME, CHILD_LEVEL } from '../data.js';
import { esc, fmtInt, fmtNum, isNum } from '../format.js';

function fmtCell(v, type) {
  if (!isNum(v)) return '–';
  return type === 'pct' ? fmtNum(v, 2) : fmtInt(v);
}

export function fullTableHTML(ctx) {
  const { ind, data, groupKey, groupLabel, route } = ctx;
  const cols = ind.table ?? [];
  const rows = [...data.rows, { ...data.total, name: `รวม ${data.scope.name}`, _total: true }];
  const head = `<tr><th scope="col" class="ft-name">${esc(LEVEL_NAME[CHILD_LEVEL[route.level]])}</th>${cols
    .map((c) => `<th scope="col">${esc(c.label)}</th>`)
    .join('')}</tr>`;
  const body = rows
    .map((r) => {
      const v = vals(r, groupKey) ?? {};
      return `<tr${r._total ? ' class="ft-total"' : ''}><th scope="row" class="ft-name">${esc(r.name)}</th>${cols
        .map((c) => `<td>${r.hasData === false ? '–' : fmtCell(v[c.key], c.type)}</td>`)
        .join('')}</tr>`;
    })
    .join('');
  return `<details class="panel fulltable" id="panel-table">
    <summary><span class="ft-sum">ตารางข้อมูลเต็ม</span><span class="panel-sub">${
      groupLabel ? `${esc(groupLabel)} · ` : ''
    }${rows.length} แถว × ${cols.length} คอลัมน์ · กดเพื่อขยาย</span></summary>
    <div class="ft-bar">
      <button type="button" class="btn" id="csv-btn">ดาวน์โหลด CSV</button>
      <span class="panel-note">CSV รวม${ind.groups ? 'ทุกกลุ่มอายุ' : 'ทุกคอลัมน์'} · UTF-8 เปิดใน Excel ได้</span>
    </div>
    <div class="scroll-x ft-scroll" tabindex="0"><table class="ft">${`<thead>${head}</thead><tbody>${body}</tbody>`}</table></div>
  </details>`;
}

function csvCell(v) {
  const s = v == null ? '' : String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function downloadCSV(ctx) {
  const { ind, data, route } = ctx;
  const cols = ind.table ?? [];
  const groups = ind.groups ?? [{ key: null, label: '' }];
  const header = ['รหัสพื้นที่', 'พื้นที่', ...(ind.groups ? ['กลุ่มอายุ'] : []), ...cols.map((c) => c.label)];
  const lines = [header];
  const rows = [...data.rows, { ...data.total, name: `รวม ${data.scope.name}` }];
  for (const r of rows) {
    for (const g of groups) {
      const v = vals(r, g.key ?? 'total') ?? {};
      lines.push([
        r.code,
        r.name,
        ...(ind.groups ? [g.label] : []),
        ...cols.map((c) => (r.hasData === false || !isNum(v[c.key]) ? '' : v[c.key])),
      ]);
    }
  }
  const csv = '﻿' + lines.map((l) => l.map(csvCell).join(',')).join('\r\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${route.indicator}_${route.year}_${route.level}_${route.scope}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
