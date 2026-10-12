# web_spec_phase3.md — ตัวชี้วัดที่ 3 "เชื่อม DSPM × เข้าถึงบริการ" (แผนอนาคต)

v0.1 · grilling 2026-10-12 (Save + Claude) · **สถานะ: รอ HDC — ยังไม่ execute** · ต่อจาก [`web_spec_phase2.md`](web_spec_phase2.md) (v2.0 + §12)

เหตุผลที่มีไฟล์นี้: HDC ประกาศแนวทางว่าจะสร้างตัวชี้วัดใหม่ที่นำ**ฐานข้อมูลสมวัย (DSPM)** มาเชื่อมกับ**ข้อมูลเข้าถึงบริการ**
เพื่อให้ได้ยอด "เด็กที่ได้รับการคัดกรอง **และ** เข้าสู่การรักษาจริง" (นับคน) — ปัจจุบันไม่มีใครนำ 2 ตารางนี้มารวมกัน
ไฟล์นี้ล็อกการตัดสินใจที่ตัดสินได้แล้วตอนนี้ เพื่อให้ session ที่ execute เริ่มจากการ**เติมช่องว่าง §3** ไม่ต้อง grill ใหม่ทั้งรอบ

---

## 0. วิธีใช้ไฟล์นี้

| เมื่อ | ทำ |
|---|---|
| ตอนนี้ | ไม่ต้องทำอะไร · รอบอัปเดตเป็นรายสัปดาห์แล้ว (§1) |
| Save รู้**ชื่อตาราง** บน MOPH Open Data API (`s_…`) | เริ่ม **ขั้น 0** (§8) — probe โครงข้อมูลแล้วเติม §3 |
| ตารางมีข้อมูลจริง ≥ 1 ปีงบ + HDC มี template Excel | **execute phase 3** — สั่ง "execute web_spec_phase3.md" (grill สั้น ๆ เฉพาะ §3 ที่ยังว่าง) |
| HDC ไม่ทำ / เปลี่ยนแนว | ไฟล์นี้คงไว้เป็นบันทึก · ไม่มีโค้ดค้างในระบบ (phase 3 ยังไม่แตะโค้ดเลย) |

---

## 1. สิ่งที่ทำแล้ววันนี้ (2026-10-12) — ไม่ใช่ phase 3 แต่เกี่ยว

- `.github/workflows/update.yml`: cron รายวัน → **รายสัปดาห์** จันทร์ 07:17 ICT รอบเดียว `--national` เสมอ (~100 นาที)
  + อังคาร 07:17 ICT = **รอบซ่อม** รันเฉพาะเมื่อรอบ schedule ล่าสุดที่จบแล้วไม่สำเร็จ (`gh run list --event schedule --status completed`)
  มิฉะนั้น job `update` ถูกข้าม (ไม่ยิง API) · รายละเอียดใน README §1 และ spec phase 2 §12
- เหตุผล (Save): ไม่สิ้นเปลือง — ที่ประหยัดจริงคือ **โควตา MOPH API ที่แชร์ทั้งประเทศ** (429 เมื่อ 2026-10-09/10) + commit/อีเมลรายวัน
  ไม่ใช่นาที GitHub Actions (repo public = ฟรี) · ยอมรับว่า "ข้อมูล ณ" เก่าได้ถึง 7 วัน
- ไม่แตะโค้ด pipeline/เว็บ

---

## 2. Decision log (grilling 2026-10-12)

