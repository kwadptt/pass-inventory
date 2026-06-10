# PASS Inventory — Schema Design (v1)

> เอกสารต่อจาก `01_data_understanding.md`
> เป้าหมาย: ออกแบบ schema เชิงตรรกะก่อนเขียน Django models จริง
> ขอบเขต: รองรับ requirements ทั้งหมดที่สรุปไว้ในเฟส 1 (Tablet ก่อน, OR เดียว, 3 roles, Q1–Q3 PM rounds)

---

## ภาพรวม

7 ตารางหลัก + Django User/Group (built-in สำหรับ auth+role)

| กลุ่ม | ตาราง | บทบาท |
|---|---|---|
| Master | `Plant` | รายชื่อ plant |
| Master | `AssetType` | ชนิดอุปกรณ์ + default warranty |
| Master | `PMRound` | ปฏิทินรอบ PM ต่อปี (config ปรับได้) |
| Master | `SnPrefix` | map prefix S/N → ปี (fallback) |
| Core | `Device` | ตัวเครื่อง (entity หลัก ยึด `serial_number`) |
| Core | `PMSnapshot` | บันทึกสถานะเครื่องในแต่ละรอบ |
| Aux | `PlantRoundNote` | โน้ตระดับ plant+round |

---

## รายละเอียดต่อตาราง

### 1. `Plant`

ตาราง master ของ plant ทั้ง 7 แห่ง

| Field | Type | Constraint | หมายเหตุ |
|---|---|---|---|
| `id` | int | PK auto | |
| `code` | varchar(8) | unique, not null | เช่น `PKT`, `HDY`, `KBV`, `URT`, `UTP`, `UDT`, `CNX` |
| `name_th` | varchar(64) | not null | เช่น `ภูเก็ต` |
| `name_en` | varchar(64) | nullable | เผื่อใช้ในรายงานภาษาอังกฤษ |
| `is_active` | bool | default true | ปิด plant ที่ยกเลิกแล้วโดยไม่ลบ |

**Index:** `code` (unique)

---

### 2. `AssetType`

ชนิดอุปกรณ์ — เริ่มจาก Tablet, ขยายไปชนิดอื่น (UPS, Scanner, ...) ได้

| Field | Type | Constraint | หมายเหตุ |
|---|---|---|---|
| `id` | int | PK auto | |
| `code` | varchar(16) | unique, not null | เช่น `TABLET` |
| `name` | varchar(64) | not null | เช่น `Tablet` |
| `default_warranty_months` | int | default 12, not null | warranty default ต่อชนิด |
| `description` | text | nullable | |

**Index:** `code` (unique)

---

### 3. `PMRound`

ปฏิทินรอบ PM ต่อปี — **เก็บเป็น row ละรอบ ไม่ hard-code** เพราะ window ขยับได้ในแต่ละปี

| Field | Type | Constraint | หมายเหตุ |
|---|---|---|---|
| `id` | int | PK auto | |
| `year` | int | not null | เช่น 2025 |
| `quarter` | varchar(2) | not null, enum {`Q1`, `Q2`, `Q3`} | |
| `field_start_date` | date | not null | วันเริ่มงานภาคสนาม |
| `field_end_date` | date | not null | วันจบงานภาคสนาม |
| `document_due_date` | date | not null | กำหนดส่งเอกสาร (ใช้เป็น warranty anchor) |

**Constraint:** unique(`year`, `quarter`)
**Index:** (`year`, `quarter`) — สำหรับ lookup ตาม Q+ปี

**ตัวอย่าง row (จากแผน 2025):**
```
(2025, Q1, 2025-02-03, 2025-03-22, 2025-03-31)
(2025, Q2, 2025-05-31, 2025-07-19, 2025-07-31)
(2025, Q3, 2025-09-13, 2025-11-09, 2025-11-21)
```

---

### 4. `SnPrefix`

Mapping prefix S/N → ปี ใช้เป็น fallback สำหรับเครื่องที่ไม่มีบันทึก "ส่งมอบเครื่องใหม่" (เครื่องก่อนปี 2024)

| Field | Type | Constraint | หมายเหตุ |
|---|---|---|---|
| `prefix` | varchar(8) | PK | เช่น `RP9`, `RPB`, `RMA`, `RJB` |
| `year` | int | not null | ปีรุ่น เช่น 2025, 2023, 2021, 2018 |
| `notes` | text | nullable | |

**ตัวอย่าง row:**
```
('RP9', 2025), ('RPB', 2023), ('RMA', 2021), ('RJB', 2018), ('RNC', 2023), ('REC', ?)
```

