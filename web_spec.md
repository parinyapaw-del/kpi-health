# web_spec.md — ระบบติดตามตัวชี้วัด (kpi-health)

| | |
|---|---|
| Version | **1.1** (Phase 0 ล็อกหลัง grilling 40 ข้อ · แก้จาก 1.0 เพราะพบ MOPH Open Data API ใช้แทน Excel ได้) |
| วันที่ | 2026-09-29 |
| ผู้สั่ง | Save (Parinya Pawenawan) — สำหรับ รพ.อ่างทอง (พี่ต้อง) |
| สถานะ | **approved → Phase 1 execute ใน session ใหม่** ที่เปิดใน `~/Desktop/Claude/web project/kpi-health/` ด้วยคำสั่ง "execute web_spec.md" |
| Model | Orchestrator = Fable (หรือ Opus) อ่าน spec นี้ทั้งไฟล์ก่อน · Sonnet = pipeline ข้อมูล + โลโก้ · Opus = หน้าเว็บ · Orchestrator ตรวจทุกขั้น |

> spec นี้เขียนให้ session ใหม่ทำงานได้โดยไม่ต้องรู้บทสนทนา Phase 0 · ทุกข้อเท็จจริงตรวจแล้ว 2026-09-29 · ห้ามเดาตัวเลข (CLAUDE.md rule 4) · ถ้าอะไรใน spec ขัดกับของจริงในเครื่อง ให้หยุดรายงาน ไม่ต้องแก้เอง

## 1. วัตถุประสงค์และผู้ใช้

- Dashboard/infographic ตัวชี้วัดสาธารณสุขที่ **ผู้ตรวจราชการ** เปิด link แล้วดูได้ทันที ไม่ต้อง login · ไม่มีข้อมูล sensitive (ระดับพื้นที่)
- เจาะจากภาพใหญ่ (ประเทศ) → เขต 4 → จังหวัดอ่างทอง → อำเภอเมืองอ่างทอง (**ตำบล**) = พื้นที่ รพ.อ่างทอง
- ทุกเปอร์เซ็นต์มี **ตัวตั้ง / ตัวหาร** กำกับ
- ตอบคำถาม "ต้องพัฒนาที่**กลุ่มอายุไหน / พื้นที่ไหน**" ด้วย heatmap + กล่องสรุปจุดอ่อน
- **สั่งคำสั่งเดียวแล้วดึงข้อมูลจาก API ขึ้นเว็บได้เอง** (ปีใหม่ / ตัวชี้วัดใหม่) — Excel เก็บเป็นชุดทดสอบ
- Roadmap: Phase 1 = ข้อมูลที่มี (2 ตัวชี้วัด × 2567–2569 อ่างทอง) · Phase 2+ = **เพิ่มตัวชี้วัด** (Save จะให้วิธีดึงเอง) · ไม่ทำจังหวัดอื่น

## 2. Decision log (สรุปจาก grilling Q1–Q40)