| # | คำถาม | ตัดสิน | เหตุผล |
|---|---|---|---|
| Q1 | ตัวชี้วัดใหม่คืออะไร | **ยังไม่มีร่างจาก HDC** · แนวคิด = รวม DSPM กับเข้าถึงบริการ ให้ได้ยอดเด็กที่คัดกรองและเข้าสู่การรักษาจริง (นับคน) | ยังไม่รู้สูตร/ตาราง/ระดับ → แผนนี้เป็น placeholder ที่ล็อกเฉพาะโครง |
| Q2 | แหล่งข้อมูล | **(a) รอ MOPH Open Data API** อย่างเดียว · ไม่ทำทาง Excel-เป็นแหล่งหลัก | เว็บนี้ดึงทุกระดับจาก API; Excel เป็น oracle เท่านั้น · รอดูก่อนว่า API จะมีข้อมูลแค่ไหน |
| Q3 | แบบ 1 (มีแค่อันใหม่) vs แบบ 2 (3 อัน) | **เขียนทั้ง 2 แบบเป็นทางแยกเลือกด้วย config** · ค่าตั้งต้น = แบบ 2 · รองรับ "แสดงรายปี" เพื่อให้แบบ 1 เปิดได้โดยปี 2569 (verify 100% แล้ว) ยังอยู่ | ไม่ทิ้งข้อมูลที่ตรวจแล้ว · ตัดสินแบบไหนเมื่อ HDC ประกาศ KPI ปี 2570 จริง |
| Q4 | รอบอัปเดต | จันทร์ national รอบเดียว + อังคารซ่อม | §1 |
| Q5 | ไฟล์แผน / push | `web_spec_phase3.md` ที่ root · commit แยก `pipeline: weekly` และ `docs: phase 3 plan` แล้ว push | cron ที่ไม่ push = ยังรายวัน |
| Q6 | ความละเอียดแผน | ระดับ spec แบบ phase 2 + checklist ไฟล์ที่ต้องแตะ + "สิ่งที่ยังไม่รู้" | session อนาคตเติมช่องว่าง ไม่ grill ใหม่ |
| Q7 | ทำ "ตัวเชื่อม" ชั่วคราวจาก 2 ตารางเดิมเองไหม | **(a) ไม่ทำ** | Save: ไม่รู้ว่ามีข้อมูล**ซ้ำ**ระหว่าง 2 ตาราง (เด็กคนเดียวกันนับใน DSPM 3.2 และ Coverage (4)/(5)/(6)) ที่ต้องเอาออกหรือไม่ — ยอดรวมคนละฐานจะถูกอ่านเป็น "เด็กจริง" แล้วขัดกับของ HDC ทีหลัง · ดู §9 |
| Q8 | รู้ได้อย่างไรว่าตารางมาบน API | **(a) Save บอกชื่อตารางเอง** · ไม่ทำ `watchTables`/probe อัตโนมัติ | API ไม่มี catalog ให้ probe ชื่อที่ไม่รู้ |
| Q9 | แบบ 1: ตัวเก่ายังดึงต่อไหม | **ดึงต่อแบบเงียบ** (8 จังหวัด + Coverage ของปีที่ไม่แสดง ~8 นาที/สัปดาห์; 77 จังหวัดเฉพาะปีที่แสดง) | สลับแบบ 1↔2 ได้ด้วย config อย่างเดียว ไม่มีช่องว่างข้อมูล |
| Q10 | รอบสัปดาห์ล้ม | **(b) cron อังคารซ่อมอัตโนมัติ** | ไม่เพิ่มการยิง API เมื่อปกติ · ลดโอกาสเว็บค้าง 2 สัปดาห์ |

ตัดสินเองโดย Claude (Save ไม่ทัก): id ชั่วคราว `linked` ป้ายสั้น "คัดกรอง→รักษา" · เปลี่ยนปีแล้วแท็บนั้นไม่มีในปีนั้น → ไปแท็บแรกของปีนั้น ·
ตัวใหม่ไม่มีเป้า = สีกลาง "ยังไม่กำหนด" (พฤติกรรมเดิม) · spec phase 2 ไม่แก้เนื้อ เพิ่มเฉพาะบรรทัด §12

---

## 3. สิ่งที่ยังไม่รู้ — ต้องเติมก่อน execute (ขั้น 0, §8)

เติมในตารางนี้เมื่อรู้ (ถ้าไม่ครบ ห้ามเริ่มเขียนโค้ด):

