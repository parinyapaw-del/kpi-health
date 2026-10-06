# kpi-health — ระบบติดตามตัวชี้วัดเข็มมุ่งพัฒนาการเด็ก เขตสุขภาพที่ 4

Dashboard ตัวชี้วัดพัฒนาการเด็กปฐมวัยสำหรับผู้ตรวจราชการ เปิด link แล้วดูได้ทันที ไม่ต้อง login
เจาะได้ 4 ชั้น: **เขตสุขภาพที่ 4 → 8 จังหวัด → ทุกอำเภอ (70) → ทุกตำบล (702 ตำบลที่มีหน่วยบริการ — ตัวเลขสดดู §4)**

- URL: `https://kpi-health.pages.dev/` (link เก่า `/angthong/…` redirect มาที่นี่)
- จัดทำโดย: โรงพยาบาลอ่างทอง
- Spec ฉบับล็อก: [`web_spec_phase2.md`](web_spec_phase2.md) (v2.0, 2026-09-30 · §3/§4.4 เป็น snapshot วันนั้น, สิ่งที่เปลี่ยนหลังจากนั้นดู §12 ของ spec) · Phase 1: [`web_spec.md`](web_spec.md) · ตัวเลขสดอยู่ที่ README §4 ที่เดียว
- ตัวชี้วัด: **สมวัย** — ร้อยละของเด็กอายุ 0-5 ปี มีพัฒนาการสมวัย 5 ช่วงอายุ (DSPM) และ **เข้าถึงบริการ** — ร้อยละของเด็กปฐมวัยที่มีพัฒนาการล่าช้าเข้าถึงบริการพัฒนาการและสุขภาพจิตที่ได้มาตรฐาน (Coverage) · ปีงบ 2569 (ปีใหม่เพิ่มเองเมื่อ DSPM ของปีนั้นมีข้อมูล — ดู §1)
- แหล่งข้อมูล: **MOPH Open Data API ทุกระดับ** · Excel HDC export ใน `data/excel_reference/` เป็น oracle ให้ `verify` (ระดับอำเภอ/ตำบลต้องตรง 100% · DSPM ประเทศ/เขต ต่างจาก HDC ได้ 0.1–3% → warning, ดู `docs/API_NOTES.md` §3)
- Static site (vanilla HTML/CSS/JS + Chart.js จาก CDN) ไม่มี build step + Pages Function `/api/hit` (นับผู้ใช้, D1) · deploy ด้วย Cloudflare Pages จาก `site/`

## 1. อัปเดตข้อมูล

