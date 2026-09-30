# web_spec_phase2.md — ระบบติดตามตัวชี้วัดเข็มมุ่งพัฒนาการเด็ก เขตสุขภาพที่ 4 (kpi-health Phase 2 / 2b)

| | |
|---|---|
| Version | **2.0** (ล็อกหลัง grilling 39 ข้อ · ต่อจาก `web_spec.md` v1.1 ซึ่งคงไว้เป็น reference ของ Phase 1) |
| วันที่ | 2026-09-30 |
| ผู้สั่ง | Save (Parinya Pawenawan) — จัดทำโดย รพ.อ่างทอง สำหรับเขตสุขภาพที่ 4 |
| สถานะ | **approved → Phase 2 execute ใน session ใหม่** ที่เปิดใน `~/Desktop/Claude/web project/kpi-health/` ด้วยคำสั่ง "execute web_spec_phase2.md" · Phase 2b (admin) execute เป็น session ถัดไปด้วยคำสั่ง "execute web_spec_phase2.md phase 2b" |
| Model | **Fable = plan + ตรวจทุกขั้น** (อ่าน spec นี้ทั้งไฟล์ก่อน) · **Sonnet = pipeline ข้อมูล + โลโก้ + Actions** · **Opus = หน้าเว็บ + Pages Functions + admin** |

> spec นี้เขียนให้ session ใหม่ทำงานได้โดยไม่ต้องรู้บทสนทนา · อ่านคู่กับ `web_spec.md` (โครงข้อมูล/สูตร/API ยังใช้ของเดิมทุกข้อที่ไม่ได้เขียนทับในนี้) และ `README.md` · ห้ามเดาตัวเลข (CLAUDE.md rule 4) · ถ้าอะไรใน spec ขัดกับของจริงในเครื่อง ให้หยุดรายงาน ไม่แก้เอง

## 1. สิ่งที่เปลี่ยนจาก Phase 1 (ภาพรวม)

| เรื่อง | Phase 1 | Phase 2 |
|---|---|---|
| ขอบเขต | เว็บของ **จังหวัดอ่างทอง** เจาะ ประเทศ → เขต 4 → อ่างทอง → เมืองอ่างทอง | เว็บของ **เขตสุขภาพที่ 4** เจาะ เขต 4 → **8 จังหวัด** → **ทุกอำเภอ** → **ทุกตำบล** (ทั้ง 2 ตัวชี้วัด) |
| ชื่อ / โลโก้ | "ระบบติดตามตัวชี้วัด จังหวัดอ่างทอง" · โลโก้ รพ.อ่างทอง | **"ระบบติดตามตัวชี้วัดเข็มมุ่งพัฒนาการเด็ก เขตสุขภาพที่ 4"** · โลโก้เขต 4 เป็นหลัก · "จัดทำโดย โรงพยาบาลอ่างทอง" + โลโก้อ่างทองเล็ก ใต้ header และใน footer |
| ปี | 2567–2569 สลับได้ + แนวโน้ม 3 ปี | **2569 เท่านั้น** · 2570 โผล่เองเมื่อ API มีข้อมูล · ไม่มีแนวโน้ม/Δ ปีก่อน |
| หน้าแรก | ระดับประเทศ + การ์ดเส้นทางลัด | **ระดับเขต 4** → กราฟ 13 เขต → กราฟ 8 จังหวัด (กดเจาะ) → heatmap 8 จังหวัด |
| กราฟ | แนวนอน + tooltip | **แนวนอนทุกกราฟ** ตัวเลข `% (n/d)` บนแท่งเสมอ |
| Coverage | headline = (10) ปีงบ · การ์ด สะสม/TEDA4I/ICD-10 | **headline = (8) สะสม** เป้า 30 · การ์ด (4) TEDA4I / (5) ICD9CM / (6) ICD-10 · กราฟ แดง=คาดประมาณ 100% เขียว=สะสม เส้น 30% |
| ตัดออก | – | กราฟรายเดือน · แนวโน้ม 3 ปี · กล่อง "จุดควรพัฒนา" · การ์ดเส้นทางลัด · หน้า country แยก · ปี 2567–2568 |
| ตำบล | กฎ "ตำบลที่หน่วยมีเป้ามากสุด" [INFERRED] เฉพาะเมืองอ่างทอง | **ที่ตั้งหน่วยจากทะเบียน MOPH GIS** (§4.3) ทุกอำเภอ · fallback กฎเดิมเฉพาะหน่วยที่ไม่มีในทะเบียน |
| Backend | static ล้วน | + **Pages Functions** `/api/hit` (D1) นับผู้ใช้/หน้า · Phase 2b: `/api/config`, `/api/admin/*` (KV + Google Sign-In) |
| อัปเดต | Save รันเอง | **GitHub Actions ทุกวัน 07:00 ICT** + กดเองได้ · แจ้งเตือนด้วย GitHub Issue |
| URL | `/` → `/angthong/` | **เปิดที่ `/`** · `/angthong/*` redirect กลับ `/` (link เก่าไม่ตาย) |

## 2. Decision log (grilling รอบ 1–3, 2026-09-30)

