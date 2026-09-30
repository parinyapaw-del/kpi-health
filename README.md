# kpi-health — ระบบติดตามตัวชี้วัด จังหวัดอ่างทอง

Dashboard ตัวชี้วัดสาธารณสุขสำหรับผู้ตรวจราชการ เปิด link แล้วดูได้ทันที ไม่ต้อง login
เจาะได้ 4 ชั้น: ประเทศ (13 เขตสุขภาพ) → เขตสุขภาพที่ 4 (8 จังหวัด) → อ่างทอง (7 อำเภอ) → เมืองอ่างทอง (14 ตำบล)

- ผู้ดูแล: โรงพยาบาลอ่างทอง
- Spec ฉบับล็อก: [`web_spec.md`](web_spec.md) (v1.1, 2026-09-29)
- ตัวชี้วัด Phase 1: **DSPM** (ร้อยละเด็ก 0–5 ปี พัฒนาการสมวัย) และ **Coverage** (ร้อยละเด็กพัฒนาการล่าช้าเข้าถึงบริการ) ปีงบ 2567–2569
- แหล่งข้อมูล: **MOPH Open Data API ทุกระดับ** · Excel HDC export ใน `data/excel_reference/` ใช้เป็น oracle สำหรับ `verify` (ระดับอ่างทอง/อำเภอเมืองต้องตรง 100%; DSPM ประเทศ/เขต ต่างจาก HDC ได้ 0.1–3% บางจังหวัด → warning, ดู `docs/API_NOTES.md` §3)
- Static site ล้วน (vanilla HTML/CSS/JS + Chart.js จาก CDN) ไม่มี build step · deploy ด้วย Cloudflare Pages จาก `site/`

## 1. อัปเดตข้อมูล (ทำเองได้ด้วยคำสั่งเดียว)

ต้องมี Python 3.13 (python.org) และ package ใน `scripts/requirements.txt`:

```bash
python3 -m pip install -r scripts/requirements.txt
```

ดึงข้อมูลจาก API → สร้าง JSON เว็บ → ตรวจกับ Excel → รายงาน:

```bash
python3 scripts/kpi.py update --site angthong
```

ตัวเลือกที่ใช้บ่อย

| คำสั่ง | ความหมาย |
|---|---|
| `update --year 2570` | ดึงเฉพาะปีงบ 2570 (ระบุซ้ำได้หลายปี) |
| `update --indicator dspm` | ดึงเฉพาะตัวชี้วัดเดียว (`dspm` / `coverage`) |
| `update --refresh` | ไม่ใช้ raw cache ใน `data/raw_api/` ยิง API ใหม่ทั้งหมด (DSPM ดึงทุก 77 จังหวัด ทีละจังหวัด ≈ 45 นาที/ปี → ใช้คู่กับ `--year <ปีปัจจุบัน>`) |
| `fetch` / `build` / `verify` | ทำทีละขั้น · `verify` ทำงาน offline จาก `data/cache/` |
| `lookup` | สร้าง `data/lookup/areas.json` ใหม่ (ชื่อพื้นที่จากรหัส DOPA + ตารางจังหวัด→เขตสุขภาพ) |

คำสั่งจบด้วย exit code ≠ 0 ถ้ามี **hard error** (สูตรไม่ตรง, จำนวนแถวผิด, ตัวเลขไม่ตรง Excel) → ห้าม push จนกว่าจะแก้
Warning ที่คาดไว้แล้ว: `followed ≠ normal_after + delay_after_total` ระดับเขต · `normal_total ≠ female + male` ปี 2568–2569 (ความคลาดของ HDC เอง) · `API != HDC Excel` ของ DSPM ประเทศ/เขต · เขตสุขภาพที่ 13 (กทม.) ไม่มีข้อมูล DSPM

หลังรันผ่านแล้ว:

```bash
git add -A && git commit -m "data: update 2570" && git push
```

Cloudflare Pages จะ deploy ให้อัตโนมัติเมื่อ push ขึ้น `main`

### ปีใหม่ต้องเตรียมอะไรเพิ่ม
- **DSPM ระดับประเทศ / เขต 4** มาจาก API: `fetch` ดึงครบ 77 จังหวัด (cache รายจังหวัดเก็บในเครื่อง, commit เฉพาะ `data/cache/dspm/<ปี>/provinces.json`) · ปีใหม่ใช้เวลาราว 45 นาที
- Excel ของปีใหม่ **ไม่จำเป็น** แต่ถ้ามีจะถูกใช้ตรวจสอบเพิ่ม
- เพิ่มปีใน `sites/angthong.json` (`years`, `currentYear`) และเป้าหมายใน `targets`

## 2. โครงสร้าง repo