| # | ต้องรู้ | ค่า | วิธีหา |
|---|---|---|---|
| U1 | ชื่อตาราง API (`s_…`) + body ที่ต้องส่ง (`year`, `province`? — Coverage ส่ง `province` แล้ว 400) | | Save จาก HDC / ประกาศ · `moph_api.probe(table, year)` |
| U2 | ชื่อทางการของตัวชี้วัด (`name_th`) + ป้ายสั้น + มีเป้าหมายร้อยละไหม (ค่า) | | template HDC |
| U3 | **คอลัมน์** (template Excel (1)…(n)) + field ดิบใน API ที่ตรงกัน + **สูตรร้อยละทุกตัว** (เศษ/ส่วน) → ตาราง `PCT` เดียวแบบ `indicators/dspm.py` | | export Excel HDC 1 ชุด + raw API 1 จังหวัด แล้วเทียบ |
| U4 | **หน่วยของ 1 แถว API**: hospcode × areacode(8) × เดือน (แบบ DSPM) หรือ 1 แถว/อำเภอ (แบบ Coverage `areacode=<อำเภอ>0101`, hospcode ไม่จริง) | | นับแถว/ดู areacode ของจังหวัด 15 |
| U5 | **ระดับลึกสุดบนเว็บ**: ถ้า U4 = แบบ DSPM → ตำบลได้ และต้องใช้**กฎที่ตั้งหน่วยบริการ** (phase 2 §4.3 `units.json` + `overrides`) · ถ้าแบบ Coverage → อำเภอ | | ตามหลัง U4 |
| U6 | มี **กลุ่มอายุ** (9/18/30/42/60) ไหม → `groups` + แท็บกลุ่มอายุ หรือ flat | | template |
| U7 | ปีงบแรกที่มีข้อมูล · ข้อมูลย้อนหลัง (2569?) มีไหม | | probe ทุกปีใน `years` ∪ {max+1} |
| U8 | HDC **นับซ้ำ**อย่างไร (เด็ก 1 คนหลายหน่วย/หลายรหัส) — เพื่อรู้ว่ายอด "รวม" ของเราต้อง sum ตรง ๆ หรือมีคอลัมน์ "ไม่นับซ้ำ" แบบ Coverage (7) | | คำอธิบาย template HDC |
| U9 | ความสัมพันธ์กับ 2 ตัวเดิม: HDC ประกาศว่า**แทน**ตัวไหน หรือเป็นตัวที่ 3 ของปี 2570 | | ประกาศ KPI ปีงบ / สสจ. |
| U10 | ใส่ในกราฟ 13 เขต / ยอดเขต 4 ไหม (ต้องดึง 77 จังหวัดเหมือน DSPM หรือ API ให้ทั้งประเทศในครั้งเดียวเหมือน Coverage) | | ตามหลัง U4 |

U9 ตัดสิน **แบบ 1 vs แบบ 2** (§4) · U4/U5 ตัดสินว่า plugin ลอกจาก `dspm.py` หรือ `coverage.py` (§5)

---

## 4. ทางแยก 2 แบบ — เลือกด้วย config อย่างเดียว

### 4.1 Config `sites/angthong.json` (schema 3)

```jsonc
{
  "schema": 3,
  "indicators": ["dspm", "coverage", "linked"],   // = ชุดที่ pipeline "ดึง/build/verify" (เหมือนเดิม)
  "display": {                                      // ใหม่ (ไม่บังคับ) = ชุดที่ "แสดง" รายปี · ไม่มี key = แสดงทุกตัวใน indicators ทุกปี
    "2569": ["dspm", "coverage"],
    "2570": ["linked"]                              // แบบ 1 · แบบ 2 = ["dspm", "coverage", "linked"] หรือไม่ใส่ display เลย
  },
  "targets": { "linked": { "2570": { "value": null } } }   // null/ไม่มี = "ยังไม่กำหนด" สีกลาง
}
```