> **Note:** ใน `Device.serial_number` เราเก็บ S/N เต็ม → derive `prefix` (3 ตัวแรก) ตอน query

---

### 5. `Device` — entity หลัก

| Field | Type | Constraint | หมายเหตุ |
|---|---|---|---|
| `id` | int | PK auto | |
| `serial_number` | varchar(32) | unique, not null | เช่น `RMA03F1028` |
| `asset_type` | FK → AssetType | not null | |
| `home_plant` | FK → Plant | nullable | plant เจ้าของ (null = legacy ไม่ทราบ) |
| `received_round` | FK → PMRound | nullable | รอบที่รับเครื่อง (null = legacy ก่อนระบบ) |
| `warranty_months_override` | int | nullable | ถ้าไม่ใส่ ใช้ของ `asset_type.default_warranty_months` |
| `is_retired` | bool | default false | true หลังจาก "เสื่อมสภาพนำกลับ Enco" |
| `retired_round` | FK → PMRound | nullable | รอบที่เสื่อมสภาพ (set พร้อม is_retired) |
| `replaced_predecessor` | FK → Device (self) | nullable | เครื่องเก่าที่ถูกเครื่องนี้แทน |
| `notes` | text | nullable | |
| `created_at`, `updated_at` | datetime | auto | |

**Index:** `serial_number` (unique), `home_plant`, `is_retired`

**Computed (ไม่เก็บใน DB, คำนวณตอนใช้):**
- `prefix` = `serial_number[:3]`
- `received_year` = ถ้ามี `received_round` ใช้ค่านั้น ถ้าไม่มี ใช้ `SnPrefix.year` จาก prefix (สมมติ Q1)
- `warranty_start` = `received_round.document_due_date` (หรือ Q1 ของปีตาม prefix สำหรับ legacy)
- `warranty_end` = `warranty_start + (warranty_months_override or asset_type.default_warranty_months)` เดือน
- `warranty_months` = `warranty_months_override or asset_type.default_warranty_months`
- `pm_responsibility` = `vendor` ถ้า `warranty_end ≥ next_pm_round.field_start_date` มิฉะนั้น `on_site`
- `current_plant` = `plant` ของ `PMSnapshot` ล่าสุด (สำหรับเครื่องนี้)
- `current_status` = `status` ของ `PMSnapshot` ล่าสุด

---

### 6. `PMSnapshot` — หัวใจของประวัติ

บันทึก 1 row ต่อ (เครื่อง, รอบ PM) → ลำดับ snapshot ของเครื่องคือ timeline ของมัน

| Field | Type | Constraint | หมายเหตุ |
|---|---|---|---|
| `id` | int | PK auto | |
| `device` | FK → Device | not null | |
| `pm_round` | FK → PMRound | not null | |
| `plant` | FK → Plant | not null | plant ที่เครื่องอยู่ในรอบนั้น (อาจ ≠ home_plant กรณีถูกยืม) |
| `status` | varchar(16) | not null, enum (ดูด้านล่าง) | |
| `note` | text | nullable | ข้อความหมายเหตุดิบ (เหมือนคอลัมน์ "หมายเหตุ" เดิม) |
| `checklist_results` | JSON | nullable | ขยายสำหรับ Role inspector (works/needs_repair/details) |
| `recorded_by` | FK → User | nullable | ใครเป็นคนกรอก |
| `recorded_at` | datetime | auto | |

**Constraint:** unique(`device`, `pm_round`)
**Index:** (`pm_round`, `plant`) — สำหรับ "ดูเครื่องทั้งหมดที่ plant X รอบ Y", (`device`, `pm_round`) — สำหรับดูประวัติเครื่อง

**Status enum:**
| ค่า | ความหมาย | mapping จากหมายเหตุเดิม |
|---|---|---|
| `in_use` | ใช้งานปกติ (default) | (ไม่มีหมายเหตุพิเศษ) |
| `new_delivery` | เพิ่งรับเครื่องใหม่ในรอบนี้ | "ส่งมอบเครื่องใหม่", "ส่งมอบใหม่ YYYY" |
| `retired` | เสื่อมสภาพ/คืนผู้ผลิต | "เสื่อมสภาพนำกลับ Enco" |
| `borrowed_in` | ยืมมาจาก plant อื่น | "ยืมจาก สอ.X", "ยืมจากกระบี่" |
| `loaned_out` | ของเราถูกยืมไป plant อื่น | "สอ.X ยืมใช้งาน", "ยืมใช้" (มุมเจ้าของ) |
| `correction` | บันทึกแก้ไขข้อมูล | "แก้ไขจากเลข ..." |