| # | เรื่อง | ตัดสินใจ |
|---|---|---|
| Q1 | Hosting | **Cloudflare Pages** (static) เชื่อม GitHub repo · ไม่ใช้ GAS |
| Q2 | URL | `kpi-health.pages.dev` (สำรอง `kpi-health-th`) · Save มี Cloudflare account · ยังไม่ซื้อ domain |
| Q3 | Repo | `~/Desktop/Claude/web project/kpi-health/` · GitHub `parinyapaw-del/kpi-health` **public** · ย้ายทุกอย่างจากโฟลเดอร์เก่า "พัฒนาการเด็ก พี่ต้อง" (ยุบทิ้ง) |
| Q4 | ระดับลึกสุด | 4 ชั้น: ประเทศ → เขต 4 → อ่างทอง → เมืองอ่างทอง (ตำบล) |
| Q5/Q27 | Headline + เป้า | DSPM = ร้อยละสมวัย (ตัวหาร = เป้าหมาย) เป้า 85\*/87/88 · Coverage = คอลัมน์ (10) ปีงบ เป้า 30 (2569) · ตัวชี้วัดย่อยไม่มีเส้นเป้า |
| Q6 | เศษส่วน | ทุก % มี n/d · ตารางเต็มซ่อน กดขยาย |
| Q7/Q29 | อัปเดตข้อมูล | Save รัน `python3 scripts/kpi.py update` เอง แล้ว `git push` |
| Q8 | มุมมอง | bar เทียบพื้นที่ลูก + line แนวโน้ม 3 ปี · กลุ่มอายุเป็นแท็บย่อย |
| Q9/Q38 | ณ วันที่ | แสดง**ต่อตัวชี้วัด-ปี** จาก `date_com` ของ API · ส่วนที่มาจาก Excel ใช้วัน export 29 ก.ย. 2569 ป้าย "HDC export" |
| Q10 | เขต 13 ปี 2569 = 0 | "ไม่มีข้อมูล" ไม่นับในกราฟ/อันดับ |
| Q11 | ชื่อ/โลโก้ | "ระบบติดตามตัวชี้วัด จังหวัดอ่างทอง" · โรงพยาบาลอ่างทอง · `logo.webp` ลบพื้นขาว |
| Q12 | อุปกรณ์ | จอใหญ่/โปรเจกเตอร์เป็นหลัก · มือถือ 375px ต้องไม่พัง |
| Q13 | Model | Sonnet: pipeline + โลโก้ · Opus: เว็บ · Orchestrator ตรวจ |
| Q14/Q34 | โครงสร้าง site | แยก site (`sites/angthong.json`) · **site เดียว** ไม่ทำจังหวัดอื่น |
| Q15 | URL site | `/angthong/` · root redirect ไป `/angthong/` |
| Q16 | หาจุดพัฒนา | heatmap (พื้นที่ × กลุ่มอายุ) + กล่อง "จุดควรพัฒนา" 3 อันดับต่ำสุด |
| Q17 | สี | ok ≥ เป้า · warn [เป้า−5, เป้า) · bad < เป้า−5 · na · ตัวหาร < 20 = "n น้อย" |
| Q19 | เชื่อม Cloudflare | Save ทำในหน้า dashboard เองตาม README |
| Q20 | สิทธิ์ | สร้าง repo public ได้ · **ขอยืนยันอีกครั้งก่อน `gh repo create`** |
| Q21 | Tech | vanilla HTML/CSS/JS + Chart.js (CDN) ไม่มี build step · แยก data layer เผื่อย้าย Vite+React |
| Q22 | ปี | เปิดที่ 2569 · สลับ 2567/2568/2569 · แนวโน้ม 3 ปีเสมอ |
| Q23 | อันดับ | เล็กใต้ headline เช่น "อันดับ 2/8 ในเขต 4" |
| Q24 | แยกเพศ | ตารางเต็มเท่านั้น |
| Q25 | Theme | light default + ปุ่ม dark |
| Q28 | แหล่งข้อมูลหลัก | **API** เป็นหลัก · Excel 22 ไฟล์ = oracle สำหรับ `verify` (ต้องตรง 100%) |
| Q30 | commit อะไร | cache ที่ aggregate แล้ว (`data/cache/`) + JSON เว็บ · raw response ไม่ commit |
| Q31/Q39 | key พื้นที่ | **areacode** (DOPA) · ชื่อจาก lookup `data/lookup/areas.json` ตรวจกับชื่อใน Excel อ่างทอง |
| Q32 | Plugin ตัวชี้วัด | 1 ตัวชี้วัด = 1 ไฟล์ `scripts/indicators/<id>.py` ประกาศ metadata · เว็บวาดจาก metadata |
| Q33 | ดึงอัตโนมัติ | Phase 1 รันเอง · GitHub Actions รายเดือน = option Phase 2 |
| Q35 | Excel | `data/excel_reference/angthong/...` |
| Q36 | DSPM ประเทศ/เขต 4 | **Excel** (API ทั้งประเทศ 612,509 แถว/ปี ช้าและหลุด 404) · API เฉพาะอ่างทอง→อำเภอ→ตำบล · เขต 4 ต้องแสดง 8 จังหวัด (มีใน Excel เขต 4) |
| Q37 | Coverage | **API ทุกระดับ** (0.2 วิ) + verify Excel · ต้องมีตาราง จังหวัด→เขตสุขภาพ |
| Q40 | รายเดือน | **ทำกราฟความคืบหน้ารายเดือน** (DSPM อ่างทอง/อำเภอ/ตำบล) ใน Phase 1 · cache ละเอียดถึง ตำบล × เดือน |