| # | เรื่อง | ตัดสินใจ |
|---|---|---|
| Q1 | โลโก้เขต 4 | ใช้ `logo เขต 4.jpg` (ขาว-ดำ 2048px ขอบขาว ~40%) → ตัดขอบให้เรียบร้อย + พื้นโปร่ง ด้วย `process_logo.py` → `site/assets/logo-r4.png` · dark theme กลับสีเส้นเป็นขาว (CSS `filter: invert(1)` เฉพาะ dark) · ถ้าได้ไฟล์สีภายหลังวางทับแล้วรันซ้ำ |
| Q2 | "จัดทำโดย รพ.อ่างทอง" | **ทั้ง 2 ที่**: บรรทัดเล็กใต้ชื่อเว็บใน header (โลโก้อ่างทอง ~24px) และ footer (โลโก้ + ข้อความ + ยอดผู้ใช้ + ข้อมูล ณ) |
| Q3 | URL | เปิดที่ root `/` · hash `#/<indicator>/<year>/<level>/<code>` เหมือนเดิม · `_redirects`: `/angthong/*  /  301` · site id ภายในยังเป็น `angthong` ได้ (ไม่ rename ไฟล์/โฟลเดอร์ `sites/angthong.json`, `site/data/angthong/`) |
| Q4 | ชื่อตัวชี้วัด | แท็บ = ชื่อย่อ **"สมวัย"** / **"เข้าถึงบริการ"** · หัวเรื่องใต้แท็บ = ชื่อเต็ม (§5.2) · มือถือชื่อเต็มขึ้น 2 บรรทัดได้ |
| Q5 | ปี | เว็บมี 2569 เท่านั้น · ปุ่มสลับปีโผล่เมื่อ ≥ 2 ปี · ตัดแนวโน้ม 3 ปี + Δ ปีก่อน · pipeline build เฉพาะปีใน config · cache 2567–68 เก็บในเครื่องไม่ขึ้นเว็บ ลบ `site/data/**/*_2567_*`, `*_2568_*` |
| Q6 | จุดควรพัฒนา | ตัดกล่องออกทุกหน้า · heatmap ตอบแทน · เรียงตามรหัสพื้นที่ + ปุ่มสลับเรียงตาม % |
| Q7 | โครงหน้าแรก | header → headline เขต 4 + การ์ดรอง → กราฟ 13 เขต → กราฟ 8 จังหวัด (กดเจาะ) → heatmap 8 จังหวัด → ตารางเต็ม (ยุบ) · ตัดการ์ดเส้นทางลัด |
| Q8 | 2 ตัวชี้วัด | แท็บสลับ (sticky บนมือถือ) ไม่เรียงต่อกัน |
| Q9 | ระดับประเทศ | กราฟ 13 เขตบนหน้าแรกอย่างเดียว · ไม่มีหน้า country · กดเขตอื่นไม่ได้ |
| Q10 | รายเดือน | **ตัดออกทั้งหมด** (pipeline ไม่ต้อง build `*_monthly_*`, ลบ `components/monthly.js`) |
| Q11 | ความลึก | **ทุกอำเภอทั้ง 8 จังหวัดกดลงตำบลได้** (70 อำเภอ ≈ 713 ตำบล) ทั้ง DSPM และ Coverage |
| Q12 | หน้ารายจังหวัด/อำเภอ | headline แถวเล็ก → **heatmap** → กราฟแนวนอน (กดเจาะ) → ตารางเต็ม · ทุกอำเภอโครงเดียวกัน ไม่มีอำเภอ "บ้าน" |
| Q13 | กราฟ | แนวนอนทุกกราฟ · label `88.1% (4,748/5,681)` ทุกแท่งไม่ต้อง hover · มือถือ `88.1% · 4,748/5,681` ใต้ชื่อ |
| Q14 | สีแท่ง DSPM | ตามสถานะ ok/warn/bad + เส้นเป้า · ไฮไลต์พื้นที่ที่กำลังดูด้วยกรอบ |
| Q15 | Coverage (9)/(10) | รวมในการ์ด headline สะสม: บรรทัดเล็ก "ปีงบนี้ 48 คน (11.0%)" |
| Q16 | Heatmap Coverage | 4 คอลัมน์: (8) สะสม % [สีตามเป้า 30] · (4)/(3) TEDA4I % · (5)/(3) ICD9CM % · (6)/(3) ICD-10 % [สีกลางไล่เฉด] |
| Q17 | Heatmap มือถือ | เลื่อนซ้าย-ขวาในกรอบ · คอลัมน์ชื่อพื้นที่ sticky |
| Q18 | ยอดผู้ใช้ | ผู้ใช้โดยประมาณ (1 เครื่อง/วัน = 1) + วันนี้ · **นับรายหน้า** (ตัวชี้วัด/ระดับ/รหัสพื้นที่) + จังหวัด/เมืองผู้เข้าชมจาก Cloudflare geo · footer "ผู้ใช้งาน N คน · วันนี้ M · ไม่เก็บข้อมูลส่วนบุคคล" |
| Q19/Q29 | Admin login | **Google Sign-In** ตรวจ ID token ใน Pages Function · allowlist ใน KV (2 อีเมลของ Save ตั้งต้น — **ไม่เขียนอีเมลใน repo public**, ใส่ผ่าน setup ตาม §8.4) · ไม่ใช้ Cloudflare Access (ไม่แน่ใจเรื่องบัตร) |
| Q20 | Admin แก้อะไร | ข้อความทั้งหมด (ชื่อเว็บ, จัดทำโดย, ชื่อเต็ม/ย่อตัวชี้วัด, ป้ายการ์ด, footer) + **เป้าหมาย** + ปีปัจจุบัน · เว็บอ่าน `/api/config` ทับค่าใน `index.json` |
| Q21 | โหลด spec | ปุ่มในหน้า admin ได้ `.md` ไฟล์เดียว = spec ล่าสุด + config ปัจจุบันจาก KV + วิธีอัปเดต/เชื่อม Cloudflare จาก README · ไม่รวมตัวเลข |
| Q22 | แบ่งเฟส | **Phase 2** = เว็บ + ข้อมูล + ยอดผู้ใช้ (D1) + Actions · **Phase 2b** = Google Sign-In + KV config + admin + spec download (spec ไฟล์เดียวกัน) |
| Q23/Q31 | อัปเดตอัตโนมัติ | GitHub Actions cron **ทุกวัน 07:00 ICT (00:00 UTC)** อัตโนมัติ + `workflow_dispatch` |
| Q25 | ยืนยันกฎตำบล | Save ให้ Excel DSPM 2569 เพิ่ม 4 ไฟล์ (สระบุรี/อยุธยา รายอำเภอ · หนองแค/ท่าเรือ รายตำบล) → พบกฎเดิมผิดที่ท่าเรือ → เปลี่ยนไปใช้ทะเบียนที่ตั้งหน่วย (§4.3) |
| Q26 | ที่เก็บสถิติ/config | **D1** เก็บ hit (ฟรี 100k writes/วัน) · **KV** เก็บ config admin · Save login Cloudflare ใน browser pane แล้ว Claude กด bind ให้ |
| Q27 | บันทึกต่อ hit | วัน-เวลา · route · ธง "เครื่องใหม่ของวัน" (localStorage) · `cf.region` + `cf.city` ของผู้ชม · **ไม่เก็บ IP / user-agent / id** |
| Q28 | ดูสถิติ | footer สาธารณะ = ยอดรวม + วันนี้ · ตารางรายหน้า/รายจังหวัดผู้ชม ดูในหน้า admin (2b) · เก็บตั้งแต่ Phase 2 |
| Q30 | หน้า admin | ① ฟอร์มข้อความ/เป้า + preview ② สถิติ (รายวัน/รายหน้า/จังหวัดผู้ชม เลือกช่วงวัน) ③ จัดการอีเมล admin (ห้ามลบตัวเอง) ④ โหลด spec.md ⑤ คืนค่าเริ่มต้น · role เดียว |
| Q32 | เมื่อ Actions ล้ม | ไม่ commit · workflow แดง (GitHub อีเมลอัตโนมัติ) · เว็บคงข้อมูลเดิม ไม่แสดงป้ายบนเว็บ |
| Q33 | ปี 2570 | **auto**: Actions ตรวจ API พบ `b_year` ใหม่ที่มีแถว → เพิ่มปีใน config เอง, `currentYear` = ปีล่าสุดที่มีข้อมูล, เป้า = `null` → เว็บแสดง "เป้าหมาย: ยังไม่กำหนด" สีกลาง จน Save ใส่เป้าใน admin/config · ข้อมูลเอาเท่าที่มี |
| Q34/Q38 | Coverage ตำบล | ทำด้วยที่ตั้งหน่วยจากทะเบียนเดียวกัน · ป้ายหัวตาราง "[INFERRED] ไม่มีรายงาน HDC ระดับตำบลให้ตรวจสอบ" |
| Q35 | อำเภอ | ทุกอำเภอเท่ากัน · เส้นทาง "บ้าน" = เขต 4 อย่างเดียว |
| Q37 | หน่วยนอกทะเบียน | fallback กฎเป้ามากสุดเฉพาะหน่วยนั้น · footnote ใต้ตารางตำบล "หน่วย n แห่งใช้การอนุมานที่ตั้ง" · ป้าย [INFERRED] เฉพาะอำเภอที่มีหน่วยแบบนี้ · ตารางอำเภอที่กระทบอยู่ใน §4.4 ให้ Save export Excel มาเทียบเพิ่ม |
| Q39 | แจ้งเตือน | workflow เปิด **GitHub Issue อัตโนมัติ** (พบปีใหม่ / verify ล้ม / API ล่ม) → GitHub ส่งอีเมลถึง Save · ปิด Issue เองเมื่ออ่านแล้ว |

