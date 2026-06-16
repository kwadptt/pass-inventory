# PASS Inventory — Project Context

> ไฟล์นี้คือ context สำหรับ Claude (Claude Code) โหลดเข้าทุก session โดยอัตโนมัติ
> เนื้อหาในนี้สรุปสิ่งที่ตกลงไปแล้วในเฟส planning/design — โปรดอย่ารื้อโดยไม่ถาม

---

## What this is

ระบบ inventory tracking สำหรับอุปกรณ์ที่ plant ของ **OR (PTT Oil & Retail)** เริ่มจาก Tablet ก่อน, ขยายชนิดอื่นได้ภายหลัง โครงการนี้ทดแทน workflow ที่ใช้ Excel อยู่ปัจจุบัน

## People

- **Project lead (Nopporn)** — IT secondment, ไม่ใช่ full-time developer ใช้ AI tools ในการ build แต่อยากเข้าใจการตัดสินใจ
- **Users** — ทีม IT support + field engineer (ภายใน) + OR (read-only)

## Working style — please follow

- อธิบาย technical decision ก่อน implement
- เสนอ approach ที่ง่ายที่สุดก่อน เพิ่ม complexity เฉพาะที่จำเป็น
- โค้ดอ่านง่าย ไม่ over-engineer
- ไม่แน่ใจ requirement ให้ถามก่อน assume
- ตัดสินใจสำคัญ บันทึกใน `docs/` เป็น markdown
- ตอบเป็นภาษาไทยได้ (Nopporn พิมพ์ไทย)

## Current state

| Phase | Status | ไฟล์ |
|---|---|---|
| 1. Data understanding | ✅ | `docs/01_data_understanding.md` |
| 2. Schema design | ✅ | `docs/02_schema_design.md` |
| 3. Django models + admin (verified) | ✅ | `starter/models.py`, `starter/admin.py` |
| Setup (Django project local) | ✅ | `docs/03_setup_guide.md` |
| A. Excel import | ✅ | `inventory/management/commands/import_excel.py` — 48 devices, 233 snapshots |
| B. Customer read-only view | ✅ | `inventory/views.py`, `inventory/templates/inventory/`, `docs/04_customer_view.md` |
| C. Groups + permissions | ✅ | `inventory/management/commands/setup_groups.py`, `docs/05_roles_and_permissions.md` |

Schema verified แล้ว: `python manage.py check` ผ่าน, `makemigrations` รู้จัก 7 ตารางครบ, ทดสอบ scenario (replacement, borrow, warranty calc) ใน sandbox ผ่าน

DB มีข้อมูลจริงแล้ว (import จาก `data/PASS_Inventory.xlsx`), `/devices/` ใช้งานได้ (login ผ่าน `/admin/login/`), groups `support`/`inspector`/`customer` พร้อมใช้ (ยังไม่ได้สร้าง user จริงให้ทีม — รอ Nopporn สร้างเองผ่าน admin ตาม `docs/05`)

## Tech stack (decided — อย่าเปลี่ยนโดยไม่ถาม)

- **Django 5.x + SQLite** (Postgres ทีหลังถ้า scale ต้องการ)
- **Django Admin** เป็น UI หลักสำหรับ Role support (ทีมกรอกข้อมูล)
- **3 roles via Django Groups**: `customer` (read), `support` (write), `inspector` (future write + checklist)
- **Single tenant** (OR เดียว) — ไม่มี `customer_id` ใน schema

## Key design decisions (อย่าทำกลับด้านโดยไม่ถาม)

1. **Device-centric** — entity หลักคือเครื่อง (S/N) ไม่ใช่ "ช่องที่ plant" (รายละเอียดใน `02_schema_design.md` §3)
2. **Borrow modeled as `PMSnapshot.status`** ไม่ใช่ตารางแยก (§D1)
3. **Replacement = self-FK บน Device** (`replaced_predecessor`) ไม่ใช่ event table (§D2)
4. **Warranty คำนวณตอนใช้** จาก `received_round` + `warranty_months` ไม่เก็บใน DB (§D3)
5. **PMRound dates ปรับได้ต่อปี** — เก็บใน DB ไม่ hardcode (§D4)
6. **ไม่มี `current_plant` cache บน Device** — query จาก latest PMSnapshot (§D5)
7. **`status` enum + `note` text ควบคู่กัน** — enum สำหรับ filter, note สำหรับข้อมูลดิบ (§D6)

## Recommended next step

Phase A/B/C เสร็จหมดแล้ว (ดูตาราง Current state) ยังไม่มี phase ถัดไปที่ตกลงไว้ — รอ Nopporn บอกทิศทาง
ไอเดียที่ค้างไว้ (ยังไม่ตัดสินใจ):
- สร้าง user account จริงให้ทีม + assign groups (ตาม `docs/05_roles_and_permissions.md`)
- เพิ่ม asset type อื่นนอกจาก Tablet
- Inspector checklist UI (ใช้ `PMSnapshot.checklist_results` ที่เตรียมไว้)

## Open TODOs

- [x] **Plant codes** — ใช้ PKT, HDY, KBV, URT, UTP, UDT, CNX ถูกต้องแล้ว ไม่ต้องเปลี่ยน
- [ ] **Chain borrow** ในข้อมูลเก่า (ภูเก็ตยืมจากกระบี่ ซึ่งกระบี่ก็ยืมมาจากที่อื่น) — schema รองรับ แต่ตอน map ข้อมูลต้องระวัง

## Resolved

- **`REC` prefix** — import ปกติโดยไม่มี `SnPrefix.REC` entry (warranty คืน `None`, `pm_responsibility()` คืน `on_site` เป็น default ปลอดภัย — เครื่องกลุ่มนี้ retired แล้วจึงไม่กระทบ)

## Reference data

- `data/PASS_Inventory.xlsx` — inventory เดิม (Tablet, 2024 Q1 ถึง 2026 Q1)
  - แถวที่ 1 = legend สี (เขียว=ใหม่, ส้ม=เสื่อม, เหลือง=ยืม)
  - แถวที่ 2 = mapping prefix → ปี (RP9=2025, RPB=2023, RMA=2021, RJB=2018)
  - แถวที่ 3-4 = header ปี + Q (Q1/Q2/Q3, ไม่มี Q4)
  - คอลัมน์ A = plant (เว้นว่าง = ยึดค่าด้านบน)
  - แต่ละ Q มี 2 คอลัมน์: S/N + หมายเหตุ
  - **อ่านรายละเอียดเต็มใน `docs/01_data_understanding.md`**

## PM round calendar (ใช้ตอนสร้าง fixture)

ยึดจากแผน 2025 (วันที่ปรับต่อปีได้):
- Q1: ต้น ก.พ. – กลาง มี.ค., ปิดเอกสาร 31 มี.ค.
- Q2: ปลาย พ.ค. – กลาง ก.ค., ปิดเอกสาร 31 ก.ค.
- Q3: กลาง ก.ย. – ต้น พ.ย., ปิดเอกสาร ~21 พ.ย.
- (ไม่มี Q4) — ปลายปีลูกค้าวางบิล + ต้องล่าลายเซ็น