## 3. แหล่งข้อมูล

### 3.1 MOPH Open Data API (หลัก) — รายละเอียดเต็มใน `docs/API_NOTES.md`

- `POST https://opendata.moph.go.th/api/report_data` · `Content-Type: application/json` · ไม่ต้อง auth
- Response `{"data":[...], "total":"N", "limit":1000, "offset":0}` · **default limit 1000** → ส่ง `"limit"` ใหญ่พอ (ใช้ 20000) หรือวน offset
- ทุกแถวมี `areacode` (8 หลัก = จังหวัด 2 + อำเภอ 2 + ตำบล 2 + หมู่ 2), `hospcode`, `date_com` (`YYYYMMDDhhmm` เวลาประมวลผล = "ข้อมูล ณ"), `b_year` · **ไม่มีชื่อพื้นที่**
- **Python ในเครื่อง (python.org 3.13) ไม่มี root cert → `urllib` ล้ม `CERTIFICATE_VERIFY_FAILED` · ต้องใช้ `requests` (มี certifi แล้ว)**
- ไม่เสถียร: เคยได้ `404` หลังรอ 60 วิ (สิงห์บุรี 2568) → retry 3 ครั้ง backoff 5/15/45 วิ · timeout 120 วิ · ยิงทีละคำขอ

| ตัวชี้วัด | tableName | body | ขนาด/เวลา (ทดสอบ 2026-09-29) |
|---|---|---|---|
| DSPM | `s_childdev_specialpp` | `{"tableName":..,"year":"2569","province":"15","type":"json","limit":20000}` | อ่างทอง 3,156 แถว / 42 วิ · 1 แถว = hospcode × areacode × `monthly` |
| Coverage | `s_child0_5_pshyche_develop_coverage` | `{"tableName":..,"year":"2569","type":"json","limit":20000}` **ห้ามส่ง `province`** (400) → filter `provcode` เอง | 2567/2568: 77 แถว (รายจังหวัด) · 2569: 928 แถว (รายอำเภอ) / 0.2 วิ |

DSPM field ต่อกลุ่มอายุ suffix `_9 _18 _30 _42 _60` · "รวม 5 กลุ่มอายุ" = ผลรวม 5 suffix:

| key (§3.3) | field | | key | field |
|---|---|---|---|---|
| `target` | `target_*` | | `followed` | `follow_*` |
| `screened` | `result_*` | | `normal_after` | `1b260_2_*` |
| `normal_first` | `1b260_1_*` | | `delay_after_total` | `improper_*` |
| `suspect_wait30` | `1b261_*` | | `delay_after_codes` | `1b202_* 1b212_* 1b222_* 1b232_* 1b242_*` |
| `suspect_refer` | `1b262_*` | | `pending_followup` | `wait30_*` |
| `normal_female/male` | `1b260_f_* / 1b260_m_*` | | `lost_followup` | `loss_*` |

Coverage: `c_1…c_7, c_9, c_11` = คอลัมน์ (1)…(11) ของ Excel · **`c_8`, `c_10` ไม่ส่งมา** → คำนวณ `c_7/c_3×100`, `c_9/c_3×100` · `c_11` ไม่มีใน 2569

ผลตรวจกับ Excel: DSPM อ่างทอง 2568 รายอำเภอตรง 7/7 · ตำบล 2569 (`areacode[:6]`) ตรง (150101 ตลาดหลวง กลุ่ม 9 เดือน 8/3/3) · Coverage อ่างทอง 2569 รายอำเภอตรง · Coverage 2567 รายจังหวัดตรง (นครนายก 12,273)

`monthly` = เลขเดือน 2 หลัก [UNCERTAIN ว่าเป็นเดือนปฏิทินหรือลำดับในปีงบ] → **ขั้น 2 ต้องตรวจ**: ถ้าปี 2569 มีค่า 10, 11, 12 แสดงว่าเป็นเดือนปฏิทิน (ปีงบ = ต.ค.–ก.ย.) แล้วเรียงเดือนตามปีงบ

### 3.2 Excel HDC export (oracle) — 22 ไฟล์ใน `data/excel_reference/angthong/`