## 3. ข้อเท็จจริงที่ตรวจแล้ว 2026-09-30 (ใช้ตัดสินใจ ไม่ต้องตรวจซ้ำ แต่ถ้าไม่ตรงให้หยุดรายงาน)

- **DSPM cache รายจังหวัดมีครบ 77 จังหวัด × 2567–2569** ใน `data/cache/dspm/<ปี>/<prov>.json` (ละเอียด `areacode6 × unit6 × monthly`) แต่ `.gitignore` commit เฉพาะ `15.json` + `provinces.json` · เขต 4 ปี 2569 รวม 8 ไฟล์ ≈ 1.8 MB · raw response อยู่ `data/raw_api/s_childdev_specialpp/<ปี>/<prov>.json` (มี `hospcode`; ไม่ commit)
- **Coverage 2569 มีรายอำเภอครบทุกอำเภอของทั้ง 8 จังหวัด**: นนทบุรี 6 · ปทุมธานี 7 · พระนครศรีอยุธยา 16 · อ่างทอง 7 · ลพบุรี 11 · สิงห์บุรี 6 · สระบุรี 13 · นครนายก 4 = **70 อำเภอ** · แถว API = `hospcode × areacode(8)` จึงคำนวณตำบลได้ · ตำบลใน lookup: 52/60/209/73/124/43/111/41 = **713**
- **กฎตำบลเดิมผิดเมื่อหน่วยเป็นโรงพยาบาล**: ท่าเรือ (1402) — รพ.ท่าเรือ `10768` เป้า 122 กระจาย จำปา 73 / ท่าเรือ 26 / ท่าหลวง 23 → กฎ "เป้ามากสุด" ลงจำปา ทำให้ Excel HDC (ท่าเรือ 122, จำปา 41) ไม่ตรง · หนองแค (1903) ตรงเพราะทุกหน่วยเป้ามากสุดที่ตำบลตัวเอง · ยอดอำเภอไม่กระทบ (630 = 630)
- **ทะเบียนที่ตั้งหน่วย**: `GET https://opendata-service.moph.go.th/gis/v1/getgis/hoscode/{hoscode}` (ไม่ต้อง auth, GeoJSON) → `properties.provcode/distcode/subdistcode/hosname/hostype/dep` · `10768` → `14`+`02`+`01` = 140201 ท่าเรือ ✓ · `01167` รพ.สต.จำปา → 140202 ✓ · เขต 4 ปี 2569 มี **982 hospcode** ดึงครบแล้ว → พบ 882 ไม่พบ 100 (รายละเอียด §4.4) · **`data/lookup/units.json` สร้างแล้วในรอบ plan** · กฎ "ที่ตั้งตามทะเบียน + fallback" ตรง Excel รายตำบล 100% ทั้ง 3 อำเภอที่มีไฟล์ (เมืองอ่างทอง/หนองแค/ท่าเรือ) ไม่มีหน่วยตั้งข้ามอำเภอใน 3 อำเภอนี้ · endpoint รายจังหวัดไม่มี (404) ต้องยิงทีละ hoscode ≈ 0.45 วิ/ครั้ง
- **Excel oracle ใหม่ 4 ไฟล์** (DSPM 2569, layout เดียวกับของเดิม 140 คอลัมน์, header A1 = `อำเภอ`/`ตำบล`): `สระบุรีจังหวัด.xlsx` (13 อำเภอ) · `อำเภอหนองแค สระบุรี.xlsx` (18 ตำบล) · `อยุธยาจังหวัด.xlsx` (16 อำเภอ) · `อำเภอท่าเรือ อยุธยา.xlsx` (10 ตำบล) — ตอนนี้วางที่ root repo · สุ่มเทียบ cache ระดับอำเภอตรงทุกแถวที่ดู
- `logo เขต 4.jpg` 2048×2048 RGB ขาว-ดำ · แปดเหลี่ยม + ชื่อ 8 จังหวัด · ขอบขาวราว 40% ทุกด้าน
- เว็บ live: `https://kpi-health.pages.dev/` → 302 `/angthong/` (200) · repo `parinyapaw-del/kpi-health` public · Cloudflare Pages เชื่อม Git แล้ว (push main = deploy)
- โควตาฟรี Cloudflare: Pages Functions 100,000 req/วัน · **KV เขียน 1,000/วัน** (ไม่พอสำหรับ hit รายหน้า) · **D1 เขียน 100,000/วัน อ่าน 5M/วัน 5 GB** · Cloudflare Access ฟรี ≤ 50 คน แต่ [UNCERTAIN] ต้องผูกบัตรตอนเปิด Zero Trust → ไม่ใช้
- `chospital` / `s_hospital` บน `opendata.moph.go.th/api/report_data` มีตารางแต่ใช้ไม่ได้ (400 Parameter Invalid / 0 แถว) · `hcode.moph.go.th` เป็น dashboard ไม่มี export · `data.go.th` ไม่มีทะเบียนรหัสหน่วยทั้งประเทศ
- ปีงบ 2570 เริ่ม **1 ต.ค. 2569 (พรุ่งนี้)** → Actions รอบแรก ๆ อาจพบ `b_year=2570` ทันที

## 4. Pipeline ข้อมูล (Sonnet) — เปลี่ยนจาก Phase 1

### 4.1 Config `sites/angthong.json`
```json
{
  "name": "ระบบติดตามตัวชี้วัดเข็มมุ่งพัฒนาการเด็ก เขตสุขภาพที่ 4",
  "org": "จัดทำโดย โรงพยาบาลอ่างทอง",
  "logo": "assets/logo-r4.png", "orgLogo": "assets/logo-angthong.png",
  "home": {"level": "region", "code": "4", "name": "เขตสุขภาพที่ 4"},
  "drill": {"provinces": ["12","13","14","15","16","17","19","26"], "districts": "all", "subdistricts": "all"},
  "indicators": ["dspm", "coverage"],
  "years": [2569], "currentYear": 2569, "autoYear": true,
  "targets": {"dspm": {"2569": {"value": 88}}, "coverage": {"2569": {"value": 30}}},
  "colorRules": {"warnBand": 5, "smallN": 20},
  "excel": {"dir": "data/excel_reference", "sourceLabel": "HDC export"}
}
```
- ลบ `home.path` 4 ชั้นเดิม · ลบ targets 2567/2568 · `autoYear: true` = §7.3
- เป้าที่ไม่มี (`targets[ind][year]` ว่างหรือ `value: null`) → เว็บแสดง "เป้าหมาย: ยังไม่กำหนด" สีกลาง ไม่มีเส้นเป้า ไม่จัดอันดับสี

### 4.2 ระดับ/ขอบเขตที่ build (ทั้ง 2 ตัวชี้วัด ปีใน `years`)

| level | scope | rows | ไฟล์ | จำนวน |
|---|---|---|---|---|
| country | TH | 13 เขต (เขต 13 = null) | `<ind>_<ปี>_country_TH.json` | 1 |
| region | 4 | 8 จังหวัด | `<ind>_<ปี>_region_4.json` | 1 |
| province | 12,13,14,15,16,17,19,26 | อำเภอของจังหวัด | `<ind>_<ปี>_province_<prov>.json` | 8 |
| district | ทุกอำเภอ (70) | ตำบลของอำเภอ (**ตามที่ตั้งหน่วย** §4.3) | `<ind>_<ปี>_district_<dist>.json` | 70 |