**สำคัญ:** การ "ยืม" จะเก็บแค่ฝั่ง **borrower** (plant ที่ถือเครื่องอยู่) เป็น snapshot ปกติ
ส่วนมุม **owner** ("เราถูกยืมไป") เป็น derived view: query หา snapshot ที่ `device.home_plant ≠ snapshot.plant`

---

### 7. `PlantRoundNote`

โน้ตระดับ plant + รอบ ที่ไม่ผูกกับเครื่องตัวใดตัวหนึ่ง (เช่น "เปลี่ยน UPS 2 Plug 2" ที่ merge หลายแถวในไฟล์เดิม)

| Field | Type | Constraint | หมายเหตุ |
|---|---|---|---|
| `id` | int | PK auto | |
| `plant` | FK → Plant | not null | |
| `pm_round` | FK → PMRound | not null | |
| `note` | text | not null | |
| `recorded_by` | FK → User | nullable | |
| `recorded_at` | datetime | auto | |

**Constraint:** unique(`plant`, `pm_round`)

---

### 8. `User` / `Group` (Django built-in)

- `User` ใช้ของ Django (มี username, password, email อยู่แล้ว)
- `Group` ใช้กำหนด role — สร้าง 3 groups:
  - `customer` — read-only (สำหรับ OR)
  - `support` — write บน `PMSnapshot`, `PlantRoundNote`, `Device` (ตามรอบที่กำลังเปิด)
  - `inspector` — *(future)* เหมือน support + กรอก `checklist_results` ได้
- Django permission framework จัดการสิทธิ์ระดับ model ได้พอ สำหรับ field-level (เช่น lock บางรอบ) ค่อยทำ custom logic ตอน implement

---

## การตัดสินใจสำคัญ (และเหตุผล)

### D1. การยืม → `status` ใน PMSnapshot ไม่ใช่ตารางแยก

**ทางเลือกที่พิจารณา:**
- (A) ตาราง `BorrowEvent` แยก มี `device, lender_plant, borrower_plant, start_round, end_round`
- (B) ✅ ใช้ `PMSnapshot.status` + `plant_id ≠ device.home_plant_id`

**เลือก B เพราะ:**
- ข้อมูล borrow ทั้งหมด derive ได้จาก PMSnapshot อยู่แล้ว
- ลด table + ลด complexity (ไม่ต้อง sync 2 ที่)
- ใน Excel เดิม ก็บันทึกแบบ per-round อยู่แล้ว ไม่มี "ช่วง"
- ถ้าอนาคตอยากได้ analytics เชิง event (ระยะเวลาเฉลี่ยของการยืม ฯลฯ) คำนวณจาก snapshot ได้ทั้งหมด

### D2. การเปลี่ยนเครื่อง → self-FK ใน Device ไม่ใช่ตาราง event

**ทางเลือกที่พิจารณา:**
- (A) ตาราง `ReplacementEvent` มี `old_device, new_device, plant, round`
- (B) ✅ field `replaced_predecessor_id` self-FK ใน Device

**เลือก B เพราะ:**
- ตอบ "ทดแทนเครื่องไหน" ได้ในหนึ่ง field
- "เมื่อไหร่/ที่ไหน" derive จาก PMSnapshot แรกของเครื่องใหม่ ไม่ต้องเก็บซ้ำ
- เคสที่เครื่องเดียวมีหลาย predecessor หายาก (เครื่องใหม่มักทดแทนเครื่องเก่า 1:1)

### D3. Warranty คำนวณตอนใช้ ไม่เก็บ

**เลือกไม่เก็บ `warranty_end_date` เพราะ:**
- ถ้าเก็บ → ทุกครั้งที่แก้ `warranty_months` ต้องวิ่งอัปเดตหลายแถว เสี่ยง drift
- คำนวณจาก `received_round.document_due_date + warranty_months` รวดเร็ว query ไม่หนัก
- ถ้าอนาคต performance เป็นปัญหา ค่อย materialize เป็น view

### D4. PMRound เป็นตารางแยก ไม่ใช่ enum

**เพราะ:**
- ปฏิทินจริงขยับ 1-2 สัปดาห์ต่อปี
- ต้องเก็บวันที่จริงเพื่อใช้คำนวณ warranty
- การเพิ่มปีใหม่ = เพิ่ม 3 rows ไม่ต้องแก้ code

