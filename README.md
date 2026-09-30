# kpi-health — ระบบติดตามตัวชี้วัดเข็มมุ่งพัฒนาการเด็ก เขตสุขภาพที่ 4

Dashboard ตัวชี้วัดพัฒนาการเด็กปฐมวัยสำหรับผู้ตรวจราชการ เปิด link แล้วดูได้ทันที ไม่ต้อง login
เจาะได้ 4 ชั้น: **เขตสุขภาพที่ 4 → 8 จังหวัด → ทุกอำเภอ (70) → ทุกตำบล (703 ตำบลที่มีหน่วยบริการ)**

- URL: `https://kpi-health.pages.dev/` (link เก่า `/angthong/…` redirect มาที่นี่)
- จัดทำโดย: โรงพยาบาลอ่างทอง
- Spec ฉบับล็อก: [`web_spec_phase2.md`](web_spec_phase2.md) (v2.0, 2026-09-30) · Phase 1: [`web_spec.md`](web_spec.md)
- ตัวชี้วัด: **สมวัย** — ร้อยละของเด็กอายุ 0-5 ปี มีพัฒนาการสมวัย 5 ช่วงอายุ (DSPM) และ **เข้าถึงบริการ** — ร้อยละของเด็กปฐมวัยที่มีพัฒนาการล่าช้าเข้าถึงบริการพัฒนาการและสุขภาพจิตที่ได้มาตรฐาน (Coverage) · ปีงบ 2569 (ปีใหม่เพิ่มเองเมื่อ API มีข้อมูล)
- แหล่งข้อมูล: **MOPH Open Data API ทุกระดับ** · Excel HDC export ใน `data/excel_reference/` เป็น oracle ให้ `verify` (ระดับอำเภอ/ตำบลต้องตรง 100% · DSPM ประเทศ/เขต ต่างจาก HDC ได้ 0.1–3% → warning, ดู `docs/API_NOTES.md` §3)
- Static site (vanilla HTML/CSS/JS + Chart.js จาก CDN) ไม่มี build step + Pages Function `/api/hit` (นับผู้ใช้, D1) · deploy ด้วย Cloudflare Pages จาก `site/`

## 1. อัปเดตข้อมูล

### อัตโนมัติ (GitHub Actions — [`.github/workflows/update.yml`](.github/workflows/update.yml))
- **ทุกวัน 07:00 ICT**: DSPM 8 จังหวัดเขต 4 + Coverage ทั้งประเทศ → build → verify → ถ้าผ่านและมีข้อมูลใหม่ commit `data: auto-update <วันที่>` → Cloudflare deploy เอง (≈ 10 นาที)
- **ทุกวันจันทร์**: เพิ่ม DSPM ทั้ง 77 จังหวัด (`--national`, ≈ 45–60 นาที) สำหรับกราฟ 13 เขต / ยอดเขต 4
- **ปีงบใหม่**: ก่อนดึงจะยิงถาม API ปี `max(years)+1` ถ้ามีข้อมูลจะเพิ่มปีใน `sites/angthong.json` เอง (`currentYear` = ปีใหม่, เป้าหมายยังว่าง → เว็บแสดง "เป้าหมาย: ยังไม่กำหนด") และเปิด Issue **"พบข้อมูลปีงบ 2570 — กรุณาใส่เป้าหมาย"** → ใส่เป้าใน `targets` แล้ว push (หรือหน้า `/admin/`) แล้วปิด Issue
- **ล้มเหลว**: ไม่ commit (เว็บคงข้อมูลเดิม) · workflow แดง · เปิด Issue label `pipeline` "อัปเดตข้อมูลล้มเหลว <วันที่>" แนบ log 50 บรรทัด (ถ้ามี Issue เปิดอยู่จะคอมเมนต์ต่อ) · GitHub ส่งอีเมลให้เอง · ปิด Issue เองเมื่ออ่านแล้ว
- กดรันเองได้ที่ GitHub → Actions → **update-data** → Run workflow (ติ๊ก `national` ถ้าต้องการรอบ 77 จังหวัด)

### ทำเองในเครื่อง
ต้องมี Python 3.13 (python.org) และ package ใน `scripts/requirements.txt`:

```bash
python3 -m pip install -r scripts/requirements.txt
```

```bash
python3 scripts/kpi.py update --site angthong
```