- DSPM: country/region จาก `provinces.json` (เหมือน Phase 1) · province/district จาก `data/cache/dspm/<ปี>/<prov>.json` ของ 8 จังหวัด → **แก้ `.gitignore` ให้ commit 8 ไฟล์นี้** (`!data/cache/dspm/*/{12,13,14,15,16,17,19,26}.json`) เฉพาะปีใน `years` · cache ต้องเพิ่มคอลัมน์ `hospcode` (rowFormat `[areacode6, hospcode, monthly, <fields>]`) เพื่อคำนวณตำบลจากทะเบียน → **rebuild cache 8 จังหวัดจาก raw ที่มีในเครื่อง** ไม่ต้องยิง API (raw 2569 ครบ 77 จังหวัด)
- Coverage: จาก `all.json` เดิม · province rows = `areacode[:4]` · district rows = ตำบลของ hospcode (§4.3) · เพิ่ม `"district"` ใน `META.levels`
- `tree` ใน `index.json`: region 4 → 8 provinces → districts → subdistricts (ครบทั้งต้นไม้ ≈ 800 node, เว็บใช้ตัดสินว่ากดต่อได้ไหม) · แต่ละ node district มี `"inferredUnits": n` (จำนวนหน่วย fallback §4.3) เว็บใช้แสดงป้าย/footnote
- ไม่ build `*_monthly_*` อีก · ลบไฟล์ 2567/2568 ใน `site/data/angthong/`
- ทุกไฟล์ dataset มี `asOf` จาก `date_com` สูงสุดของแถวที่ใช้ และ `source: "api"`

### 4.3 กฎตำบล = ที่ตั้งหน่วยบริการ (แทนกฎ Phase 1)
1. `scripts/build_lookup.py units` → ยิง GIS service ทีละ hoscode สำหรับทุก `hospcode` ที่พบใน raw DSPM + Coverage ของ 8 จังหวัด (ปีใน `years`) → เขียน `data/lookup/units.json` (commit):
   `{"schema":1,"source":"<url template>","fetchedAt":..., "units":{"10768":{"name":"โรงพยาบาลท่าเรือ","tambon":"140201","hostype":"07","dep":"21002"}, ...}, "missing":{"41425":{"maxTargetArea":"120103","target":..,"areas":{...}}, ...}}`
   - **incremental**: hospcode ที่มีอยู่แล้วไม่ยิงซ้ำ · retry 3 ครั้ง backoff 5/15/45 วิ · ครั้งแรก 982 รหัส ≈ 8 นาที · **ไฟล์นี้ถูกสร้างไว้แล้วในรอบ plan (2026-09-30)** ถ้ามีอยู่ให้ใช้เลย แค่เติมรหัสใหม่
2. ตำบลของแถว = `units[hospcode].tambon` · ถ้าไม่มีในทะเบียน → fallback = ตำบลที่หน่วยนั้นมีเป้า (DSPM `target`; Coverage ใช้ `c_1`) มากสุดในปีนั้น (กฎ Phase 1) และนับหน่วยนั้นเป็น `inferredUnits` ของอำเภอ
3. ตำบลตามทะเบียนต้องอยู่ในอำเภอเดียวกับ `areacode[:4]` ของแถวส่วนใหญ่ของหน่วย ถ้าไม่ (หน่วยตั้งข้ามอำเภอ) → ยึด**อำเภอที่ตั้งตามทะเบียน** และ log warning ให้ Fable ดู · **verify hard error ถ้ายอดรวมตำบลทั้งอำเภอ ≠ ยอดอำเภอที่ได้จาก `areacode[:4]`** ยกเว้นเคสข้ามอำเภอที่ log ไว้ (รายงานเป็น warning พร้อมตัวเลข)
4. Excel 2569 ที่มี (เมืองอ่างทอง 14 ตำบล · หนองแค 18 · ท่าเรือ 10) ต้องตรง **100%** ด้วยกฎใหม่ — ถ้าเมืองอ่างทองไม่ตรงด้วยกฎใหม่ (Phase 1 ตรงด้วยกฎเก่า) ให้**หยุดรายงาน** ไม่เลือกกฎเอง

### 4.4 อำเภอที่มีหน่วยนอกทะเบียน (fallback) — ให้ Save export Excel HDC รายตำบล 2569 มาเทียบเพิ่ม
ทะเบียนดึงแล้ว 2026-09-30: **982 hospcode → พบ 882 · ไม่พบ 100 (10%)** ใน 23 อำเภอ · รหัสที่ไม่พบ: `4xxxx` 44 (อปท./คลินิก) · `2xxxx` 27 และ `1xxxx` 19 (สถานพยาบาลเอกชน/นอก สป.สธ.) · `7xxxx`/`3xxxx`/`9xxxx` 10 · **กฎใหม่ + fallback ตรง Excel 100% แล้วที่ เมืองอ่างทอง (14 ตำบล, fallback 2 หน่วย) · หนองแค (18) · ท่าเรือ (10)**

| จังหวัด | อำเภอ | รหัส | หน่วยนอกทะเบียน | เป้า DSPM 2569 ของหน่วยเหล่านี้ | รหัสหน่วย |
|---|---|---|---|---|---|
| นนทบุรี | เมืองนนทบุรี | 1201 | 21 | 1,151 | 14414, 15237, 15238, 15240, 15244, 21428, 21429, 23821, 23836, 23933, 28866, 40879, 41303, 41433, 41434, 41438, 41609, 41613, 41615, 41624, 41625 |
| นนทบุรี | บางกรวย | 1202 | 5 | 409 | 23763, 41358, 41435, 41610, 41612 |
| นนทบุรี | บางใหญ่ | 1203 | 7 | 958 | 24053, 40753, 41305, 41427, 41524, 41614, 41675 |
| นนทบุรี | บางบัวทอง | 1204 | 6 | 828 | 11237, 22868, 23917, 41626, 41627, 41833 |
| นนทบุรี | ปากเกร็ด | 1206 | 8 | 403 | 11168, 13815, 22971, 23218, 23764, 41304, 41611, 41804 |
| ปทุมธานี | เมืองปทุมธานี | 1301 | 2 | 695 | 14342, 41319 |
| ปทุมธานี | คลองหลวง | 1302 | 11 | 1,449 | 24041, 24042, 24707, 25052, 25053, 31157, 41330, 41332, 41709, 41798, 42041 |
| ปทุมธานี | ธัญบุรี | 1303 | 8 | 562 | 14344, 14345, 15228, 22735, 22841, 22864, 41604, 41605 |
| ปทุมธานี | ลำลูกกา | 1306 | 13 | 1,720 | 11802, 14346, 14809, 23567, 24924, 28013, 40855, 41306, 41390, 41425, 41439, 42239, 42952 |
| ปทุมธานี | สามโคก | 1307 | 1 | 1 | 41428 |
| ปทุมธานี | **ไม่มีในทะเบียนอำเภอ** (areacode `1310`) | 1310 | 1 | 30 | 33160 |
| พระนครศรีอยุธยา | บางปะอิน | 1406 | 1 | 112 | 42288 |
| พระนครศรีอยุธยา | เสนา | 1412 | 1 | 44 | 77696 |
| อ่างทอง | เมืองอ่างทอง | 1501 | 2 | 95 | 14416, 14O3F |
| ลพบุรี | เมืองลพบุรี | 1601 | 3 | 163 | 22425, 22761, 77734 |
| ลพบุรี | ชัยบาดาล | 1604 | 1 | 4 | 40909 |
| ลพบุรี | บ้านหมี่ | 1606 | 1 | 55 | 77776 |
| สิงห์บุรี | เมืองสิงห์บุรี | 1701 | 1 | 118 | 77431 |
| สระบุรี | เมืองสระบุรี | 1901 | 3 | 281 | 11485, 23813, 77604 |
| สระบุรี | วิหารแดง | 1904 | 1 | 174 | 99730 |
| สระบุรี | ดอนพุด | 1907 | 1 | 40 | 77731 |
| สระบุรี | พระพุทธบาท | 1909 | 1 | 2 | 13623 |
| นครนายก | องครักษ์ | 2604 | 1 | 2 | 99842 |