### D5. ไม่มี cache field สถานะปัจจุบันใน Device

**ทางเลือกที่พิจารณา:** เพิ่ม `current_plant_id`, `current_status` ใน Device เพื่อ query เร็ว

**เลือกไม่ทำ เพราะ:**
- Cache ต้องรีเฟรชทุกครั้งที่มี snapshot ใหม่ → bug-prone
- ขนาดข้อมูลเล็ก (~70 เครื่อง × 15 รอบ × 5 ปี = ~5,000 rows) query ตรงเร็วพอ
- ใช้ Django ORM `prefetch_related` + queryset อาจช่วยได้ถ้าจำเป็น

### D6. หมายเหตุดิบ (`note`) + status enum ควบคู่กัน

**Status enum** ใช้สำหรับ filter/group/report (มีค่าจำกัด)
**`note` text** เก็บข้อความดิบ — เผื่อมีรายละเอียดที่ enum ครอบคลุมไม่ได้ (เช่น "เครื่องใช้งานได้ปกติ บันทึกสลับกับ RJB03F0083")
ไม่ลบ note หลัง map เป็น status เพราะข้อมูลดิบมีคุณค่าสำหรับการตรวจสอบ

### D7. ลูกค้าเดียว (OR) → ไม่มี `customer_id`

ถ้าอนาคตขยายเป็น multi-tenant ค่อยเพิ่ม field/migration ภายหลัง สำหรับตอนนี้ลดความซับซ้อนก่อน

---

## Queries หลักที่ schema นี้ตอบได้

ทดสอบความเพียงพอของ schema ด้วย use case จริง:

**Q1: "เครื่อง RMA03F1028 ผ่านอะไรมาบ้าง?"**
```python
Device.objects.get(serial_number="RMA03F1028").pmsnapshot_set.order_by("pm_round__year", "pm_round__quarter")
```

**Q2: "ตอนนี้เครื่องนี้อยู่ไหน?"**
```python
device.pmsnapshot_set.latest("pm_round__year", "pm_round__quarter").plant
```

**Q3: "เครื่องไหนที่ภูเก็ตยืมไป?"**
```python
PMSnapshot.objects.filter(device__home_plant__code="PKT", plant__ne=F("device__home_plant"))
```

**Q4: "PM coverage list ของกระบี่รอบ Q1 2026?"**
```python
# เครื่องอยู่ที่กระบี่รอบนั้น + ทีมต้องดูแล (หมดประกัน)
PMSnapshot.objects.filter(
    pm_round__year=2026, pm_round__quarter="Q1", plant__code="KBV"
).filter(<custom logic: device.warranty_end < pm_round.field_start>)
```

**Q5: "เครื่อง RPB03T0403 ทดแทนเครื่องไหน?"**
```python
Device.objects.get(serial_number="RPB03T0403").replaced_predecessor
```

**Q6: "สร้างตารางหน้าตา Excel เดิมสำหรับภูเก็ต ปี 2024-2026"**
```python
# Group PMSnapshot ตาม (plant=PKT, year, quarter) แล้ว pivot
```

---

## ไม่ครอบคลุมในรอบนี้ (defer)

- **Audit log** ของการแก้ไข — Django มี `django-simple-history` ใส่ทีหลังได้
- **Attachment** (รูปถ่ายเครื่อง, ใบ PM) — เพิ่ม field `FileField` ใน PMSnapshot ทีหลัง
- **Notification** (alert ก่อน warranty หมด) — สร้างเป็น management command + email/LINE ทีหลัง
- **Multi-tenant** — ถ้ารับลูกค้าอื่นเพิ่ม
- **Cross-asset checklist template** — ตอนทำ Role inspector จริง ค่อย design `ChecklistTemplate` table ถ้าจำเป็น

---

## ก่อนเขียน Django models — จุดที่อยากให้ดูเพิ่ม

1. **Plant codes** — ผมตั้งเดาไว้ (PKT, HDY, KBV, ...) มี convention ภายในบริษัทมั้ย?
2. **`SnPrefix.REC`** — มีในไฟล์ (REC39F1523) แต่ไม่อยู่ในแถว prefix legend → คืออะไร ปีไหน?
3. **เคสพิเศษในข้อมูล** — เจอ `RJB03F0086` ที่กระบี่ borrow ไปภูเก็ต โดยกระบี่เองก็ borrow มาจากที่อื่นด้วย (chain borrow) → schema นี้รองรับได้ แต่ logic ตอน mapping ต้องระวัง