| ตัวชี้วัด | ปี | ประเทศ (13 เขต) | เขต 4 (8 จว.) | อ่างทอง (7 อำเภอ) | เมืองอ่างทอง (14 ตำบล) |
|---|---|---|---|---|---|
| DSPM | 2567–2569 | ✓ | ✓ | ✓ | ✓ |
| Coverage | 2567–2568 | ✓ | ✓ | ✗ | ✗ |
| Coverage | 2569 | ✓ | ✓ | ✓ | ✗ |

- ชื่อไฟล์ไม่สม่ำเสมอ (`เขต4`/`เขต 4`, `อำเภอเมือง`/`อำเภอเมืองอ่างทอง`) → **ระบุระดับจากหัวคอลัมน์ A** (`เขตสุขภาพ`/`จังหวัด`/`อำเภอ`/`ตำบล`) · จับคู่แถวด้วย**ชื่อ** (ลำดับต่างกันข้ามปี)
- 2569 DSPM: แถวรวม label ว่าง → ถือเป็น `รวม` · เขต 13 ทั้งแถว 0 → `null`
- Layout DSPM: header 4 แถว ข้อมูลเริ่มแถว 5 · คอลัมน์ A ชื่อ · 6 กลุ่ม `total, m9, m18, m30, m42, m60` · กลุ่ม total กว้าง 22 (2569: 24) กลุ่มอายุกว้าง 21 (2569: 23) · ลำดับฟิลด์: target, screened, pct_screened, normal_first, [pct_normal_first เฉพาะ total], suspect_wait30, suspect_refer, suspect_total, pct_suspect, followed, pct_followed, normal_after, delay_after_total, codes×5, pending_followup, lost_followup, [normal_female, normal_male เฉพาะ 2569], normal_total, pct_normal · รวม 128 คอลัมน์ (2569: 140)
- Layout Coverage: header 2 แถว ข้อมูลเริ่มแถว 3 · A ชื่อ · B–L = (1)…(11) · 2569 ไม่มี (11)

### 3.3 Metric keys และสูตร (ตรวจกับ Excel ผ่านทุกแถวทุกปี)

DSPM ต่อกลุ่ม: `target, screened, pct_screened=screened/target, normal_first, suspect_wait30, suspect_refer, suspect_total=wait30+refer, pct_suspect=suspect_total/screened, followed, pct_followed=followed/suspect_wait30` (**ไม่ใช่** /suspect_total)`, normal_after, delay_after_total, delay_after_codes{1B202,1B212,1B222,1B232,1B242}, pending_followup, lost_followup, normal_female, normal_male (2569), normal_total=normal_first+normal_after, pct_normal=normal_total/target` (**headline**)

Coverage: `population, prevalence(21.7), expected, served_teda4i, served_icd9, diagnosed_icd10, reached_cum, pct_reached_cum=reached_cum/expected, reached_fy, pct_reached_fy=reached_fy/expected` (**headline**)`, out_of_province`

### 3.4 Source matrix (ระดับไหนมาจากไหน)

| ตัวชี้วัด | country (13 เขต) | region 4 (8 จว.) | province 15 (7 อำเภอ) | district 1501 (14 ตำบล) | monthly |
|---|---|---|---|---|---|
| DSPM | Excel | Excel | **API** `province=15` group `areacode[:4]` | **API** group `areacode[:6]` | **API** group `monthly` (จังหวัด/อำเภอ/ตำบล) |
| Coverage 2567–68 | **API** group เขต | **API** filter เขต 4 | ไม่มีข้อมูล | ไม่มีข้อมูล | – |
| Coverage 2569 | **API** group เขต | **API** filter เขต 4 | **API** filter `provcode=15` | ไม่มีข้อมูล | – |

แถว "รวม" ของ scope: ใช้ผลรวมจากแถวลูก **ยกเว้น** ระดับที่มาจาก Excel ใช้แถว `รวม` ของไฟล์ · จังหวัดอ่างทองใน region view (Excel) กับ province view (API) ต้องเท่ากัน → เป็น verify case

### 3.5 Validation (ใน `kpi.py verify` และท้าย `update`)