| คำสั่ง | ความหมาย |
|---|---|
| `update` | ตรวจปีใหม่ → fetch (ใช้ raw cache ใน `data/raw_api/` ถ้ามี) → units → build → verify |
| `update --refresh` | ไม่ใช้ raw cache ยิง API ใหม่ (DSPM 8 จังหวัด ≈ 5 นาที) |
| `update --national` | DSPM ทั้ง 77 จังหวัด → `data/cache/dspm/<ปี>/provinces.json` (ระดับประเทศ/เขต ≈ 45 นาที ห้ามยิงขนาน) |
| `update --year 2570` | เฉพาะปีที่ระบุ (ซ้ำได้) · `--indicator dspm` เฉพาะตัวชี้วัด · `--no-auto-year` ข้ามการตรวจปีใหม่ |
| `fetch` / `units` / `build` / `verify` | ทำทีละขั้น · `build` และ `verify` ทำงาน offline จาก `data/cache/` |
| `units` | เติมทะเบียนที่ตั้งหน่วยบริการ `data/lookup/units.json` จาก MOPH GIS (เฉพาะรหัสใหม่) |
| `lookup` | สร้าง `data/lookup/areas.json` ใหม่ (ชื่อพื้นที่จากรหัส DOPA + ตารางจังหวัด→เขตสุขภาพ) |

จบด้วย exit code ≠ 0 ถ้ามี **hard error** (สูตรไม่ตรง, จำนวนแถวผิด, ตัวเลขไม่ตรง Excel) → ห้าม push จนกว่าจะแก้ ·
สถานะรอบล่าสุดอยู่ใน `data/cache/pipeline_status.json` (ไม่ commit)
Warning ที่คาดไว้แล้ว: `normal_total ≠ female + male` และ `followed ≠ normal_after + delay_after_total` (ความคลาดของ HDC เอง) · `API != HDC Excel` ของ DSPM ประเทศ/เขต · เขต 13 (กทม.) ไม่มีข้อมูล DSPM · อำเภอรหัส `1310` (ปทุมธานี) ไม่มีในทะเบียน → แถว "ไม่ระบุพื้นที่"

หลังรันผ่านแล้ว:

```bash
git add -A && git commit -m "data: update" && git push
```

### ใส่เป้าหมาย / เพิ่มปี
`sites/angthong.json` → `years`, `currentYear`, `targets.<indicator>.<ปี>.value` (ไม่มีค่า = "ยังไม่กำหนด" สีกลาง ไม่มีเส้นเป้า) · หรือแก้ทับผ่านหน้า `/admin/` (ค่าใน KV ทับค่า repo จนกว่าจะกด "คืนค่าเริ่มต้น")

### เพิ่ม Excel HDC มาตรวจสอบ
วางไฟล์ Excel ที่ export จาก HDC ไว้ที่ `data/excel_reference/<dspm|coverage>/<ปี>/<YYYY-MM-DD>/` เท่านั้น — ชื่อโฟลเดอร์คือวันที่ export (ปี พ.ศ. เช่น `2569/2569-09-30/`) และถือเป็น asOf ของไฟล์ชุดนั้น · ชื่อไฟล์อิสระ (`verify` อ่านระดับจาก header A1 `เขตสุขภาพ`/`จังหวัด`/`อำเภอ`/`ตำบล` และหาพื้นที่จากชื่อแถว) · ไฟล์ที่วางใน `<ปี>/` ตรง ๆ จะทำให้ `build`/`verify` หยุดพร้อม error · ถ้าข้อมูล API ใหม่กว่าวันที่ของโฟลเดอร์ ตัวเลขที่ต่างเป็น warning (โครงสร้างยัง hard: ชุดแถว/ชื่อตำบล/ผลรวมข้ามระดับ) — อยาก verify แบบตรง 100% ให้ export ชุดใหม่ลงโฟลเดอร์วันที่ใหม่ ·
อำเภอที่มีไฟล์รายตำบลตรง 100% จะถูกใส่ใน `index.json → verified` และป้ายบนเว็บเปลี่ยนเป็น "ตรวจกับ HDC แล้ว" ·
อำเภอที่ควร export มาเพิ่ม (มีหน่วยนอกทะเบียนมาก): ดู spec §4.4

## 2. โครงสร้าง repo