```
kpi-health/
├── README.md · web_spec.md · docs/API_NOTES.md
├── sites/angthong.json                 # ชื่อ, โลโก้, เส้นทางหลัก TH→4→15→1501, ปี, เป้าหมาย, กฎสี
├── data/
│   ├── excel_reference/angthong/{dspm,coverage}/<ปี>/*.xlsx   # oracle
│   ├── lookup/areas.json + SOURCE.md   # รหัส→ชื่อพื้นที่ + จังหวัด→เขตสุขภาพ
│   ├── cache/<indicator>/<ปี>/*.json   # aggregate จาก API (commit)
│   └── raw_api/                        # response ดิบ (.gitignore)
├── scripts/
│   ├── kpi.py                          # CLI
│   ├── loaders/moph_api.py · xlsx_hdc.py
│   ├── indicators/dspm.py · coverage.py   # plugin ต่อตัวชี้วัด
│   ├── build_site.py · verify.py · build_lookup.py · process_logo.py
│   └── requirements.txt
└── site/                               # Cloudflare output directory
    ├── index.html (redirect) · _redirects · angthong/index.html
    ├── assets/ (styles.css, app.js, modules/, logo-angthong.png)
    └── data/angthong/*.json            # JSON ที่เว็บอ่าน
```

URL: `/` → `/angthong/` · หน้าเดียว ใช้ hash `#/<indicator>/<ปี>/<level>/<code>` เช่น `#/dspm/2569/province/15`

## 3. เชื่อม Cloudflare Pages (ทำครั้งเดียว)

1. เข้า Cloudflare dashboard → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**
2. เลือก repo `parinyapaw-del/kpi-health` (GitHub)
3. Project name: `kpi-health` (ถ้าไม่ว่างใช้ `kpi-health-th`)
4. Production branch: `main` · **Build command: เว้นว่าง** · Framework preset: None · **Build output directory: `site`**
5. กด **Save and Deploy** → ได้ URL `https://kpi-health.pages.dev` (root จะ redirect ไป `/angthong/` เอง)
6. หลังจากนั้นทุกครั้งที่ `git push` ขึ้น `main` จะ deploy ใหม่อัตโนมัติ (ประมาณ 1 นาที)

## 4. เพิ่มตัวชี้วัดใหม่ (Phase 2)

1. สร้าง `scripts/indicators/<id>.py` โดยเลียนแบบ `dspm.py` / `coverage.py`: ประกาศ `ID`, `TABLE`, metadata (`name_th`, `short`, `levels`, `groups`, `headline`, `cards`, `table`, `monthly`), ฟังก์ชัน fetch/aggregate/build/validate
2. ถ้ามี Excel HDC ของตัวชี้วัดนั้น วางใน `data/excel_reference/angthong/<id>/<ปี>/` และเพิ่ม layout ใน `loaders/xlsx_hdc.py` เพื่อให้ `verify` เทียบได้
3. เพิ่ม `<id>` ใน `sites/angthong.json` → `indicators` และเป้าหมายใน `targets`
4. รัน `python3 scripts/kpi.py update --site angthong --indicator <id>` → แท็บใหม่ขึ้นเว็บเองจาก metadata (เว็บไม่ hardcode ชื่อ metric)

## 5. ข้อควรรู้เกี่ยวกับข้อมูล

- ทุกเปอร์เซ็นต์บนเว็บมีตัวตั้ง/ตัวหารกำกับ · สีตามกฎ ok ≥ เป้า · warn [เป้า−5, เป้า) · bad < เป้า−5 · ตัวหาร < 20 = "n<20" ไม่นับในอันดับ
- `monthly` ของ API DSPM = เดือนปฏิทิน (01–12) → ปีงบเรียง ต.ค.→ก.ย. · กราฟรายเดือนแสดงความคืบหน้าสะสมเทียบเป้าหมายทั้งปี
- **ระดับตำบล**: รายงาน HDC จัดกลุ่มตามตำบลของหน่วยบริการ (hospcode) ไม่ใช่ `areacode[:6]` ของบ้านเด็ก · pipeline กำหนดตำบลของแต่ละ hospcode จากพื้นที่ที่หน่วยนั้นมีเป้าหมายมากที่สุด (ตรง Excel 100% ทั้ง 3 ปี, `verify` จะฟ้องทันทีถ้าหยุดตรง)
- Coverage ปี 2567–2568 API ให้รายจังหวัดเท่านั้น → ระดับอำเภอ/ตำบลไม่มีข้อมูล · ปี 2569 มีรายอำเภอ
- เขตสุขภาพที่ 13 (กทม.) ปี 2569 DSPM ทั้งแถวเป็น 0 → แสดง "ไม่มีข้อมูล" ไม่นับในกราฟ/อันดับ
- เป้าหมายที่มี `*` (DSPM 2567 = 85, Coverage 2568 = 20) เป็นค่าอ้างอิงที่ยังไม่ยืนยัน
- รายละเอียด API และ field mapping: [`docs/API_NOTES.md`](docs/API_NOTES.md)