**Hard error** (exit ≠ 0): สูตรใน §3.3 (tol 0.06) · `suspect_wait30 == followed + pending_followup + lost_followup` · จำนวนแถว: country 13, region 8, province 7, district 14 · **ทุกตัวเลขที่ Excel มี ต้องเท่ากับที่สร้างจาก API 100%** (เทียบทุก key ทุกกลุ่ม ทุกแถว ทุกปี ที่ทั้งสองแหล่งมี)

**Warning**: `followed == normal_after + delay_after_total` (HDC คลาดระดับเขต) · `normal_total == female+male` (คลาด 2569) · `expected ≈ population×0.217`

## 4. เป้าหมายและกฎสี

| ตัวชี้วัด | metric | 2567 | 2568 | 2569 | ที่มา |
|---|---|---|---|---|---|
| DSPM | `pct_normal` | 85 [UNCERTAIN] | 87 | 88 | KPI_template_2568/2569 (spd.moph.go.th) |
| Coverage | `pct_reached_fy` | – | 20 [UNCERTAIN] | 30 | คู่มือ PA กรมสุขภาพจิต 2569 KPI 12 |

- เก็บใน `sites/angthong.json` → `targets[indicator][year]` · ค่า [UNCERTAIN] มี `"note"` แสดง `*` + tooltip "เป้าหมายอ้างอิง ยังไม่ยืนยัน"
- ตัวชี้วัดย่อยไม่มีเส้นเป้า
- สี: `ok` ≥ เป้า · `warn` [เป้า−5, เป้า) · `bad` < เป้า−5 · `na` · `small_n` ตัวหาร < 20 → สีจาง + ป้าย "n<20" ไม่นับในอันดับ/จุดควรพัฒนา · ไม่ใช้สีอย่างเดียว มีไอคอน ✓ / ! / ✗

## 5. Data model

### 5.1 Lookup `data/lookup/areas.json`
`{"provinces": {"15": {"name":"อ่างทอง","region":4}, ...77}, "districts": {"1501":"เมืองอ่างทอง", ...}, "subdistricts": {"150101":"ตลาดหลวง", ...}, "regions": {"1":"เขตสุขภาพที่ 1", ...,"13":"เขตสุขภาพที่ 13"}}`
- ดึงจากชุดรหัส DOPA แบบเปิด (ทั้งประเทศ) + ตาราง จังหวัด→เขตสุขภาพ ของ สธ. · บันทึก URL ที่มาใน `data/lookup/SOURCE.md`
- **ต้องตรวจ**: 7 อำเภอ + 14 ตำบลของอ่างทอง ตรงชื่อใน Excel ทุกตัว · 8 จังหวัดเขต 4 = นครนายก นนทบุรี ปทุมธานี พระนครศรีอยุธยา ลพบุรี สระบุรี สิงห์บุรี อ่างทอง · ถ้าหาแหล่งไม่ได้ ใช้ชื่อจาก Excel อ่างทองตามลำดับรหัส (ยืนยันแล้ว 150101 = ตลาดหลวง, 1501–1507 ตามลำดับ Excel)

### 5.2 Cache `data/cache/<indicator>/<year>/<provcode>.json` (commit)
DSPM: aggregate จาก raw เป็น `areacode6 × monthly` (ทุก field ดิบ) · Coverage: แถวตามที่ API ให้ (ทั้งประเทศ ไฟล์เดียว `all.json`) · เก็บ `date_com` สูงสุด, `fetchedAt`, `rowCount`

### 5.3 JSON เว็บ `site/data/angthong/`
- `index.json`: `{schema, site, org, logo, indicators:{dspm:{...metadata §5.4}, coverage:{...}}, targets, tree, datasets:[{indicator, year, level, scope, file, asOf, source:"api"|"excel"}]}`
- `tree`: `{"code":"TH","level":"country","name":"ประเทศ","children":[{"code":"4","level":"region","name":"เขตสุขภาพที่ 4","children":[{"code":"15","level":"province","name":"อ่างทอง","children":[{"code":"1501","level":"district","name":"เมืองอ่างทอง"}]}]}]}` — เว็บใช้ตัดสินว่ากดเจาะต่อได้ไหม
- `<indicator>_<year>_<level>_<scopeCode>.json` เช่น `dspm_2569_province_15.json`:

```json
{"schema":1,"site":"angthong","indicator":"dspm","year":2569,
 "level":"province","scope":{"code":"15","name":"อ่างทอง","parent":{"level":"region","code":"4"}},
 "asOf":"2569-09-29T09:08","source":"api",
 "rows":[{"code":"1501","name":"เมืองอ่างทอง","hasData":true,
          "groups":{"total":{"target":1014,"screened":832,"pct_screened":82.05,"...":0},
                    "m9":{},"m18":{},"m30":{},"m42":{},"m60":{}}}],
 "total":{"code":"15","name":"รวม","groups":{}}}
```
- Coverage ใช้ `"metrics":{...}` แทน `groups`
- `dspm_<year>_monthly_<scopeCode>.json`: `{"months":[{"fyIndex":1,"calMonth":10,"label":"ต.ค.","screened":..,"target":..,"normal_total":..,"cum":{...}}], "rows":[{code,name,months:[...]}]}` สำหรับ province 15, district 1501 และตำบล (rows)
- ตัวเลขเป็น number หรือ `null` ห้าม string · level ∈ `country|region|province|district` · scopeCode ของ country = `TH`

### 5.4 Indicator metadata (plugin) — ผลิตโดย `scripts/indicators/<id>.py`
`{id, name_th, short, source:{table, bodyTemplate, needsProvince}, levels:[...], groups:[{key,label}] | null, headline:{metric, num, den}, cards:[{metric,label,num,den}], table:[{key,label}], monthly:bool, targets_key}` — เว็บ **ไม่ hardcode** ชื่อ metric ของ DSPM/Coverage ใน JS นอกเหนือจาก metadata นี้

## 6. โครงสร้างเว็บ

### 6.1 URL
- `/` → `/angthong/` (Cloudflare `_redirects`: `/  /angthong/  302`)
- `/angthong/` single-page · hash `#/<indicator>/<year>/<level>/<scopeCode>` เช่น `#/dspm/2569/province/15` · default `#/dspm/2569/country/TH`

### 6.2 ส่วนบน (คงที่)
โลโก้ (โปร่ง; dark = บนแถบขาวมุมมน) · "ระบบติดตามตัวชี้วัด จังหวัดอ่างทอง" · "โรงพยาบาลอ่างทอง" · แท็บตัวชี้วัด (สร้างจาก `index.json`) · ปี 2567 · 2568 · **2569** (ป้าย "ปีงบปัจจุบัน") · ปุ่ม light/dark · บรรทัด "ข้อมูล ณ <asOf ของ dataset ที่กำลังดู> · <source>"

### 6.3 Breadcrumb
`ประเทศ › เขตสุขภาพที่ 4 › อ่างทอง › เมืองอ่างทอง` กดย้อนได้

### 6.4 เนื้อหาต่อ 1 ชั้น
1. **Headline card**: % ใหญ่ + สี + `n / d` + เป้า + อันดับในกลุ่มพี่น้อง + Δ จากปีก่อน
2. **การ์ดรอง** จาก `cards` ใน metadata (DSPM: คัดกรอง / สงสัยล่าช้า / ติดตามได้ · Coverage: สะสม / TEDA4I / ICD-10) มี `n / d`
3. **Bar chart พื้นที่ลูก** แนวนอน เรียงมาก→น้อย · เส้นเป้า · ไฮไลต์เส้นทางอ่างทอง · **กดแท่ง = เจาะ** (ถ้า tree มีลูก) · tooltip `n / d`
4. **Line chart 3 ปี** ของ scope + เส้นเป้ารายปี + เส้น parent จาง
5. **Monthly chart** (DSPM ระดับ province/district/ตำบลที่เลือก): ความคืบหน้าสะสมในปีงบ ต.ค.→ก.ย. — เส้น "คัดกรองสะสม/เป้าหมายทั้งปี %" และ "สมวัยสะสม/เป้าหมาย %" + เส้นเป้า 88 · แสดงเดือนล่าสุดที่มีข้อมูล
6. **Heatmap** พื้นที่ลูก × (รวม, 9, 18, 30, 42, 60 เดือน) — % สี + `n/d` เล็ก · Coverage: พื้นที่ลูก × (ปีงบ, สะสม)
7. **กล่อง "จุดควรพัฒนา"**: 3 ช่องห่างเป้ามากสุด (ตัด n<20 / na) เป็นประโยค เช่น "ตำบลบ้านแห · 30 เดือน · สมวัย 71.2% (52/73) ต่ำกว่าเป้า 16.8 จุด"
8. **แท็บกลุ่มอายุ** (DSPM): 9/18/30/42/60 → การ์ด+bar+line ใช้กลุ่มนั้น
9. **ตารางเต็ม** ยุบไว้ (ทุก key รวม codes + เพศ) + ปุ่ม CSV
10. ชั้น/ปีที่ไม่มีข้อมูล → กล่อง "ไม่มีข้อมูลระดับนี้ในปี …" ปิดการเจาะ