- **แบบ 2 (ค่าตั้งต้น)**: เพิ่ม `"linked"` ใน `indicators` ไม่ใส่ `display` → 3 แท็บทุกปีที่มี dataset
- **แบบ 1**: ใส่ `display` ตามปี · ปี 2569 ยังเห็น 2 แท็บเดิม · ปี 2570 เห็นแท็บเดียว
- Q9: `indicators` ยังมี `dspm`/`coverage` อยู่เสมอ → ดึงต่อเงียบ ๆ (refresh policy เดิม: `currentYear` + ปีก่อน) ·
  **ข้อยกเว้นเพื่อประหยัด**: `--national` (77 จังหวัด ~85 นาที) ทำเฉพาะตัวชี้วัดที่อยู่ใน `display[currentYear]` (หรือทุกตัวเมื่อไม่มี `display`)
- สลับแบบ = แก้ `display` แล้ว push (หรือผ่าน `/admin/` ถ้าเพิ่มช่อง — §6.3) · ไม่ต้องดึงข้อมูลใหม่

### 4.2 ผลต่อ `site/data/angthong/index.json`
- `indicators` (META) ยังมีทุกตัวที่ build · เพิ่ม `display: {year: [ids]}` ส่งต่อให้เว็บตรง ๆ · `datasets` มีทุกตัวที่ build (เว็บกรองเองตาม `display`)
- ไฟล์ dataset ของตัวที่ไม่แสดงยังถูก publish (ขนาดเล็ก, ทำให้สลับแบบได้ทันทีโดยไม่ build ใหม่)

---

## 5. Pipeline (ตาม phase 2 §4 · ลอกโครงจาก plugin ที่ U4 ชี้)

### 5.1 plugin ใหม่ `scripts/indicators/linked.py`
- `ID = "linked"` (เปลี่ยนเป็นรหัสทางการเมื่อรู้ U2 — ใช้ id เดียวตลอด เพราะ id อยู่ใน URL hash, ชื่อไฟล์ dataset, `targets`, KV override)
- `TABLE`, `RAW` (key → field ดิบ), `COUNT_KEYS`, **`PCT` ตารางเดียว** (เศษ, ส่วน) ← U3, `TABLE_KEYS` ลำดับ+ป้ายไทยตาม header Excel HDC
- `META`: `name_th`, `short`, `source.table`, `groups` (U6), `headline` (metric หลัก + `sub` ถ้ามี), `cards` (≤ 3), `heatmap.columns` (คอลัมน์แรก `useTarget: true`), `chart` (`style: "fill"` แบบ Coverage ถ้า "เข้าถึง/ทำได้ ต่อ ฐาน" · `"bar"` แบบ DSPM ถ้าเทียบร้อยละข้ามพื้นที่), `table`, `targets_key: "linked"`
- ฟังก์ชันที่ plugin ต้องมีให้ `build_site`/`verify` เรียก (ดู `PLUGINS` ใน `build_site.py` และสิ่งที่ `dspm.py`/`coverage.py` export): `fetch`, `load_cache`, aggregate ต่อระดับ, `derive_pcts`/`check_pcts`/`compare_values` ผ่าน `common.py`
- ถ้า U4 = แบบ DSPM: ใช้ `fallback_tambon` + `units.json` + `overrides` เดียวกัน (ห้ามสร้างทะเบียนหน่วยชุดที่ 2) และ `do_units` ใน `kpi.py` ต้องรวม hospcode จาก cache ของ `linked` ด้วย (ตอนนี้อ่านเฉพาะ `dspm.load_cache`)

### 5.2 ไฟล์ที่ต้องแตะ (ทุกจุดที่ enumerate ตัวชี้วัดแบบ hard-coded — ตรวจแล้ว 2026-10-12)