### อัตโนมัติ (GitHub Actions — [`.github/workflows/update.yml`](.github/workflows/update.yml))
- **ทุกวัน 07:00 ICT**: DSPM 8 จังหวัดเขต 4 + Coverage ทั้งประเทศ ของ `currentYear` และปีก่อนหน้า (policy `refresh_scope()` ใน `scripts/kpi.py`; ปีที่เก่ากว่านั้นใช้ cache ที่ commit ไว้ ไม่ดึงซ้ำ — ดึงเฉพาะเมื่อ cache หาย) → build → verify → ถ้าผ่านและมีข้อมูลใหม่ commit `data: auto-update <วันที่>` → Cloudflare deploy เอง (≈ 10 นาที) · timeout 40 นาที
- **ทุกวันจันทร์** (หรือกด `national`): เพิ่ม DSPM ทั้ง 77 จังหวัดของ `currentYear` (`--national`, ราว 45–85 นาทีต่อปี) สำหรับกราฟ 13 เขต / ยอดเขต 4 · timeout 150 นาที
- **ปีงบใหม่** (`"autoYear": true` ใน `sites/angthong.json`):
  1. ทุกรอบ `kpi.py` **แค่ probe** API ปี `max(years)+1` (Coverage ทั้งประเทศ + DSPM จังหวัด 15 หรือจังหวัด drill แรก) — ไม่แก้ `sites/angthong.json` · นับว่า "พบปีใหม่" เมื่อ **DSPM มีแถวเท่านั้น** (มีแต่ Coverage = รอ)
  2. รอบรายวันที่พบ: **ไม่ดึงปีใหม่** · เขียน `pendingYears: [Y]` ลง `pipeline_status.json` → step "dispatch รอบระดับประเทศของปีงบใหม่" สั่ง `gh workflow run update.yml -f national=true -f year=Y` (ข้ามถ้ามีรอบ run-name "ปีงบ Y" ค้างอยู่ queued/in_progress)
  3. รอบ national ของ Y (`update --refresh --national --year Y` หรือรอบวันจันทร์ที่ probe พบ Y): DSPM ทั้ง 77 จังหวัดของ Y → Coverage (0 แถว = warning ไม่ล้ม) → units → **เมื่อมี `data/cache/dspm/Y/provinces.json` แล้วเท่านั้น** จึงเพิ่ม Y ใน `years`, `currentYear = max(currentYear, Y)`, **เป้าหมายของ Y ที่ยังไม่มี = คัดลอกจากปีก่อนหน้า** (`targets.<ind>.Y = {"value": v, "inheritedFrom": Y-1}` — Save 2026-10-06: เว็บมีสีต่อเนื่อง ไม่ต้องรอใส่เป้า), status `newYears: [Y]` + `inheritedTargets` → เปิด Issue **"พบข้อมูลปีงบ Y — กรุณาตรวจ/แก้เป้าหมาย"** (บอกเป้าที่ใช้อยู่) → ตรวจ/แก้ที่หน้า `/admin/` (หรือ `targets` แล้ว push) แล้วปิด Issue · ปี 2570 ใส่ไว้ล่วงหน้าแล้วใน config (DSPM 88 / Coverage 30 = เท่าปี 2569)
     (รอบที่ดึงปีใหม่ระดับประเทศจะดึง `currentYear` เดิมแบบ 8 จังหวัดเท่านั้นในรอบนั้น เพื่อให้จบใน 150 นาที — รอบ 77 จังหวัดของปีเดิมรอวันจันทร์ถัดไป)
  4. ดึง DSPM ของ Y ล้ม → exit 2 + Issue "อัปเดตข้อมูลล้มเหลว" และ config ไม่เปลี่ยน · DSPM ว่างทั้ง 77 จังหวัด → warning ไม่เพิ่มปี
- **ล้มเหลว / หมดเวลา**: ไม่ commit (เว็บคงข้อมูลเดิม) · workflow แดง · step Issue (`if: always()`) เปิด Issue label `pipeline` "อัปเดตข้อมูลล้มเหลว <วันที่>" แนบ log 50 บรรทัด (ถ้ามี Issue เปิดอยู่จะคอมเมนต์ต่อ) ทั้งกรณี failure และ cancelled/timeout · GitHub ส่งอีเมลให้เอง · ปิด Issue เองเมื่ออ่านแล้ว
- กดรันเองได้ที่ GitHub → Actions → **update-data** → Run workflow · input `national` (ติ๊กถ้าต้องการรอบ 77 จังหวัด) และ `year` (ปี พ.ศ. `25xx` เช่น `2570` — จำกัดการดึงเฉพาะปีนั้น; ปีที่ยังไม่อยู่ใน config + `national` = เพิ่มปีเมื่อดึงสำเร็จ; เว้นว่าง = ตาม config) · ชื่อรอบบน Actions ต่อท้าย "ปีงบ Y" / "(national)"

### ทำเองในเครื่อง
ต้องมี Python 3.13 (python.org) และ package ใน `scripts/requirements.txt` (`requests`, `certifi`, `openpyxl`):

```bash
python3 -m pip install -r scripts/requirements.txt
```

```bash
python3 scripts/kpi.py update --site angthong
```