```
kpi-health/
├── README.md · web_spec_phase2.md · web_spec.md
├── docs/                               # API_NOTES.md · UNIT_LOCATION_HDC_2569.md · units_missing_2569.xlsx (100 หน่วย fallback รายอำเภอ)
├── .github/workflows/update.yml        # อัปเดตอัตโนมัติ (§1)
├── functions/api/hit.js · config.js    # Pages Functions: นับผู้ใช้ (D1 `DB`) · config override สาธารณะ (KV `CONFIG`)
├── functions/api/admin/*.js · _lib/    # หน้าผู้ดูแล (Google Sign-In → KV/D1) ดู §3
├── sites/angthong.json                 # ชื่อ, โลโก้, home = เขต 4, drill 8 จังหวัด, ปี, เป้าหมาย, กฎสี
├── data/
│   ├── excel_reference/{dspm,coverage}/<ปี>/<YYYY-MM-DD>/*.xlsx   # oracle (ชื่อไฟล์อิสระ · โฟลเดอร์วันที่ = วัน export)
│   ├── excel_reference/_unresolved/    # Excel ที่ยังไม่ตรง API (นนทบุรี 3 อำเภอ) — verify ไม่อ่าน, ใช้กับ unit_location_solver.py
│   ├── lookup/areas.json + units.json + SOURCE.md   # รหัส→ชื่อพื้นที่ · ที่ตั้งหน่วยบริการ (MOPH GIS + `overrides` รายหน่วยจาก Excel HDC)
│   ├── cache/dspm/<ปี>/{12,13,14,15,16,17,19,26,provinces}.json · coverage/<ปี>/all.json   # commit (ปี 2567–2568 มีเฉพาะ provinces.json + coverage)
│   ├── logo-r4.jpg · logo.webp         # โลโก้ต้นฉบับ (เขต 4 · รพ.อ่างทอง)
│   └── raw_api/                        # response ดิบ (.gitignore)
├── scripts/
│   ├── kpi.py                          # CLI (§1)
│   ├── loaders/moph_api.py · xlsx_hdc.py
│   ├── indicators/dspm.py · coverage.py   # plugin ต่อตัวชี้วัด (metadata + สูตร + กฎที่ตั้งหน่วย)
│   ├── build_site.py · verify.py · build_lookup.py · process_logo.py
│   └── requirements.txt
└── site/                               # Cloudflare output directory
    ├── index.html · _redirects (/angthong/* → /) · admin/ (หน้าผู้ดูแล)
    ├── assets/ (styles.css, app.js, modules/, logo-r4.png, logo-angthong.png)
    └── data/angthong/ index.json + <ind>_<ปี>_{country_TH,region_4,province_<8>,district_<70>}.json
```

หน้าเดียว ใช้ hash `#/<indicator>/<ปี>/<level>/<code>` เช่น `#/dspm/2569/province/19` · `#/coverage/2569/district/1903` (level ∈ region|province|district)

## 3. Cloudflare Pages (ทำครั้งเดียว)

1. Workers & Pages → Create → Pages → Connect to Git → repo `parinyapaw-del/kpi-health` → Project name `kpi-health` · Production branch `main` · Build command **ว่าง** · Build output directory **`site`** → Save and Deploy
2. **ยอดผู้ใช้ (Phase 2)**: Workers & Pages → **D1** → Create database `kpi-health-hits` → Pages project `kpi-health` → Settings → **Bindings** → Add → D1 database · Variable name **`DB`** · database `kpi-health-hits` → Save แล้ว redeploy 1 ครั้ง (Function สร้างตาราง `hits` เองครั้งแรก) · ไม่มี binding เว็บยังใช้ได้ footer แสดง "–" · **ทำแล้ว 2026-09-30** (D1 `kpi-health-hits` bind เป็น `DB`)
3. **หน้าผู้ดูแล (Phase 2b)** — ดูหัวข้อถัดไป

ทุกครั้งที่ `git push` ขึ้น `main` จะ deploy ใหม่อัตโนมัติ (≈ 1 นาที)

### Phase 2b — หน้าผู้ดูแล `/admin/` (Google Sign-In + KV)

หน้า `https://kpi-health.pages.dev/admin/` (ลิงก์ "ผู้ดูแลระบบ" ท้ายหน้า) ให้ผู้ดูแลแก้ **ข้อความ / เป้าหมาย / ปีปัจจุบัน** ทับค่าใน repo (พร้อมตัวอย่างสด) · ดู **สถิติผู้ใช้งาน** รายวัน/รายหน้า/พื้นที่ผู้ชม · จัดการ **อีเมลผู้ดูแล** · **ดาวน์โหลด spec.md** (spec ล่าสุด + README §1, §3 + config ปัจจุบัน) · **คืนค่าเริ่มต้น** · เห็นสถานะ workflow อัปเดตข้อมูลล่าสุด · เข้าได้เฉพาะบัญชี Google ในรายชื่อผู้ดูแล

ตั้งค่าครั้งเดียว (ทำใน browser หลัง login):
1. **Google Cloud Console** → APIs & Services → Credentials → Create credentials → **OAuth client ID** (Web application) · Authorized JavaScript origins = `https://kpi-health.pages.dev` (ถ้ายังไม่มี OAuth consent screen ให้สร้างแบบ External + เพิ่มอีเมลผู้ดูแลเป็น test user หรือ publish) → คัดลอก **Client ID** (ไม่ใช่ความลับ ไม่ต้องใช้ client secret)
2. **Cloudflare** → Workers & Pages → **KV** → Create namespace `kpi-health-config` → Pages project `kpi-health` → Settings → **Bindings** → Add → KV namespace · Variable name **`CONFIG`** = `kpi-health-config`
3. Pages `kpi-health` → Settings → **Variables and Secrets** → เพิ่ม `GOOGLE_CLIENT_ID` = Client ID จากข้อ 1 และ `ADMIN_EMAILS` = อีเมลผู้ดูแลตั้งต้นคั่นด้วย comma (ใช้เมื่อ KV ยังไม่มี key `admins`; เมื่อบันทึกรายชื่อจากหน้า admin ครั้งแรก รายชื่อจะไปอยู่ใน KV key `admins` และตัวแปรนี้ไม่มีผลอีก) → **Redeploy** 1 ครั้ง (binding/env มีผลเมื่อ deploy ใหม่)
4. เปิด `/admin/` → Sign in with Google → ต้องเห็นหน้า dashboard · อีเมลนอกรายชื่อจะเห็น "ไม่อยู่ในรายชื่อผู้ดูแล"