- **ลำดับที่ควร export Excel HDC รายตำบล 2569 มาเทียบ (เป้ากระทบมากสุด)**: ลำลูกกา (1,720) · คลองหลวง (1,449) · เมืองนนทบุรี (1,151) · บางใหญ่ (958) · บางบัวทอง (828) · เมืองปทุมธานี (695) · ธัญบุรี (562) · บางกรวย (409) · ปากเกร็ด (403) — 9 อำเภอนี้ครอบคลุม 84% ของเป้าที่ใช้ fallback · ที่เหลือหน่วยเดียว/เป้าน้อย ป้ายอย่างเดียวพอ
- วางไฟล์ใน `data/excel_reference/dspm/2569/` ชื่อไฟล์อิสระ · `verify` จับ scope เองจากชื่อตำบล (§4.5) · ถ้าไฟล์ไหนตรง 100% ป้าย [INFERRED] ของอำเภอนั้นยังคงอยู่ (เพราะหน่วยยังไม่มีในทะเบียน) แต่ spec ถือว่ากฎ fallback ผ่านการยืนยัน → เปลี่ยนข้อความป้ายเป็น "ตรวจกับ HDC แล้ว" ได้ผ่าน `verifiedDistricts` ใน `index.json`
- **ความผิดปกติของข้อมูลที่ต้องรองรับ**: hospcode `14O3F` (มีตัวอักษร O) ใน เมืองอ่างทอง → เก็บเป็น string ตามที่ API ให้ ไม่แปลงเป็นเลข · areacode อำเภอ `1310` (ปทุมธานี) ไม่มีใน DOPA lookup → แถวของอำเภอที่ไม่รู้จักรวมเป็น pseudo-row **"ไม่ระบุพื้นที่ (รหัส 1310)"** ท้ายตาราง/heatmap ของจังหวัด ไม่นับในอันดับ/กราฟ แต่**นับในยอดรวมจังหวัด** (ให้ province total = แถวจังหวัดใน region view) · verify จำนวนแถว province = อำเภอใน lookup + pseudo-row (ถ้ามี) [INFERRED]

### 4.5 Excel oracle และ verify
- ย้ายโครง `data/excel_reference/angthong/<ind>/<ปี>/` → `data/excel_reference/<ind>/<ปี>/` (ไฟล์เดิม 22 ไฟล์ + 4 ไฟล์ใหม่จาก root) · ชื่อไฟล์อิสระ
- `verify` ระบุ **ระดับ**จาก header A1 (`เขตสุขภาพ`/`จังหวัด`/`อำเภอ`/`ตำบล`) และระบุ **scope** เองโดยจับคู่ชุดชื่อในคอลัมน์ A กับ lookup (ชุดอำเภอของจังหวัดไหน / ชุดตำบลของอำเภอไหน ต้องตรงกันครบและไม่กำกวม ไม่งั้น hard error "ระบุ scope ไม่ได้") · ไม่ต้องใช้ `home.path`
- เกณฑ์: อ่างทอง/สระบุรี/อยุธยา ระดับอำเภอ+ตำบล ตรง **100%** (hard) · DSPM country/region ต่างจาก HDC ได้ (warning เหมือน Phase 1) · Coverage ทุกระดับที่มี Excel ตรง 100%
- verify ข้ามระดับ: ผลรวม 8 จังหวัด = แถวเขต 4 ใน country view · ผลรวมอำเภอ = จังหวัด · ผลรวมตำบล = อำเภอ (§4.3 ข้อ 3) · จำนวนแถว: country 13, region 8, province = จำนวนอำเภอใน lookup, district = จำนวนตำบลที่มีหน่วย (ตำบลที่ไม่มีหน่วยใดตั้งอยู่จะไม่มีแถว — ตรงกับ HDC ซึ่งแสดงเฉพาะตำบลที่มีหน่วย เช่น ท่าเรือ 10 ตำบล)

### 4.6 Metadata ตัวชี้วัด (`scripts/indicators/*.py`)
DSPM: `name_th` = "ร้อยละของเด็กอายุ 0-5 ปี มีพัฒนาการสมวัย 5 ช่วงอายุ (DSPM)" · `short` = "สมวัย" · `levels` = 4 ระดับเดิม · `monthly: False` · การ์ดรองคงเดิม (คัดกรอง / สงสัยล่าช้า / ติดตามได้)

Coverage: `name_th` = "ร้อยละของเด็กปฐมวัยที่มีพัฒนาการล่าช้าเข้าถึงบริการพัฒนาการและสุขภาพจิตที่ได้มาตรฐาน (Coverage)" · `short` = "เข้าถึงบริการ" · `levels` = `["country","region","province","district"]` · **`headline` = `{"metric":"pct_reached_cum","num":"reached_cum","den":"expected","sub":{"metric":"pct_reached_fy","num":"reached_fy","label":"ปีงบนี้"}}`** · `cards` = TEDA4I (4)/(3) · ICD9CM (5)/(3) [เพิ่ม `pct_icd9` ใน derive/validate] · ICD-10 (6)/(3) · `heatmap` = 4 คอลัมน์ตาม Q16 (เพิ่ม key `heatmap` ใน META ให้ web ไม่ต้องเดา) · `chart: {"style":"fill","fillNum":"reached_cum","fillDen":"expected","fillLabel":"เข้าถึงบริการสะสม","baseLabel":"คาดประมาณเด็กพัฒนาการล่าช้า"}` (§5.5)

## 5. หน้าเว็บ (Opus — โหลด skill `dataviz` + `artifact-design` ก่อนเขียนกราฟ)

### 5.1 URL / routing
- `site/index.html` = แอป (ย้ายจาก `site/angthong/index.html`) · `_redirects`: `/angthong/*  /  301` (hash ติดมาเอง)
- hash `#/<indicator>/<year>/<level>/<code>` · default `#/dspm/2569/region/4` (ปี = `currentYear`) · country level ไม่มี route (ถ้าเจอ → redirect ไป region/4)
- ไฟล์: `site/assets/{styles.css, app.js, modules/*}` ต่อยอดของเดิม · ลบ `monthly.js`, `trend.js`, `weakness.js`, `shortcuts.js` · เพิ่ม `footer.js`, `hit.js`, `configOverride.js` (2b)