| คำสั่ง | ความหมาย |
|---|---|
| `update` | probe ปีใหม่ → fetch ตาม refresh policy (ใช้ raw cache ใน `data/raw_api/` ถ้ามี) → units → build → verify |
| `update --refresh` | ไม่ใช้ raw cache ยิง API ใหม่ — เฉพาะ `currentYear` และ `currentYear-1` (DSPM 8 จังหวัด ≈ 5 นาทีต่อปี + Coverage) · ปีเก่ากว่านั้นใช้ cache ที่ commit (ดึงแบบไม่ refresh เฉพาะเมื่อ cache หาย) |
| `update --national` | + DSPM ทั้ง 77 จังหวัดของ `currentYear` (และปีใหม่ที่ probe พบ) → `data/cache/dspm/<ปี>/provinces.json` (ระดับประเทศ/เขต ห้ามยิงขนาน) |
| `update --year 2570` | **จำกัดการ fetch เฉพาะปีที่ระบุ** (ซ้ำได้ — ปีอื่นไม่ถูกดึง) · build/verify ยังครอบทุกปีใน config ∪ ปีที่ระบุ · ไม่ probe ปีใหม่ · ใช้กับ `--national` = DSPM 77 จังหวัดของปีนั้น และถ้าปีนั้นยังไม่อยู่ใน config จะถูกเพิ่มเมื่อได้ `provinces.json` · ไม่ใส่ `--national` = ดึงแบบ 8 จังหวัด ไม่เพิ่มปีใน config |
| `--indicator dspm` · `--no-auto-year` | เฉพาะตัวชี้วัด · ข้ามการ probe ปีใหม่ |
| `fetch` / `units` / `build` / `verify` | ทำทีละขั้น · `build` และ `verify` ทำงาน offline จาก `data/cache/` |
| `units` | เติมทะเบียนที่ตั้งหน่วยบริการ `data/lookup/units.json` จาก MOPH GIS (เฉพาะรหัสใหม่ + รหัสที่ GIS เคยล่ม) |
| `lookup` | สร้าง `data/lookup/areas.json` ใหม่ (ชื่อพื้นที่จากรหัส DOPA + ตารางจังหวัด→เขตสุขภาพ) |

Refresh policy: ปีที่ถูก "refresh" = `refreshYears` ปีล่าสุดจบที่ `currentYear` (key ไม่บังคับใน `sites/angthong.json` — ตอนนี้ไม่มี key นี้ จึงใช้ค่าเริ่มต้น 2 = `currentYear` กับปีก่อนหน้า) · ปีปิดแล้วข้อมูลไม่เปลี่ยน จึงไม่ยิงซ้ำ

จบด้วย exit code ≠ 0 ถ้ามี **hard error** (สูตรไม่ตรง, จำนวนแถวผิด, ตัวเลขไม่ตรง Excel) → ห้าม push จนกว่าจะแก้ ·
สถานะรอบล่าสุดอยู่ใน `data/cache/pipeline_status.json` (ไม่ commit; ฟิลด์ `ok`, `years`, `newYears`, `pendingYears`, `national`, `fetchPlan` (โหมดของแต่ละปี: national/drill/cached), `fetchWarnings`, `hardErrors`, `warnings`, `filesWritten`, `error`) · exit code: 0 ok · 1 verify hard error · 2 fetch ล้ม · 3 `--fail-test`
Warning ที่คาดไว้แล้ว: `normal_total ≠ female + male` และ `followed ≠ normal_after + delay_after_total` (ความคลาดของ HDC เอง) · `API != HDC Excel` ของ DSPM ประเทศ/เขต · เขต 13 (กทม.) ไม่มีข้อมูล DSPM · อำเภอรหัส `1310` (ปทุมธานี) ไม่มีในทะเบียน → แถว "ไม่ระบุพื้นที่" · ทะเบียน GIS ล่ม/timeout ระหว่างดึงหน่วยใหม่ → หน่วยนั้นใช้ fallback ชั่วคราว (นับเป็น INFERRED) และยิงซ้ำรอบถัดไปเอง ไม่ทำให้รอบล้ม · Coverage ปีใหม่ API ยังให้ 0 แถว → warning (ไม่ล้ม) · แถว Coverage ที่เสียถูกข้ามและนับเป็น warning

หลังรันผ่านแล้ว:

```bash
git add -A && git commit -m "data: update" && git push
```

### ใส่เป้าหมาย / เพิ่มปี
`sites/angthong.json` → `years`, `currentYear`, `targets.<indicator>.<ปี>.value` (ไม่มีค่า = "ยังไม่กำหนด" สีกลาง ไม่มีเส้นเป้า — heatmap แสดง "เป้าหมาย: ยังไม่กำหนด (ไม่แบ่งสี)"; ปีใหม่ที่ pipeline เพิ่มเองจะคัดลอกเป้าปีก่อนหน้าให้ — key `inheritedFrom` บอกที่มา) · หรือแก้ทับผ่านหน้า `/admin/` (ค่าใน KV ทับค่า repo จนกว่าจะกด "คืนค่าเริ่มต้น") · ปีใหม่ปกติ pipeline เพิ่มใน `years`/`currentYear` ให้เอง (§1) ไม่ต้องแก้มือ · หน้า admin แสดงช่องเป้าเฉพาะปีที่มีข้อมูลบนเว็บแล้ว

### เพิ่ม Excel HDC มาตรวจสอบ
วางไฟล์ Excel ที่ export จาก HDC ไว้ที่ `data/excel_reference/<dspm|coverage>/<ปี>/<YYYY-MM-DD>/` เท่านั้น — ชื่อโฟลเดอร์คือวันที่ export (ปี พ.ศ. เช่น `2569/2569-09-30/`) และถือเป็น asOf ของไฟล์ชุดนั้น · ชื่อไฟล์อิสระ (`verify` อ่านระดับจาก header A1 `เขตสุขภาพ`/`จังหวัด`/`อำเภอ`/`ตำบล` และหาพื้นที่จากชื่อแถว) · ไฟล์ที่วางใน `<ปี>/` ตรง ๆ จะทำให้ `build`/`verify` หยุดพร้อม error · ถ้าข้อมูล API ใหม่กว่าวันที่ของโฟลเดอร์ ตัวเลขที่ต่างเป็น warning (โครงสร้างยัง hard: ชุดแถว/ชื่อตำบล/ผลรวมข้ามระดับ) — อยาก verify แบบตรง 100% ให้ export ชุดใหม่ลงโฟลเดอร์วันที่ใหม่ ·
อำเภอที่มีไฟล์รายตำบลตรง 100% จะถูกใส่ใน `index.json → verified` และป้ายบนเว็บเปลี่ยนเป็น "ตรวจกับ HDC แล้ว" ·
อำเภอที่ควร export มาเพิ่ม (มีหน่วยนอกทะเบียนมาก): ดู spec §4.4 (snapshot 2026-09-30) · ปีที่ไม่มีไฟล์ HDC ให้ตรวจ หน้า heatmap จะแสดง "ยังไม่มีไฟล์ HDC ให้ตรวจสำหรับปีนี้" (+ ป้าย [INFERRED] ถ้ามีหน่วยอนุมานที่ตั้ง)

## 2. โครงสร้าง repo

โฟลเดอร์ในเครื่อง Save: `~/Projects/kpi-health/` (ย้ายจาก `~/Desktop/Claude/web project/` เมื่อ 2026-10-06 เพราะ Desktop sync กับ iCloud Drive แล้วสร้างไฟล์ซ้ำ `… 2.json`) · repo พี่น้อง `~/Projects/primary-care-health/` ต้องอยู่ข้างกัน (อ้างด้วย `../`)