| ไฟล์ | จุด | ทำ |
|---|---|---|
| `scripts/build_site.py` | `PLUGINS = {"dspm": dspm, "coverage": coverage}` (บรรทัด ~21) · `write index` (~373–385) | เพิ่ม `linked` · เขียน `display` ลง index.json (schema 3) |
| `scripts/kpi.py` | `from scripts.indicators import coverage, dspm` (41) · `fetch_new_year` เช็ก `"dspm"`/`"coverage"` ตรง ๆ (161–190) · `inherit_targets` วน `site["indicators"]` (195) · `do_units` ใช้ dspm cache เท่านั้น (226) · `refresh_scope` (86) | เพิ่ม `linked` ใน fetch/new-year · `--national` จำกัดตาม `display[currentYear]` (§4.1) · probe ปีใหม่: ยังนับ "พบปีใหม่" จาก DSPM เท่านั้น (ไม่เปลี่ยน) |
| `scripts/verify.py` | `_check_written` มี special-case `j["indicator"] == "dspm"` (239) · `_api_vs_excel`/`_cross_level` ผ่าน `PLUGINS` | ทำให้ `_check_written` ดูจาก `META.groups` แทนชื่อ indicator |
| `scripts/loaders/xlsx_hdc.py` | `read_workbook` แยก layout ด้วย `indicator == "dspm"` (138–180) · header row 5 vs 3 | เพิ่ม layout ที่ 3 ตาม template HDC (U3) — ถ้าเหมือน Coverage ให้ reuse |
| `data/excel_reference/linked/<ปี>/<YYYY-MM-DD>/*.xlsx` | ใหม่ | oracle อย่างน้อย อ่างทอง 1 ปี ทุกอำเภอ (+ ตำบลถ้า U5 = ตำบล) |
| `docs/API_NOTES.md` | ใหม่ §5 | field mapping + ผล API vs Excel (ต้องตรง 100% ระดับอำเภอ/ตำบลเหมือน DSPM; ประเทศ/เขตต่างได้ = warning) |
| `sites/angthong.json` | `schema: 3`, `indicators`, `display`, `targets.linked` | §4.1 |
| `.github/workflows/update.yml` | commit step `git add` ครอบ `site/data` อยู่แล้ว · Issue "พบข้อมูลปีงบ" แสดงเป้าทุก indicator จาก config | แทบไม่ต้องแก้ · timeout 150 ยังพอถ้า U10 ไม่ต้องดึง 77 จังหวัดเพิ่ม (ถ้าต้อง: +45–85 นาที → แยกรอบ หรือ national สลับสัปดาห์) |

### 5.3 Verify
- hard: สูตร `PCT` ทุกตัว, ผลรวมข้ามระดับ (ตำบล→อำเภอ→จังหวัด), ชุดแถว/ชื่อพื้นที่ตรง Excel, ตัวเลขตรง Excel 100% ระดับอำเภอ/ตำบล (ไฟล์ในโฟลเดอร์วันที่ ≥ asOf ของ API)
- warning ที่คาดได้: ระดับประเทศ/เขตต่าง HDC (เหมือน DSPM) · ปีที่ไม่มี oracle
- **ห้าม** เขียน verify ข้าม indicator (เช่น `linked.screened == dspm.screened`) จนกว่า U8 จะยืนยันว่า HDC นิยามเท่ากัน — ใส่เป็น warning เท่านั้นถ้าอยากดู

---

## 6. เว็บ (phase 2 §5 — โหลด `dataviz` + `artifact-design` ก่อนแตะกราฟ)

### 6.1 Header / router (`site/assets/modules/components/header.js`, `router.js`, `data.js`)
- แท็บตัวชี้วัด = `index.display?.[year] ?? Object.keys(index.indicators)` (ลำดับตาม `indicators` ใน config; `router.js` ปัจจุบัน sort ให้ `dspm` มาก่อน → เปลี่ยนเป็นตามลำดับ config)
- `findDataset`/`canDrill`: ไม่เปลี่ยน (dataset ของตัวที่ไม่แสดงยังมี แต่ไม่มีแท็บให้ไป) · route ตรง ๆ `#/dspm/2570/...` ในแบบ 1 → ถ้า `dspm ∉ display[2570]` ถือว่า route ไม่มี → ไปแท็บแรกของปีนั้น (ไม่ 404)
- สลับปี (year switch): เก็บ indicator เดิมถ้าปีใหม่มี มิฉะนั้นแท็บแรกของปีนั้น · route เริ่มต้น = indicator แรกของ `display[currentYear]` ที่มี dataset ระดับ home
- ชื่อเต็ม + "ข้อมูล ณ" ใต้ header ใช้ META ของตัวที่เลือก (เหมือนเดิม)

