# PASS Inventory — Setup Guide (v1)

> เอกสารต่อจาก `02_schema_design.md` — วิธีลง Django project และใช้ `models.py` + `admin.py` ที่ส่งให้

## สิ่งที่ต้องเตรียม
- Python 3.10+
- pip (มาพร้อม Python)

## Setup ทีละขั้น

### 1. สร้าง virtual environment + ติดตั้ง dependencies

```bash
python -m venv venv

# Activate
source venv/bin/activate           # macOS / Linux
.\venv\Scripts\activate            # Windows PowerShell

pip install "django>=5.0,<6.0" python-dateutil
```

### 2. สร้าง Django project + app

```bash
django-admin startproject pass_inventory .
python manage.py startapp inventory
```

ตอนนี้จะได้โครงสร้าง:
```
.
├── manage.py
├── pass_inventory/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
└── inventory/
    ├── __init__.py
    ├── admin.py        ← จะแทนด้วยของเรา
    ├── apps.py
    ├── models.py       ← จะแทนด้วยของเรา
    └── migrations/
```

### 3. ลงไฟล์ที่ให้

แทนที่:
- `inventory/models.py` ← `models.py` ที่ส่งให้
- `inventory/admin.py` ← `admin.py` ที่ส่งให้

### 4. เพิ่ม `inventory` เข้า `INSTALLED_APPS`

ใน `pass_inventory/settings.py` หา `INSTALLED_APPS` แล้วเพิ่มบรรทัด:

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "inventory",                    # ← เพิ่มบรรทัดนี้
]
```

ตั้ง `TIME_ZONE` และ `LANGUAGE_CODE` ให้เหมาะกับไทย:
```python
LANGUAGE_CODE = "th"
TIME_ZONE = "Asia/Bangkok"
USE_TZ = True
```

### 5. Migrate + สร้าง admin user

```bash
python manage.py makemigrations inventory
python manage.py migrate
python manage.py createsuperuser
```

### 6. รัน server

```bash
python manage.py runserver
```

เปิด http://localhost:8000/admin/ → login → จะเห็น 7 ตารางใน section "Inventory" พร้อมใช้

---

## โครงสร้างไฟล์หลังลงเสร็จ

```
.
├── manage.py
├── pass_inventory/             ← Django project settings
│   ├── settings.py
│   └── urls.py
├── inventory/                  ← app หลัก
│   ├── models.py               ← schema 7 ตาราง
│   ├── admin.py                ← Django Admin สำหรับ Role support
│   └── migrations/
│       └── 0001_initial.py     ← auto-generated
└── db.sqlite3                  ← database (เกิดจาก migrate)
```

---

## สิ่งที่ verify แล้ว (ในแซนด์บ็อกซ์)

- `python manage.py check` ผ่าน (ไม่มี error)
- `makemigrations` รู้จัก 7 ตารางครบ ลำดับการสร้างถูก (master → core → snapshot)
- ทดสอบสร้าง Device + PMSnapshot ด้วย scenario จริง (replacement, borrow) → computed property + query ทำงานถูกตาม spec

---

## TODO ที่ยังค้าง (ตามที่คุยกัน)

- [ ] **Plant codes** — ตอนนี้ใช้ placeholder (`PKT`, `HDY`, `KBV`, `URT`, `UTP`, `UDT`, `CNX`) แทนที่ด้วย code จริงทีหลัง
- [ ] **`REC` prefix** — ยังไม่ทราบปี ตอนเพิ่ม fixture เครื่อง REC ต้องระบุก่อน
- [ ] **Chain borrow** ในข้อมูลเก่า — ตอน migrate Excel → DB ต้องเช็คเคสนี้แยก

---

## ขั้นถัดไป (3 ทางเลือก)

หลังจาก setup เสร็จและรัน Django Admin ดูได้ ขั้นถัดไปมี 3 ทาง แล้วแต่อยากเริ่มทางไหนก่อน:

| ทางเลือก | ทำอะไร | ใช้ทำอะไรต่อ |
|---|---|---|
| **A. Fixture + Excel import** | เขียน script อ่าน `PASS_Inventory.xlsx` แล้ว populate DB | เห็นข้อมูลจริงในระบบ ทดสอบ query/view ได้ |
| **B. Customer read-only view** | สร้างหน้าเว็บแบบ table + filter สำหรับ OR ดู | ลูกค้าใช้งานได้เร็วที่สุด |
| **C. Groups + permissions** | สร้าง 3 groups + กำหนดสิทธิ์ Django | พร้อมรับ user หลายคน |

ผมแนะนำ **A → B → C** เพราะ:
1. มีข้อมูลก่อน จะทดสอบ B และ C ง่ายกว่ามาก
2. ตอน import จะได้ค้น edge case ของข้อมูลเดิม (เช่น chain borrow) เจอเร็ว

แต่ถ้าอยาก demo ให้ใครเห็นเร็ว ๆ B ก่อนก็ได้