### 6.5 หน้าแรก (country) เพิ่ม "เส้นทางลัด" 3 การ์ด: เขต 4 · อ่างทอง · เมืองอ่างทอง (% ปีปัจจุบัน, กดไปได้ทันที)

## 7. Visual design
- ฟอนต์ **Sarabun** (Google Fonts) · `tabular-nums` · headline ≥ 56px จอใหญ่ · body 16–18px
- max-width 1400px · มือถือ ≤ 600px เรียง 1 คอลัมน์ · ไม่มี horizontal scroll (ตารางเต็ม scroll ในกรอบ)
- contrast ≥ 4.5:1 ทั้งสอง theme · CSS variables `:root` + `[data-theme="dark"]` · จำใน localStorage
- Chart.js 4 + chartjs-plugin-annotation จาก cdnjs · ปิด animation บนมือถือ
- ก่อนเขียนกราฟ Opus ต้องโหลด skill `dataviz` และ `artifact-design`
- ไฟล์: `site/assets/styles.css`, `site/assets/app.js` + `modules/{data,router,charts,format,components/*}.js` (ES modules)
- โลโก้: `scripts/process_logo.py` → threshold ≥ 245 → alpha 0 (ขอบไล่ระดับ) → crop ขอบว่าง → `site/assets/logo-angthong.png` กว้าง 800px

## 8. โครงสร้าง repo

```
kpi-health/
├── README.md                 # คำสั่งอัปเดต + คู่มือ Cloudflare + เพิ่มตัวชี้วัดใหม่ยังไง
├── web_spec.md
├── docs/API_NOTES.md         # ย้ายจากโฟลเดอร์เก่า
├── sites/angthong.json       # org, logo, home path (TH→4→15→1501), targets, indicators ที่เปิดใช้, ปีที่ดึง
├── data/
│   ├── excel_reference/angthong/{dspm,coverage}/<ปี>/*.xlsx   # 22 ไฟล์ oracle
│   ├── lookup/areas.json + SOURCE.md
│   ├── cache/<indicator>/<ปี>/<provcode|all>.json            # commit
│   └── raw_api/                                              # .gitignore
├── scripts/
│   ├── kpi.py                # CLI: update | fetch | build | verify  (argparse, --site, --indicator, --year, --refresh)
│   ├── loaders/moph_api.py   # requests + retry/backoff + cache
│   ├── loaders/xlsx_hdc.py   # อ่าน Excel → โครงเดียวกับ API aggregate
│   ├── indicators/{dspm,coverage}.py   # metadata + aggregate + formulas (plugin)
│   ├── build_site.py         # cache/Excel → site/data JSON + index.json
│   ├── verify.py             # เทียบ API-built vs Excel 100%
│   ├── process_logo.py
│   └── requirements.txt      # requests, certifi, openpyxl, pillow
├── site/                     # Cloudflare output dir
│   ├── index.html  _redirects  angthong/index.html  assets/  data/angthong/*.json
├── .gitignore
```

`kpi.py update --site angthong` = fetch (ใช้ cache ถ้ามี) → build → verify → รายงาน (ไฟล์/แถว/asOf/error/warning) · exit ≠ 0 ถ้า hard error · `git push` แยกต่างหาก

## 9. Deploy
1. Orchestrator: `git init` → commit → **ขอยืนยัน** → `gh repo create parinyapaw-del/kpi-health --public --source . --push`
2. Save (ครั้งเดียว): Cloudflare → Workers & Pages → Create → Pages → Connect to Git → `kpi-health` → Project name `kpi-health` (สำรอง `kpi-health-th`) → Build command ว่าง → Output dir `site` → Deploy
3. หลังนั้น push main → deploy อัตโนมัติ
4. รอบถัดไป: `python3 scripts/kpi.py update --site angthong --year 2570` → ดูรายงาน → `git add -A && git commit && git push` · DSPM ระดับประเทศ/เขต 4 ปีใหม่ต้อง export Excel 2 ไฟล์วางใน `excel_reference` (จน Phase 2 ทำ loop 77 จังหวัด)