### 6.2 เนื้อหาต่อชั้น
- ทุก component อ่านจาก META อยู่แล้ว (`headline`, `cards`, `heatmap.columns`, `chart`, `table`, `groups`) → ถ้า META ครบ ไม่ต้องแก้ `kpiCards`/`heatmap`/`childBars`/`fullTable`/`groupTabs`
- จุดที่อาจต้องแก้: `charts.js` ถ้า U3 ต้องการกราฟแบบที่ 3 (ไม่ใช่ bar/fill) — หลีกเลี่ยง ให้เลือกจาก 2 แบบเดิม
- heatmap ป้าย "ตรวจกับ HDC แล้ว" ใช้ `index.verified[linked]` อัตโนมัติ

### 6.3 Admin (`site/admin/admin.js`, `functions/api/admin/config.js`)
- ช่องเป้าหมายวนตาม `index.indicators` × ปีที่มีข้อมูล → `linked` โผล่เอง · `cleanTargets` รับ id ใหม่อยู่แล้ว (ตรวจ object)
- เพิ่ม (ไม่บังคับ): ช่อง "ตัวชี้วัดที่แสดง รายปี" (checkbox ต่อปี) → KV override key `display` · ถ้าไม่ทำ สลับแบบ 1/2 ด้วยการแก้ repo แล้ว push ก็พอ
- `functions/api/admin/spec.js` รวม `web_spec_phase2.md` เท่านั้น → เพิ่ม `web_spec_phase3.md` ต่อท้ายตอน execute

---

## 7. ปีใหม่อัตโนมัติ (autoYear) กับตัวที่ 3
- probe "พบปีใหม่" ยังยึด DSPM มีแถว (phase 2 §12) — ไม่เปลี่ยน · `linked` ของปีใหม่ดึงในรอบ national เดียวกัน 0 แถว = warning (แบบ Coverage)
- เป้าหมาย: `inherit_targets` คัดลอกจากปีก่อนถ้ามี · ปีแรกของ `linked` ไม่มีเป้าให้คัดลอก → "ยังไม่กำหนด" → Issue "พบข้อมูลปีงบ Y" จะบอกว่า `linked` ยังไม่กำหนด

---

## 8. แผน execute

**ขั้น 0 — เมื่อรู้ชื่อตาราง (ทำได้ทันที ไม่แตะโค้ดเว็บ · 1 session สั้น, Sonnet พอ)**
1. `python3 -c "from scripts.loaders import moph_api; print(moph_api.probe('<table>', 2570))"` ทุกปีใน `years` ∪ {max+1} → U1/U7
2. ดึง raw 1 จังหวัด (15 อ่างทอง) เก็บใน `data/raw_api/<table>/` (gitignore) → ดู field/หน่วยแถว → U3/U4/U6/U10
3. Save export Excel HDC template ของอ่างทองปีนั้น → `data/excel_reference/linked/<ปี>/<วันที่>/` → เทียบมือ 1 อำเภอ → U3/U8
4. เติม §3 ลงไฟล์นี้ + `docs/API_NOTES.md` §5 · ถ้า API ไม่ตรง Excel ระดับอำเภอ → **หยุด** รายงาน Save (เหมือนกฎ phase 2 §3)

**ขั้น 1 — pipeline (Sonnet, 1 session)**: §5 ทั้งหมด → `kpi.py update --site angthong --indicator linked` ผ่าน verify (exit 0) → ไฟล์ dataset ขึ้น `site/data/angthong/linked_*` · `sites/angthong.json` schema 3 แต่ **ยังไม่ใส่ `linked` ใน `indicators`** จนกว่าขั้น 2 เสร็จ (เว็บ prod ไม่เปลี่ยน)

