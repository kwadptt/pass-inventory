# 05 — Roles & Permissions (Phase C)

## Groups

สร้างผ่าน management command (idempotent, run ซ้ำได้):

```
python manage.py setup_groups
```

| Group | Permission | ใช้ทำอะไร |
|---|---|---|
| `support` | `view` + `add` + `change` บนทั้ง 7 models ใน inventory app (Device, PMSnapshot, PlantRoundNote, Plant, AssetType, PMRound, SnPrefix) | ทีมกรอกข้อมูลประจำ — เพิ่ม/แก้ PM snapshot แต่ละรอบ, ปรับวันที่ PMRound ต่อปี (ตาม design decision D4) |
| `inspector` | เหมือน `support` ทุกอย่าง (ปัจจุบัน) | เผื่อ feature checklist ในอนาคต (`PMSnapshot.checklist_results`) — ตอนนี้ permission เท่า support ไปก่อน ค่อยจำกัดเมื่อ checklist UI เสร็จ |
| `customer` | ไม่มี permission ใน admin เลย | OR — ดูข้อมูลผ่าน `/devices/` (read-only view, Phase B) เท่านั้น |

**ไม่มี group ไหนมี `delete`** — ถ้าต้องลบจริงๆ (เช่น import ผิด ต้องล้างข้อมูล) ให้ superuser ทำผ่าน `/admin/` โดยตรง เหตุผล: `PMSnapshot` ผูก `CASCADE` กับ `Device` การลบโดยไม่ตั้งใจจะทำให้ history หาย

## วิธีสร้าง user ใหม่ + assign group

ทำผ่าน Django Admin โดย superuser (`nopporn.w`):

1. `/admin/auth/user/add/` → ตั้ง username + password
2. เปิด user ที่สร้าง → เลือก **Groups**:
   - ทีม IT support / field engineer → `support` (หรือ `inspector` ถ้าเป็นทีมตรวจสอบ)
   - คนของ OR → `customer`
3. **สำคัญ — ทุก user ที่จะใช้ `/devices/` ต้องติ๊ก `Staff status` ด้วย** (ไม่ว่าจะอยู่ group ไหน)
   เพราะหน้า login ของระบบใช้ `/admin/login/` ร่วมกัน ซึ่งเช็ค `is_staff=True` ก่อนเสมอ
   (รายละเอียดใน `docs/04_customer_view.md`)
   - user กลุ่ม `customer` ที่ไม่มี admin permission เลย แม้ตั้ง `is_staff=True`
     จะเข้า `/admin/` แล้วเห็นหน้าว่าง (ไม่มีตารางให้กด) — เป็นเรื่องปกติ
     เพราะ login แล้วจะถูก redirect ไป `/devices/` อยู่แล้ว
   - **อย่าติ๊ก `Superuser status`** ให้ user ปกติ — มีไว้เฉพาะ `nopporn.w`

## Verified

- รัน `setup_groups` 2 ครั้ง → ผลลัพธ์เหมือนเดิม (idempotent)
- `support` / `inspector` มี 21 permissions (view+add+change x 7 models)
- `customer` มี 0 permissions