```
kpi-health/
├── README.md · web_spec_phase2.md · web_spec.md
├── docs/                               # API_NOTES.md · UNIT_LOCATION_HDC_2569.md · units_missing_2569.xlsx (หน่วยนอกทะเบียนรายอำเภอ — จำนวนดู §4)
├── .github/workflows/update.yml        # อัปเดตอัตโนมัติ (§1)
├── functions/api/hit.js · config.js    # Pages Functions: นับผู้ใช้ (D1 `DB`) · config override สาธารณะ (KV `CONFIG`)
├── functions/api/admin/*.js            # หน้าผู้ดูแล (Google Sign-In → KV/D1) ดู §3
├── functions/_lib/auth.js · http.js · config.js   # ตรวจ token · helper request/response (`readJsonBody` นับ byte UTF-8) · `REPO` + `readSiteOverride` (KV `site`)
├── sites/angthong.json                 # ชื่อ, โลโก้, home = เขต 4, drill 8 จังหวัด, ปี, เป้าหมาย, กฎสี (+ `refreshYears` ไม่บังคับ)
├── data/
│   ├── excel_reference/{dspm,coverage}/<ปี>/<YYYY-MM-DD>/*.xlsx   # oracle (ชื่อไฟล์อิสระ · โฟลเดอร์วันที่ = วัน export)
│   ├── excel_reference/_unresolved/    # Excel ที่ยังไม่ตรง API (นนทบุรี 3 อำเภอ) — verify ไม่อ่าน, ใช้กับ scripts/tools/unit_location_solver.py
│   ├── lookup/areas.json + units.json + SOURCE.md   # รหัส→ชื่อพื้นที่ · ที่ตั้งหน่วยบริการ (MOPH GIS + `overrides` รายหน่วยจาก Excel HDC)
│   ├── cache/dspm/<ปี>/{12,13,14,15,16,17,19,26,provinces}.json · coverage/<ปี>/all.json   # commit (ปี 2567–2568 มีเฉพาะ provinces.json + coverage)
│   ├── logo-r4.jpg · logo.webp         # โลโก้ต้นฉบับ (เขต 4 · รพ.อ่างทอง)
│   └── raw_api/                        # response ดิบ (.gitignore)
├── scripts/
│   ├── kpi.py                          # CLI (§1) — probe ปีใหม่, refresh policy, pipeline_status.json
│   ├── loaders/moph_api.py · xlsx_hdc.py
│   ├── indicators/common.py · dspm.py · coverage.py   # plugin ต่อตัวชี้วัด (metadata + ตาราง PCT + สูตร + กฎที่ตั้งหน่วย) · common = helper ร่วม
│   ├── build_site.py · verify.py · build_lookup.py
│   ├── tools/                          # งานเครื่องมือครั้งเดียว รันเองในเครื่อง (Actions ไม่รัน): process_logo.py · unit_location_solver.py · units_missing_xlsx.py
│   ├── requirements.txt                # requests · certifi · openpyxl (pipeline + Actions)
│   └── requirements-dev.txt            # pillow · numpy (เฉพาะ scripts/tools/)
└── site/                               # Cloudflare output directory
    ├── index.html · _redirects (/angthong/* → /) · admin/ (หน้าผู้ดูแล)
    ├── assets/ (styles.css, app.js, modules/, logo-r4.png, logo-angthong.png)
    └── data/angthong/ index.json + dspm_<ปี>_district_<70>.json + <ind>_<ปี>_{country_TH,region_4,province_<8>}.json  # Coverage ลึกสุดคือจังหวัด · ไฟล์ district ไม่มี `units`
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

**ทำแล้ว 2026-09-30**: OAuth client `kpi-health-admin` ในโปรเจกต์ Google Cloud `pcu-supply-request` (Client ID `572074800379-ttr7shbi75gm7dql56elbnf4tvo5gjhf.apps.googleusercontent.com` — ไม่ใช่ความลับ) · KV `kpi-health-config` bind `CONFIG` · env `GOOGLE_CLIENT_ID`, `ADMIN_EMAILS` ตั้งใน Pages แล้ว (ค่าอีเมลอยู่ใน Cloudflare เท่านั้น)

โครงสร้าง: `functions/api/config.js` (สาธารณะ, `{override, googleClientId}`, cache 60 วิ) · `functions/api/admin/_middleware.js` ตรวจ ID token กับ Google tokeninfo (`aud` = `GOOGLE_CLIENT_ID`, `email_verified`, อีเมล ∈ รายชื่อ) → `config.js` (GET/PUT/DELETE KV `site`) · `admins.js` (KV `admins`, ห้ามลบตัวเอง) · `stats.js` (D1 `hits`) · `spec.js` · `pipeline.js` (GitHub API สาธารณะ) · เว็บ merge override ใน `site/assets/modules/configOverride.js` ก่อน render — ถ้า `/api/config` ล้มเว็บใช้ค่า repo ตามเดิม · KV `site` เก็บเฉพาะ field ที่แก้ (`name, org, footerNote, currentYear, indicators.<id>.{name_th,short,cards[]}, targets.<id>.<ปี>.value`) · ไม่มีอีเมลผู้ดูแลใน repo

**`currentYear` ใน KV**: server (`functions/api/admin/config.js`) รับปี พ.ศ. จำนวนเต็ม 2500–2700 แต่ฝั่งเว็บ (`configOverride.js`) **ไม่สนใจ** `currentYear` ที่ไม่อยู่ใน `years` ของ `index.json` · ค่าที่ตั้งทับไว้ **ไม่ถูกลบเอง** — ถ้าต่างจาก `currentYear` ใน repo เว็บจะไม่ขยับไปปีใหม่เอง และหน้า admin แสดงคำเตือน "ค่าปีปัจจุบันถูกแก้ทับไว้ (repo = …)" → กด "คืนค่าเริ่มต้น" หรือเลือกช่อง "ค่าจาก repo" เมื่อ pipeline เพิ่มปีใหม่แล้ว

## 4. ข้อควรรู้เกี่ยวกับข้อมูล

- ทุกเปอร์เซ็นต์บนเว็บมีตัวตั้ง/ตัวหารกำกับ · สีตามกฎ ok ≥ เป้า · warn [เป้า−5, เป้า) · bad < เป้า−5 (ค่า `warnBand` = 5) · ตัวหาร < 20 = "n<20" (ค่า `smallN` ใน `colorRules`) ไม่นับในอันดับ
- **ระดับอำเภอและตำบล**: รายงาน HDC จัดกลุ่มตาม**ที่ตั้งของหน่วยบริการ (hospcode)** ไม่ใช่ `areacode` ของบ้านเด็ก · ลำดับกฎ: `overrides` (ยืนยันจาก Excel HDC ระดับตำบล) > ทะเบียน MOPH GIS > fallback = ตำบลที่หน่วยมีเป้ามากสุดในปีนั้น (นับเป็น `inferredUnits` → ป้าย `[INFERRED] หน่วย n แห่งใช้การอนุมานที่ตั้ง` บนหน้ารายอำเภอ) · รายละเอียดและหลักฐาน: [`docs/API_NOTES.md`](docs/API_NOTES.md) · [`docs/UNIT_LOCATION_HDC_2569.md`](docs/UNIT_LOCATION_HDC_2569.md)
- **Coverage** ปี 2569 API ให้ 1 แถวต่ออำเภอ (ไม่มีรายหน่วย/ตำบล) → ลึกสุดคือหน้ารายจังหวัด (แถว = อำเภอ) · ปี 2567–2568 ให้รายจังหวัดเท่านั้น
- Coverage headline = (8) อัตราเข้าถึงบริการสะสม เป้า 30 · บรรทัดย่อย "ปีงบนี้" = (10) · กราฟ: แดง = คาดประมาณเด็กล่าช้า (3) เขียว = เข้าถึงสะสม (7)
- เขตสุขภาพที่ 13 (กทม.) DSPM ทั้งแถวเป็น 0 → "ไม่มีข้อมูล" ไม่นับในกราฟ/อันดับ · เขต 4 อยู่อันดับ x/12
- รายละเอียด API และ field mapping: [`docs/API_NOTES.md`](docs/API_NOTES.md) · ที่มาของรหัสพื้นที่/ทะเบียนหน่วย: [`data/lookup/SOURCE.md`](data/lookup/SOURCE.md)

### ตัวเลขสด (หัวข้อเดียวที่เก็บตัวเลขนับ — ณ 2026-10-06 จาก `data/lookup/units.json` และ `site/data/angthong/index.json`; เอกสารอื่นลิงก์มาที่นี่ ไม่ซ้ำตัวเลข)

| รายการ | ค่า | แหล่ง |
|---|---|---|
| พื้นที่ | 8 จังหวัด · 70 อำเภอ · **702 ตำบล**ที่มีหน่วยบริการ | `index.json → tree` |
| หน่วยบริการ (hospcode) ใน DSPM cache 8 จังหวัด ปี 2569 | **983** = 882 พบในทะเบียน GIS + **101 ไม่พบ** | `units.json → units` / `missing` |
| ใน 101 หน่วยที่ไม่พบ | รวม 22754 (เพิ่มใหม่ 2026-10-02, GIS timeout ซ้ำ → `missing[22754].gisError` ยิงซ้ำทุกรอบ) · 17 หน่วยมี `overrides` แล้ว (ที่ตั้งยืนยันจาก HDC) ที่เหลือ **84 หน่วย** ใน 19 อำเภอใช้ fallback = INFERRED (ผลรวม `inferredUnits` ใน tree) | `units.json`, `index.json` |
| `overrides` | **20** = 17 หน่วยนอกทะเบียน + 3 หน่วยที่ GIS ระบุตำบลผิด | `units.json → overrides` |
| อำเภอที่ตรง Excel HDC ระดับตำบล 100% | **21 อำเภอ** (DSPM 2569; `index.json → verified`) จาก Excel ตำบล 24 อำเภอ · อีก 3 อำเภอนนทบุรี (เมืองนนทบุรี/ปากเกร็ด/บางบัวทอง) ต่างอำเภอละ 1 แถว เพราะ HDC ไม่นับหน่วย 41609/41804/41833 → ไฟล์อยู่ใน `data/excel_reference/_unresolved/` | `index.json`, `docs/UNIT_LOCATION_HDC_2569.md` |
| `docs/units_missing_2569.xlsx` | 101 หน่วย · 23 อำเภอ (สร้างใหม่ด้วย `python3 scripts/tools/units_missing_xlsx.py`) | `units.json → missing` |
| ไฟล์ dataset บนเว็บ | 91 ไฟล์ใน `site/data/angthong/` = `index.json` + 90 dataset (DSPM: country 1 · region 1 · province 8 · district 70 · Coverage: country 1 · region 1 · province 8) | `site/data/angthong/` |

## 5. ความเกี่ยวข้องกับ repo `primary-care-health` (แยกออกไปเมื่อ 2026-09-30)

โค้ด pop/typearea, cache, Excel ที่ export มือ และเอกสารผลตรวจสอบของข้อมูลประชากร HDC / ตัวหารเด็ก 0–5 ปี อยู่ที่ `../primary-care-health/` (เว็บเสริม Primary Care อ่างทอง) — repo นั้น**ไม่อ่าน** `site/data/angthong/*.json` ของ repo นี้แล้ว (เลิกใช้ตัวหาร `denom05`) จึงเปลี่ยนชื่อไฟล์ dataset ได้โดยไม่กระทบ

สิ่งที่ยังผูกกันคือ**สำเนา**ของไฟล์ต่อไปนี้ — repo นี้เป็น master, อีก repo ซิงก์ด้วย `python3 scripts/sync_from_kpi_health.py` (อ่าน repo นี้อย่างเดียว; `--check` = ตรวจโดยไม่เขียน):
- `scripts/loaders/moph_api.py` · `data/lookup/areas.json` → copy ตรง ๆ
- `data/lookup/units.json` → merge (repo นี้ชนะเมื่อที่ตั้งขัดกัน; เก็บหน่วยที่มีเฉพาะฝั่งโน้น)
- `scripts/build_lookup.py` → **ไม่ซิงก์** (ฝั่งโน้นเป็น fork, port การแก้ด้วยมือ + `--ack-build-lookup`) — แก้ไฟล์นี้ที่นี่แล้วต้องไปไล่ port เอง

รายละเอียด: README/CLAUDE.md ของ `primary-care-health` และ docstring ของสคริปต์นั้น