### 5.2 Header (sticky บนมือถือแบบย่อ)
โลโก้เขต 4 · **ระบบติดตามตัวชี้วัดเข็มมุ่งพัฒนาการเด็ก เขตสุขภาพที่ 4** · บรรทัดเล็ก: โลโก้อ่างทอง 24px + "จัดทำโดย โรงพยาบาลอ่างทอง" · แท็บ **สมวัย | เข้าถึงบริการ** · ปุ่มปี (ซ่อนถ้าปีเดียว) · ปุ่ม light/dark · ใต้แท็บ: ชื่อเต็มตัวชี้วัด (ตัวเล็ก) + "ข้อมูล ณ <asOf> · MOPH Open Data API"
มือถือ: เมื่อเลื่อนลง header ย่อเหลือแท็บ 2 อัน + breadcrumb 1 บรรทัด

### 5.3 Breadcrumb
`เขตสุขภาพที่ 4 › สระบุรี › หนองแค` กดย้อนได้ · ไม่มี "ประเทศ"

### 5.4 เนื้อหาต่อชั้น

**หน้าแรก (region 4)**
1. Headline card: % ใหญ่ + สี + `n / d` + เป้า + "อันดับ x/12 เขต" (ไม่นับเขต 13) · Coverage: บรรทัดย่อย "ปีงบนี้ n คน (x%)"
2. การ์ดรอง 3 ใบจาก `cards`
3. **กราฟแนวนอน 13 เขตสุขภาพ** เรียงมาก→น้อย · เขต 4 ไฮไลต์กรอบ · เขต 13 = "ไม่มีข้อมูล" ท้ายสุด · label ทุกแท่ง · **กดไม่ได้**
4. **กราฟแนวนอน 8 จังหวัด** เรียงมาก→น้อย · **กดแท่ง/ชื่อ = เจาะ** · label ทุกแท่ง
5. **Heatmap 8 จังหวัด × คอลัมน์** (DSPM: รวม, 9, 18, 30, 42, 60 เดือน · Coverage: 4 คอลัมน์ Q16) · % สี + `n/d` เล็ก · ชื่อจังหวัดกดเจาะได้ · ปุ่ม "เรียง: รหัส | %"
6. ตารางเต็ม (ยุบ) + CSV

**หน้ารายจังหวัด / รายอำเภอ** (โครงเดียวกัน แถว = อำเภอ / ตำบล)
1. Headline **แถวเล็ก** 1 บรรทัด: ชื่อพื้นที่ · % สี · `n / d` · เป้า · "อันดับ x/8 ในเขต 4" หรือ "x/13 ในสระบุรี" · Coverage มี "ปีงบนี้ …"
2. **Heatmap** (สิ่งแรกที่เห็นถัดจาก headline) · ระดับตำบล: หัวตารางมีป้าย `[INFERRED] หน่วย n แห่งใช้การอนุมานที่ตั้ง` เฉพาะเมื่อ `inferredUnits > 0` · Coverage ตำบล: ป้าย `[INFERRED] ไม่มีรายงาน HDC ระดับตำบลให้ตรวจสอบ` เสมอ
3. กราฟแนวนอนพื้นที่ลูก · กดเจาะ (อำเภอ→ตำบล) · ระดับตำบลกดไม่ได้
4. ตารางเต็ม (ยุบ) + CSV
- แท็บกลุ่มอายุ DSPM (9/18/30/42/60) คงไว้ทุกชั้น → การ์ด + กราฟ ใช้กลุ่มนั้น
- ชั้น/ตัวชี้วัดที่ไม่มีข้อมูล → กล่อง "ไม่มีข้อมูลระดับนี้ในปี …"

### 5.5 กราฟ (Chart.js 4 + annotation, แนวนอนทั้งหมด)
- ความสูงแท่ง 28–36px × จำนวนแถว (ไม่บีบ) · แกน X 0–100% · เส้นเป้าแนวตั้ง (ถ้ามีเป้า) มีป้าย "เป้า 88%"
- **DSPM**: แท่งสี ok/warn/bad/small_n · label ปลายแท่ง `88.1% (4,748/5,681)` (plugin datalabels หรือวาดเอง) · n<20 ป้าย "n<20" สีจาง
- **Coverage (`chart.style = "fill"`)**: ทุกแท่งยาวเต็ม 100% สี**แดง**จาง = คาดประมาณ (3) · ซ้อนทับสี**เขียว** ยาว = (8) สะสม % · เส้นตัดแนวตั้ง 30% · label `12.3% (54/438)` · legend: "แดง = เด็กพัฒนาการล่าช้าที่คาดประมาณจากอัตราความชุก · เขียว = เข้าถึงบริการสะสม"
- มือถือ (≤ 600px): ชื่อพื้นที่ + label อยู่บรรทัดเหนือแท่ง (`88.1% · 4,748/5,681`) แท่งกว้างเต็มจอ · ปิด animation
- ไม่ใช้สีอย่างเดียว: ไอคอน ✓ / ! / ✗ ในตาราง/heatmap คงเดิม

### 5.6 Footer
โลโก้อ่างทอง + "จัดทำโดย โรงพยาบาลอ่างทอง" · "ผู้ใช้งาน N คน · วันนี้ M · ไม่เก็บข้อมูลส่วนบุคคล" (จาก `/api/hit` §6) · "ข้อมูล ณ …" · ลิงก์ GitHub repo · (2b) ลิงก์ `/admin/` เล็ก

### 5.7 Visual / responsive
ตาม Phase 1 §7 (Sarabun, tabular-nums, CSS variables, dark, max-width 1400) · เพิ่ม: heatmap บนมือถือ scroll ในกรอบ คอลัมน์ชื่อ `position: sticky; left: 0` · แท็บ/breadcrumb sticky · ทดสอบ 1440 / 768 / 375 ไม่มี horizontal scroll ของหน้า

## 6. ยอดผู้ใช้ — Pages Function `/api/hit` + D1 (Phase 2)

- `functions/api/hit.js` (Pages Functions) · `POST /api/hit` body `{route:"dspm/province/19", newDevice:true|false}` · Function อ่าน `request.cf.region`, `request.cf.city` (ไม่อ่าน/ไม่เก็บ IP, UA) · เขียน D1:
  ```sql
  CREATE TABLE hits(day TEXT, route TEXT, region TEXT, city TEXT, views INTEGER, devices INTEGER, PRIMARY KEY(day, route, region, city));
  -- UPSERT views+1, devices+(newDevice?1:0)
  ```
  ตอบ `{total_devices, today_devices}` (SUM devices ทั้งตาราง / วันนี้ ICT) · cache ผลรวมใน memory ของ Function 60 วิ ลด reads
- client `hit.js`: ยิง 1 ครั้งต่อการเปลี่ยน route (debounce 1 วิ) · `newDevice` = ยังไม่มี `localStorage.kpiSeen == <วันนี้ ICT>` แล้วตั้งค่า · ถ้า Function ล้ม footer แสดง "–" ไม่ error
- `GET /api/hit?summary=1` (สาธารณะ) ให้ยอดรวม+วันนี้เท่านั้น · รายละเอียดรายหน้า/จังหวัด เปิดใน 2b ผ่าน `/api/admin/stats`
- **Save ทำใน Cloudflare dashboard (login ใน browser pane แล้ว Claude กดต่อ)**: Workers & Pages → D1 → Create `kpi-health-hits` → Pages project `kpi-health` → Settings → Bindings → D1 `DB` = `kpi-health-hits` · (2b เพิ่ม KV `CONFIG`) · schema สร้างโดย `wrangler d1 execute` หรือ Function สร้างเองครั้งแรก (`CREATE TABLE IF NOT EXISTS`) — เลือกอย่างหลังจะได้ไม่ต้องติดตั้ง wrangler
- local dev: `wrangler pages dev site` (ถ้าติดตั้งได้) ไม่งั้นทดสอบบน preview deployment ของ Cloudflare หลัง push branch