โครงสร้าง: `functions/api/config.js` (สาธารณะ, `{override, googleClientId}`, cache 60 วิ) · `functions/api/admin/_middleware.js` ตรวจ ID token กับ Google tokeninfo (`aud` = `GOOGLE_CLIENT_ID`, `email_verified`, อีเมล ∈ รายชื่อ) → `config.js` (GET/PUT/DELETE KV `site`) · `admins.js` (KV `admins`, ห้ามลบตัวเอง) · `stats.js` (D1 `hits`) · `spec.js` · `pipeline.js` (GitHub API สาธารณะ) · เว็บ merge override ใน `site/assets/modules/configOverride.js` ก่อน render — ถ้า `/api/config` ล้มเว็บใช้ค่า repo ตามเดิม · KV `site` เก็บเฉพาะ field ที่แก้ (`name, org, footerNote, currentYear, indicators.<id>.{name_th,short,cards[]}, targets.<id>.<ปี>.value`) · ไม่มีอีเมลผู้ดูแลใน repo

## 4. ข้อควรรู้เกี่ยวกับข้อมูล

- ทุกเปอร์เซ็นต์บนเว็บมีตัวตั้ง/ตัวหารกำกับ · สีตามกฎ ok ≥ เป้า · warn [เป้า−5, เป้า) · bad < เป้า−5 · ตัวหาร < 20 = "n<20" ไม่นับในอันดับ
- **ระดับอำเภอและตำบล**: รายงาน HDC จัดกลุ่มตาม**ที่ตั้งของหน่วยบริการ (hospcode)** ในทะเบียน MOPH GIS ไม่ใช่ `areacode` ของบ้านเด็ก (ตรง Excel 100% ที่ อ่างทอง/สระบุรี/อยุธยา รายอำเภอ และ เมืองอ่างทอง/หนองแค/ท่าเรือ รายตำบล) · หน่วยที่ไม่มีในทะเบียน (100 จาก 982 หน่วย ส่วนใหญ่คลินิกเอกชน/อปท. ในนนทบุรี-ปทุมธานี) ใช้ตำบลที่หน่วยมีเป้ามากสุด → ป้าย `[INFERRED] หน่วย n แห่งใช้การอนุมานที่ตั้ง` บนหน้ารายอำเภอ
- **Coverage** ปี 2569 API ให้ 1 แถวต่ออำเภอ (ไม่มีรายหน่วย/ตำบล) → ลึกสุดคือหน้ารายจังหวัด (แถว = อำเภอ) · ปี 2567–2568 ให้รายจังหวัดเท่านั้น
- Coverage headline = (8) อัตราเข้าถึงบริการสะสม เป้า 30 · บรรทัดย่อย "ปีงบนี้" = (10) · กราฟ: แดง = คาดประมาณเด็กล่าช้า (3) เขียว = เข้าถึงสะสม (7)
- เขตสุขภาพที่ 13 (กทม.) DSPM ทั้งแถวเป็น 0 → "ไม่มีข้อมูล" ไม่นับในกราฟ/อันดับ · เขต 4 อยู่อันดับ x/12
- รายละเอียด API และ field mapping: [`docs/API_NOTES.md`](docs/API_NOTES.md) · ที่มาของรหัสพื้นที่/ทะเบียนหน่วย: [`data/lookup/SOURCE.md`](data/lookup/SOURCE.md)

## 5. ข้อมูลประชากร HDC / ตัวหารเด็ก 0–5 ปี → ย้ายไป repo `primary-care-health` (2026-09-30)

โค้ด pop/typearea/denom05, cache, Excel ที่ export มือ และเอกสารผลตรวจสอบ อยู่ที่ `../primary-care-health/` (เว็บเสริม Primary Care อ่างทอง)
ซึ่งอ่านเป้า DSPM/ตัวหาร Coverage จาก `site/data/angthong/*.json` ของ repo นี้ — อย่าเปลี่ยนชื่อไฟล์ dataset โดยไม่แจ้ง
