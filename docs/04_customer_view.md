# 04 — Customer Read-only View (Phase B)

## สิ่งที่สร้าง

- `/devices/` — รายการอุปกรณ์ทั้งหมด พร้อม filter ตาม plant ปัจจุบัน และสถานะล่าสุด
  - คอลัมน์: S/N, ชนิด, plant เจ้าของ (home plant), plant ปัจจุบัน, สถานะล่าสุด, วันหมดประกัน, ใคร PM
- `/devices/<id>/` — รายละเอียดเครื่อง + ประวัติ PM ทุกรอบ (ตอบ Q1 ใน `02_schema_design.md`)
- `/` redirect ไป `/devices/`

ใช้ Django generic class-based views (`ListView`, `DetailView`) + template ธรรมดา ไม่มี JS framework

## Auth — ใช้ระบบ login เดิมของ Django Admin

`LoginRequiredMixin` + `LOGIN_URL = "/admin/login/"` (ใน `pass_inventory/settings.py`)

**ข้อควรระวังสำหรับ Phase C (Groups + Permissions):**

`AdminAuthenticationForm` (หน้า login ของ `/admin/`) เช็คว่า `user.is_staff == True`
ก่อนจะ login ผ่าน — ถ้า user ไม่ได้ตั้ง `is_staff=True` จะ login ไม่ได้เลย แม้ username/password ถูก

ดังนั้น user กลุ่ม **customer** (OR, read-only) ก็ต้องตั้ง `is_staff=True` ด้วย
เพื่อให้ผ่านหน้า login ได้ — แต่**ไม่ต้องให้ permission อะไรใน admin**
(ถ้าไม่มี permission เลย `/admin/` จะโชว์หน้าว่าง ซึ่งไม่เป็นไรเพราะ
หลัง login จะ redirect ไป `/devices/` อยู่แล้วผ่าน `?next=`)

สรุป: `is_staff=True` ในระบบนี้ไม่ได้แปลว่า "เป็นเจ้าหน้าที่" แค่แปลว่า "login ผ่านหน้า admin ได้"
ตัว permission จริงควบคุมด้วย Django Groups (Phase C) แยกต่างหาก

ถ้าในอนาคตอยากแยกหน้า login ของ customer ออกจาก admin จริง ๆ
ค่อยทำ custom login view ทีหลังได้ — ไม่ใช่เรื่องด่วน

## Filter logic

- Filter "plant ปัจจุบัน" ใช้ computed property `Device.current_plant`
  (มาจาก `PMSnapshot` ล่าสุด ไม่ใช่ `home_plant`) — เพื่อตอบคำถาม
  "ตอนนี้มีเครื่องอะไรอยู่ที่ plant ไหนบ้าง" ซึ่งสำคัญกว่า "ใครเป็นเจ้าของ"
- Filtering ทำใน Python (ไม่ใช่ DB query) เพราะ `current_plant`/`current_status`
  เป็น computed property — กับข้อมูลขนาด ~50 เครื่องไม่มีปัญหา performance
  ถ้าข้อมูลโตมากในอนาคตค่อยพิจารณา denormalize

## Verified

- `python manage.py check` ผ่าน
- ทดสอบผ่าน temp user (`is_staff=True`, ลบทิ้งหลังทดสอบแล้ว):
  - login → redirect `/devices/` (48 เครื่อง)
  - filter ตาม plant และ status ทำงานถูกต้อง
  - device detail แสดง borrow scenario ถูกต้อง (เช่น RJB03F0086: home=KBV, current=PKT)
  - replacement link (`replaced_by`/`replaced_predecessor`) ทำงานถูกต้อง
  - logout (POST + CSRF) ทำงานถูกต้อง — Django 5 ไม่รับ GET logout แล้ว