## 7. GitHub Actions — อัปเดตอัตโนมัติ (Phase 2)

### 7.1 `.github/workflows/update.yml`
- `on: schedule: cron "0 0 * * *"` (= 07:00 ICT ทุกวัน) + `workflow_dispatch` · `permissions: contents: write, issues: write` · `concurrency: update` (ไม่รันซ้อน) · timeout 40 นาที
- ขั้น: checkout → Python 3.13 + `pip install -r scripts/requirements.txt` → `python3 scripts/kpi.py update --site angthong --refresh --year <ทุกปีใน years>` (DSPM ดึงเฉพาะ 8 จังหวัดเขต 4 + `provinces.json` ระดับประเทศ **ต้องคิดใหม่**: ระดับประเทศ 77 จังหวัด ≈ 45 นาที เกิน → ให้ `provinces.json` (country/region) **อัปเดตรายสัปดาห์** เฉพาะรอบวันจันทร์ (`if: github.event.schedule` + วันในสัปดาห์) ส่วน 8 จังหวัด + Coverage รายวัน · จังหวัดนอกเขต 4 ในรอบสัปดาห์ยิง 3 workers ไม่ได้ (429) → 1 worker, ตั้ง timeout 90 นาทีในรอบวันจันทร์)
- ถ้า `update` exit 0 และมี diff ใน `data/cache/`, `site/data/`, `sites/angthong.json` → `git commit -m "data: auto-update <วันที่>"` + push main → Cloudflare deploy
- ถ้า exit ≠ 0 → ไม่ commit · job fail (GitHub ส่งอีเมล) · เปิด/อัปเดต Issue label `pipeline` หัวข้อ "อัปเดตข้อมูลล้มเหลว <วันที่>" แนบ 50 บรรทัดท้าย log (ใช้ `gh issue create` ด้วย `GITHUB_TOKEN`; ถ้ามี Issue เปิดอยู่แล้วให้ comment แทน)

### 7.2 สิ่งที่ `kpi.py` ต้องรองรับเพิ่ม
- `--refresh` ที่ยิงเฉพาะจังหวัดใน `drill.provinces` (ไม่ใช่ 77) · flag `--national` สำหรับรอบสัปดาห์ (77 จังหวัด → `provinces.json`)
- raw cache ใน Actions ไม่มี (ไม่ commit) → ทุกอย่างสร้างจาก API ในรอบนั้น · cache 8 จังหวัดที่ commit จึงเป็น snapshot ล่าสุด
- `build_lookup.py units` incremental รันทุกรอบ (hospcode ใหม่ ≈ 0) แล้ว commit `units.json` ถ้าเปลี่ยน

### 7.3 ปีใหม่อัตโนมัติ (`autoYear: true`)
- ก่อน fetch: ยิง Coverage `year=<max(years)+1>` (0.2 วิ) และ DSPM จังหวัด 15 ปีเดียวกัน · ถ้าอย่างใดอย่างหนึ่งได้ `total > 0` → เพิ่มปีใน `years`, `currentYear` = ปีนั้น, `targets[ind][ปี]` ไม่สร้าง (เว็บแสดง "ยังไม่กำหนด") → เปิด Issue "พบข้อมูลปีงบ <ปี> — กรุณาใส่เป้าหมาย" (ครั้งเดียว) · เว็บโชว์ปุ่มปี 2569 | **2570** ทันที
- เป้าใส่ได้ 2 ทาง: แก้ `sites/angthong.json` แล้ว push หรือหน้า admin (2b) → KV override

## 8. Phase 2b — Admin (session ถัดไป หลัง Phase 2 ขึ้นเว็บแล้ว)

### 8.1 Auth: Google Sign-In
- Save สร้าง **OAuth 2.0 Client ID (Web)** ใน Google Cloud Console (ฟรี) → Authorized JavaScript origins = `https://kpi-health.pages.dev` (+ preview) → ใส่ Client ID ใน Pages env `GOOGLE_CLIENT_ID` (ไม่ใช่ความลับ ใส่ใน `index.html` ได้)
- หน้า `/admin/` โหลด Google Identity Services → ได้ ID token → ทุกคำขอ `/api/admin/*` ส่ง `Authorization: Bearer <id_token>` → Function ตรวจ token กับ `https://www.googleapis.com/oauth2/v3/tokeninfo` (หรือ verify JWT ด้วย JWKS ของ Google) เช็ค `aud == GOOGLE_CLIENT_ID`, `email_verified`, และ `email ∈ allowlist (KV key admins)` → ไม่ผ่าน 403
- **allowlist ตั้งต้น = 2 อีเมลของ Save** ใส่ครั้งแรกด้วย `wrangler kv key put` หรือ KV dashboard (Save login browser pane) · **ห้ามเขียนอีเมลใน repo** · อีเมลบันทึกไว้ใน memory ของ Claude (project) แล้ว

### 8.2 Config override
- KV namespace `CONFIG` · key `site` = JSON `{name, org, footerNote, indicators:{dspm:{name_th,short,cards:[label...]},coverage:{...}}, targets:{...}, currentYear}` (เฉพาะ field ที่แก้ ค่าอื่นตกไปใช้ `index.json`)
- `GET /api/config` (สาธารณะ, cache 60 วิ) → เว็บ `configOverride.js` merge ทับ `index.json` ก่อน render · Function ล้ม → ใช้ค่า repo
- `PUT /api/admin/config` (auth) · `DELETE /api/admin/config` = คืนค่าเริ่มต้น · `GET/PUT /api/admin/admins` จัดการอีเมล (ห้ามลบอีเมลตัวเอง, อย่างน้อย 1 คน) · `GET /api/admin/stats?from&to` → รายวัน / รายหน้า (แปลง route → ชื่อพื้นที่จาก lookup) / จังหวัด-เมืองผู้ชม · `GET /api/admin/spec.md` → รวม `web_spec_phase2.md` (ล่าสุด) + README §1,3 + config ปัจจุบัน + วันที่ เป็นไฟล์ดาวน์โหลด · `GET /api/admin/pipeline` → สถานะ workflow ล่าสุดจาก GitHub API สาธารณะ (`/repos/parinyapaw-del/kpi-health/actions/runs?per_page=1`)

### 8.3 หน้า `/admin/` (`site/admin/index.html` + `admin.js`)
ปุ่ม Sign in with Google → 5 ส่วนตาม Q30: ① ฟอร์มข้อความ/เป้า/ปี พร้อม preview สด (iframe หน้าแรกอ่าน config draft ผ่าน `postMessage`) → บันทึก ② สถิติ: การ์ดยอดรวม/วันนี้/7 วัน + ตาราง top หน้า + ตารางจังหวัดผู้ชม + กราฟรายวัน (Chart.js) + ตัวเลือกช่วงวัน ③ อีเมล admin ④ ปุ่ม "ดาวน์โหลด spec.md" ⑤ ปุ่ม "คืนค่าเริ่มต้น" (confirm) · แสดงสถานะ pipeline ล่าสุด · ภาษาไทย · มือถือใช้ได้