**ขั้น 2 — เว็บ (Opus, 1 session)**: §6.1–6.2 → ทดสอบ 3 กรณีใน preview: ไม่มี `display` (แบบ 2) · `display` แบบ 1 · route ตรงไปตัวที่ไม่แสดง → ค่อยเปิด `indicators` + `display` ตาม U9 → push

**ขั้น 3 — admin + docs (Sonnet)**: §6.3 · README §0/§1/§2 · spec download · memory

เงื่อนไขหยุดก่อนขั้น 1: U1–U5, U8, U9 ว่าง → ไม่เริ่ม

---

## 9. ทำไมไม่ทำ "ตัวเชื่อม" เองจาก 2 ตารางเดิม (Q7) + mapping เผื่อ HDC ใช้

ตารางที่มีอยู่ให้ยอด**คนละฐาน**: DSPM นับผลคัดกรองของเด็กในหน่วย (เป้าหมาย (1) → คัดกรอง (2) → สงสัยล่าช้า (2.4) → ติดตามได้ (3) → ไม่สมวัยหลังกระตุ้น (3.2));
Coverage ใช้ตัวส่วนจาก**ความชุก** (3)=(1)×(2)/100 ไม่ใช่เด็กที่คัดกรองจริง และตัวเศษ (4)(5)(6) นับจากรหัสบริการ/วินิจฉัยซึ่งเด็ก 1 คนอาจมีหลายรหัสหลายหน่วย ("(7) ไม่นับซ้ำ" ทำที่ HDC จากรายคน)
→ จากยอดรวมเราไม่รู้ว่าเด็กใน 3.2 กับเด็กใน (4)–(6) ซ้ำกันกี่คน ยอด "เข้าสู่การรักษาจริง" จึงคำนวณจากยอดรวมไม่ได้ (Save 2026-10-12) และเลขประมาณการจะถูกอ่านเป็น "เด็กจริง" แล้วขัดกับของ HDC ทีหลัง

mapping ที่**คาดว่า** HDC จะใช้ (ไว้เทียบตอน U3 — ไม่ใช่สูตรของเรา):

| ขั้นใน funnel | field ที่เรามี | ตาราง |
|---|---|---|
| เด็กเป้าหมาย / คัดกรอง | `target`, `screened` | DSPM (1)(2) |
| สงสัยล่าช้า | `suspect_wait30 + suspect_refer = suspect_total` | DSPM (2.2)(2.3)(2.4) |
| ยืนยันล่าช้าหลังกระตุ้น | `delay_after_total` (+ รายด้าน 1B202…1B242) | DSPM (3.2) |
| เข้าสู่บริการ/รักษา | `served_teda4i`, `served_icd9`, `diagnosed_icd10`, `reached_cum` (ไม่นับซ้ำ) | Coverage (4)(5)(6)(7) |
| ร้อยละที่ HDC น่าจะนิยาม | (เข้าสู่บริการ รายคน) / (ยืนยันล่าช้า รายคน) — ทั้งคู่ต้อง join รายคนที่ HDC | — |

ถ้าตารางใหม่ให้คอลัมน์ตรงกับแถวข้างบน การ verify ข้าม indicator (§5.3) ทำได้เป็น warning

---

## 10. สมมติฐานที่ยังไม่ยืนยัน
- HDC จะปล่อยตัวชี้วัดใหม่บน MOPH Open Data API (ไม่ใช่เฉพาะใน HDC) — ถ้าไม่ phase 3 ไม่เริ่ม (Q2)
- โครงแถว API จะเป็นหนึ่งใน 2 แบบที่มีอยู่ (DSPM หรือ Coverage) — ถ้าเป็นแบบที่ 3 ต้อง grill §5 ใหม่
- timeout 150 นาทีพอ ถ้าตัวใหม่ไม่ต้องดึง 77 จังหวัดเพิ่ม (U10)
- id `linked` ใช้ชั่วคราวเฉพาะในไฟล์นี้ — ตอน execute ตั้ง id จริงครั้งเดียวแล้วไม่เปลี่ยน