## 10. แผน Phase 1 (session ใหม่)

| ขั้น | ผู้ทำ | งาน | เกณฑ์ผ่าน |
|---|---|---|---|
| 0 | Save | เปิด session ใน `~/Desktop/Claude/web project/kpi-health/` สั่ง "execute web_spec.md" | – |
| 1 | Orchestrator | สร้างโครง §8 · **ย้าย** จาก `~/Desktop/Claude/web project/พัฒนาการเด็ก พี่ต้อง/`: Excel 22 ไฟล์ → `excel_reference` (จัดโฟลเดอร์ใหม่ตาม indicator/ปี), `API_NOTES.md` → `docs/`, `logo.webp` → `data/` แล้วลบโฟลเดอร์เก่า · เขียน `sites/angthong.json`, `.gitignore`, `_redirects` | โครงตรง §8 · ไม่มีไฟล์ตกหล่น |
| 2 | Sonnet | `loaders/moph_api.py`, `loaders/xlsx_hdc.py`, `indicators/*.py`, `build_site.py`, `verify.py`, `kpi.py`, `process_logo.py`, `lookup/areas.json` (+ตรวจชื่อ) · ตรวจความหมาย `monthly` (§3.1) · รัน `kpi.py update` จริง | verify 0 error · แถวครบ · JSON ตรง §5 · โลโก้โปร่ง |
| 3 | Orchestrator | ตรวจด้วยมือ 6 จุดเทียบ Excel: อ่างทอง 2568 total 83.58 = 4,748/5,681 · เมืองอ่างทอง 2569 m9 · ตลาดหลวง 2567 total 92.78 = 90/97 · เขต 4 2567 Coverage (10) 9.14 · อ่างทอง 2569 Coverage เมือง 10.96 = 48/438 · เขต 13 2569 = null | ตรงทุกจุด |
| 4 | Opus | หน้าเว็บ §6–7 (โหลด `dataviz`, `artifact-design`) | ทุก component §6.4 · เจาะ 4 ชั้น · hash routing · dark/light · monthly chart |
| 5 | Orchestrator | ตรวจใน browser 1440 / 375: ไม่มี console error, ไม่มี horizontal scroll, ตัวเลขการ์ดตรง JSON, กดแท่งเจาะได้, hash เปิดตรงหน้า | ผ่านทุกข้อ |
| 6 | Orchestrator | README + commit + **ขอยืนยัน** → `gh repo create` + push | repo บน GitHub |
| 7 | Save | เชื่อม Cloudflare (§9.2) ส่ง URL กลับ | เปิดได้จากมือถือ |
| 8 | Orchestrator | ตรวจ URL จริง · บันทึก memory (project: repo, URL, วิธีอัปเดต) | – |

## 11. Phase 2+ (จดไว้ ไม่ทำตอนนี้)
- เพิ่มตัวชี้วัดใหม่ = เพิ่ม `scripts/indicators/<id>.py` + Excel oracle (ถ้ามี) + targets ใน site config · Save จะให้ tableName/วิธีดึงเอง
- DSPM loop 77 จังหวัด (ระดับประเทศ/เขต จาก API) · GitHub Actions รายเดือน · custom domain · ย้าย Vite+React เมื่อ component เกิน ~15

## 12. สมมติฐานที่ยังไม่ยืนยัน
- [UNCERTAIN] เป้า DSPM 2567 = 85 · Coverage 2568 = 20 · ความหมาย `monthly` (ตรวจขั้น 2)
- [INFERRED] Coverage headline = คอลัมน์ (10) ตามช่วงข้อมูลคู่มือ 1 ต.ค.–31 ส.ค. · ชื่อ `kpi-health` ว่างบน pages.dev · ระดับตำบลของ DSPM จาก API = Excel ทุกตัว (ตรวจแล้ว 1 ตำบล 1 กลุ่มอายุ; verify ขั้น 2 จะเทียบครบ)