### 8.4 สิ่งที่ Save ทำใน 2b (Claude กดให้ใน browser pane หลัง login)
Cloudflare: สร้าง KV `kpi-health-config` → bind `CONFIG` ใน Pages · เพิ่ม env `GOOGLE_CLIENT_ID` · ใส่ key `admins` = `["<email1>","<email2>"]` · Google Cloud Console: สร้าง OAuth Client ID

## 9. โครง repo หลัง Phase 2 (เฉพาะที่เปลี่ยน)
```
kpi-health/
├── web_spec.md (Phase 1, reference) · web_spec_phase2.md (ไฟล์นี้) · README.md (เขียนใหม่ตาม Phase 2)
├── .github/workflows/update.yml
├── functions/api/hit.js · functions/api/config.js (2b) · functions/api/admin/*.js (2b) · functions/_lib/{d1,auth}.js
├── sites/angthong.json (§4.1)
├── data/excel_reference/<ind>/<ปี>/*.xlsx        # ย้ายจาก angthong/ + 4 ไฟล์ใหม่
├── data/lookup/areas.json · units.json (ใหม่) · SOURCE.md (เพิ่ม GIS service)
├── data/cache/dspm/<ปี>/{12,13,14,15,16,17,19,26,provinces}.json · coverage/<ปี>/all.json
├── scripts/  (kpi.py: --national, autoYear · build_lookup.py units · indicators/*.py META ใหม่ · verify.py scope detection)
└── site/
    ├── index.html (แอป) · _redirects · admin/ (2b)
    ├── assets/ logo-r4.png · logo-angthong.png · styles.css · app.js · modules/…
    └── data/angthong/ index.json + <ind>_2569_{country_TH,region_4,province_<8>,district_<70>}.json  (≈ 160 ไฟล์)
```

## 10. แผน execute

### Phase 2 (1 session)
| ขั้น | ผู้ทำ | งาน | เกณฑ์ผ่าน |
|---|---|---|---|
| 0 | Save | เปิด session สั่ง "execute web_spec_phase2.md" | – |
| 1 | Fable | อ่าน spec ทั้งไฟล์ + `web_spec.md` + README · ตรวจ §3 กับของจริง (ไฟล์ 4 Excel ที่ root, `units.json`, cache 8 จังหวัด) | ตรงทุกข้อ ไม่งั้นหยุด |
| 2 | Sonnet | โลโก้ (`logo-r4.png`) · config §4.1 · `.gitignore` · ย้าย Excel §4.5 · `build_lookup.py units` (ใช้ `units.json` ที่มี เติมที่ขาด) · rebuild cache 8 จังหวัด (มี hospcode) · กฎตำบล §4.3 · Coverage district · ตัด monthly/ปีเก่า · META §4.6 · verify scope detection · รัน `kpi.py update` (offline จาก raw/cache) | verify 0 hard error · Excel 26 ไฟล์ตรง (country/region DSPM = warning) · เมืองอ่างทอง/หนองแค/ท่าเรือ ตำบลตรง 100% · ตารางอำเภอ §4.4 ตรงกับ `tree.inferredUnits` |
| 3 | Fable | ตรวจมือ 6 จุด: เขต 4 DSPM 2569 headline = Excel เขต 4 (tol ตาม warning) · สระบุรี เมืองสระบุรี 1,797 · ท่าเรือ ตำบลท่าเรือ 122 / จำปา 41 · หนองแค กุ่มหัก 31 · Coverage อ่างทอง เมือง 48/438 · Coverage เขต 4 region view = country view แถวเขต 4 | ตรงทุกจุด |
| 4 | Opus | เว็บ §5 ทั้งหมด (โหลด `dataviz`, `artifact-design`) · `functions/api/hit.js` §6 · `hit.js` | ครบทุก component · เจาะ เขต→จังหวัด→อำเภอ→ตำบล ทั้ง 2 ตัวชี้วัด · hash เปิดตรงหน้า · `/angthong/` redirect |
| 5 | Save + Fable | Save login Cloudflare ใน browser pane → Fable กดสร้าง D1 + bind `DB` | binding ปรากฏใน Settings |
| 6 | Sonnet | `.github/workflows/update.yml` §7 + `kpi.py --national` + autoYear §7.3 · ทดสอบด้วย `workflow_dispatch` หลัง push | run เขียว · Issue เปิดเมื่อจำลอง fail (ทดสอบด้วย flag `--fail-test` แล้วถอดออก) |
| 7 | Fable | browser 1440 / 768 / 375 light+dark: ไม่มี console error · ไม่มี horizontal scroll · label บนแท่งทุกแท่ง · Coverage แดง/เขียว/เส้น 30 · heatmap ป้าย [INFERRED] ขึ้นเฉพาะอำเภอใน §4.4 · footer ยอดผู้ใช้เพิ่มเมื่อ reload ใน browser ใหม่ | ผ่านทุกข้อ |
| 8 | Fable | README ใหม่ · commit · push · ตรวจ URL จริง · อัปเดต memory | เว็บใหม่ขึ้นที่ `kpi-health.pages.dev/` |

### Phase 2b (session ถัดไป) — สั่ง "execute web_spec_phase2.md phase 2b"
Opus: §8.1–8.3 · Save+Fable: §8.4 · Fable ตรวจ: login ด้วยอีเมลนอก allowlist ได้ 403 · แก้ชื่อเว็บแล้วหน้าแรกเปลี่ยนภายใน 60 วิ · คืนค่าเริ่มต้นกลับเป็นค่า repo · ดาวน์โหลด spec.md เปิดอ่านได้ · สถิติแสดงหน้าที่เพิ่งเปิด

## 11. สมมติฐานที่ยังไม่ยืนยัน
- [CONFIDENT] HDC จัดกลุ่มระดับตำบลตาม**ที่ตั้งหน่วยในทะเบียน** — เทียบครบแล้ว 3 อำเภอ 42 ตำบล ตรง 100% (เป้า) · verify ขั้น 2 ต้องตรงทุก key ทุกกลุ่มอายุ ไม่ใช่แค่เป้า · ถ้าไม่ตรง → หยุดรายงาน
- [INFERRED] fallback "เป้ามากสุด" สำหรับ 100 หน่วยนอกทะเบียน (10%) ถูกต้อง — ยืนยันแล้วเฉพาะเมืองอ่างทอง (2 หน่วย) · 23 อำเภอใน §4.4 รอ Excel จาก Save · หน่วยเอกชน `1xxxx/2xxxx` ที่ส่งเด็กหลายตำบลเป็นจุดเสี่ยงสุด (เหมือนเคส รพ.ท่าเรือ)
- [UNCERTAIN] Coverage ระดับตำบลไม่มีรายงาน HDC เทียบ → ป้ายบนเว็บ
- [UNCERTAIN] `request.cf.region/city` ของ Cloudflare ระบุจังหวัดไทยได้ละเอียดแค่ไหน (อาจได้เป็นภาค/เมืองใหญ่) → เก็บตามที่ได้ ไม่แก้
- [UNCERTAIN] GIS service มี rate limit ไหม (982 ครั้งใน 8 นาทีผ่านตอน plan) → retry/backoff ไว้แล้ว
- [UNCERTAIN] เป้าหมาย 2570 ยังไม่ประกาศ → "ยังไม่กำหนด" จนกว่า Save ใส่
