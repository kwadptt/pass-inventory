"""
PASS Inventory — Django Models (v1)

Schema นี้ implement ตาม spec ใน `02_schema_design.md`
- ลูกค้าเดียว (OR) → ไม่มี customer_id ในตารางใด ๆ
- Device-centric: ยึด serial_number เป็นหลัก
- Borrow modeled เป็น status ใน PMSnapshot ไม่ใช่ตารางแยก
- Warranty เป็น computed property ไม่เก็บใน DB
"""

from datetime import date

from django.conf import settings
from django.db import models
from django.utils import timezone


# ─────────────────────────────────────────────────────────────────────────────
# Master / Reference tables
# ─────────────────────────────────────────────────────────────────────────────

class Plant(models.Model):
    """plant ทั้ง 7 แห่งของ OR (ภูเก็ต, หาดใหญ่, กระบี่, ...)"""

    code = models.CharField(max_length=8, unique=True, help_text="รหัสย่อ plant (placeholder ก่อน — ใช้ของจริงทีหลัง)")
    name_th = models.CharField(max_length=64)
    name_en = models.CharField(max_length=64, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} ({self.name_th})"


class AssetType(models.Model):
    """ชนิดอุปกรณ์ — เริ่มจาก Tablet, ขยายเพิ่ม UPS/Scanner/... ได้"""

    code = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=64)
    default_warranty_months = models.PositiveIntegerField(
        default=12,
        help_text="อายุประกัน default สำหรับชนิดนี้ (เดือน)",
    )
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.name


class PMRound(models.Model):
    """ปฏิทินรอบ PM ต่อปี — แต่ละ row คือ 1 รอบ (year + quarter)"""

    class Quarter(models.TextChoices):
        Q1 = "Q1", "Q1 (ก.พ.–มี.ค.)"
        Q2 = "Q2", "Q2 (พ.ค.–ก.ค.)"
        Q3 = "Q3", "Q3 (ก.ย.–พ.ย.)"

    year = models.PositiveIntegerField()
    quarter = models.CharField(max_length=2, choices=Quarter.choices)
    field_start_date = models.DateField(help_text="วันเริ่มงานภาคสนาม")
    field_end_date = models.DateField(help_text="วันจบงานภาคสนาม")
    document_due_date = models.DateField(help_text="กำหนดส่งเอกสาร — ใช้เป็น warranty anchor")

    class Meta:
        ordering = ["year", "quarter"]
        constraints = [
            models.UniqueConstraint(
                fields=["year", "quarter"],
                name="unique_pmround_year_quarter",
            ),
        ]

    def __str__(self):
        return f"{self.year} {self.quarter}"

    def next_round(self):
        """หา PMRound ถัดไป (Q ถัดไปในปีเดียวกัน หรือ Q1 ของปีถัดไป)"""
        return (
            PMRound.objects
            .filter(field_start_date__gt=self.field_start_date)
            .order_by("field_start_date")
            .first()
        )


class SnPrefix(models.Model):
    """Map prefix S/N → ปี ใช้เป็น fallback สำหรับเครื่องที่ไม่มี received_round บันทึก"""

    prefix = models.CharField(max_length=8, primary_key=True)
    year = models.PositiveIntegerField()
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["prefix"]

    def __str__(self):
        return f"{self.prefix} → {self.year}"


# ─────────────────────────────────────────────────────────────────────────────
# Core tables
# ─────────────────────────────────────────────────────────────────────────────

class Device(models.Model):
    """ตัวเครื่อง — entity หลักของระบบ"""

    serial_number = models.CharField(max_length=32, unique=True)
    asset_type = models.ForeignKey(
        AssetType, on_delete=models.PROTECT,
        related_name="devices",
    )
    home_plant = models.ForeignKey(
        Plant, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="owned_devices",
        help_text="plant เจ้าของ (null ได้ถ้า legacy ไม่ทราบ)",
    )
    received_round = models.ForeignKey(
        PMRound, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="received_devices",
        help_text="รอบที่รับเครื่อง (null = legacy ก่อนระบบ → ใช้ SnPrefix.year เป็น fallback)",
    )
    warranty_months_override = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="ถ้าไม่ใส่ ใช้ default ของ asset_type",
    )
    is_retired = models.BooleanField(default=False, db_index=True)
    retired_round = models.ForeignKey(
        PMRound, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="retired_devices",
    )
    replaced_predecessor = models.OneToOneField(
        "self", on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="replaced_by",
        help_text="เครื่องเก่าที่ถูกเครื่องนี้แทน",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["serial_number"]

    def __str__(self):
        return self.serial_number

    # ── Computed properties ─────────────────────────────────────────────────
    @property
    def prefix(self):
        return self.serial_number[:3]

    @property
    def warranty_months(self):
        return self.warranty_months_override or self.asset_type.default_warranty_months

    @property
    def warranty_start_date(self):
        """วันเริ่มประกัน = document_due_date ของรอบที่รับ
        ถ้าไม่มี received_round (legacy) ใช้ SnPrefix.year (สมมติ Q1)"""
        if self.received_round:
            return self.received_round.document_due_date

        # Legacy fallback: ใช้ปีจาก prefix mapping
        try:
            sn_prefix = SnPrefix.objects.get(prefix=self.prefix)
        except SnPrefix.DoesNotExist:
            return None

        q1 = PMRound.objects.filter(year=sn_prefix.year, quarter="Q1").first()
        if q1:
            return q1.document_due_date
        # ถ้าไม่มี PMRound ของปีนั้นในระบบ ใช้ 31 มี.ค. ของปีนั้นเป็น default
        return date(sn_prefix.year, 3, 31)

    @property
    def warranty_end_date(self):
        from dateutil.relativedelta import relativedelta
        start = self.warranty_start_date
        if not start:
            return None
        return start + relativedelta(months=self.warranty_months)

    def pm_responsibility(self, as_of_round=None):
        """vendor ถ้า warranty คุ้มถึงวันเริ่มรอบ PM ถัดไป มิฉะนั้น on_site

        Args:
            as_of_round: รอบที่อยากเช็ค (default = รอบ PM ถัดไปจากวันนี้)
        Returns:
            "vendor" | "on_site"
        """
        end = self.warranty_end_date
        if not end:
            return "on_site"  # ไม่ทราบ warranty = ถือว่าเป็นภาระทีม

        if as_of_round is None:
            today = timezone.now().date()
            as_of_round = (
                PMRound.objects
                .filter(field_start_date__gte=today)
                .order_by("field_start_date")
                .first()
            )
            if not as_of_round:
                return "on_site"  # ไม่มีรอบในอนาคต

        return "vendor" if end >= as_of_round.field_start_date else "on_site"

    @property
    def current_snapshot(self):
        """PMSnapshot ล่าสุดของเครื่องนี้"""
        return (
            self.pm_snapshots
            .order_by("-pm_round__year", "-pm_round__quarter")
            .first()
        )

    @property
    def current_plant(self):
        snap = self.current_snapshot
        return snap.plant if snap else self.home_plant

    @property
    def current_status(self):
        snap = self.current_snapshot
        return snap.status if snap else None


class PMSnapshot(models.Model):
    """บันทึก 1 row ต่อ (device, pm_round) — เก็บ status + note ของรอบนั้น
    ลำดับ snapshot ของเครื่อง = timeline ของมัน
    """

    class Status(models.TextChoices):
        IN_USE = "in_use", "ใช้งานปกติ"
        NEW_DELIVERY = "new_delivery", "รับเครื่องใหม่"
        RETIRED = "retired", "เสื่อมสภาพ/คืน Enco"
        BORROWED_IN = "borrowed_in", "ยืมเข้ามาใช้"
        LOANED_OUT = "loaned_out", "ถูกยืมออกไป"
        CORRECTION = "correction", "แก้ไขข้อมูล"

    device = models.ForeignKey(
        Device, on_delete=models.CASCADE,
        related_name="pm_snapshots",
    )
    pm_round = models.ForeignKey(
        PMRound, on_delete=models.PROTECT,
        related_name="snapshots",
    )
    plant = models.ForeignKey(
        Plant, on_delete=models.PROTECT,
        related_name="hosted_snapshots",
        help_text="plant ที่เครื่องอยู่ในรอบนี้ (อาจ ≠ home_plant กรณีถูกยืม)",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.IN_USE,
    )
    note = models.TextField(blank=True, help_text="ข้อความหมายเหตุดิบ")
    checklist_results = models.JSONField(
        null=True, blank=True,
        help_text="ขยายสำหรับ Role inspector (future)",
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-pm_round__year", "-pm_round__quarter", "plant__code", "device__serial_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["device", "pm_round"],
                name="unique_snapshot_per_device_round",
            ),
        ]
        indexes = [
            models.Index(fields=["pm_round", "plant"]),
            models.Index(fields=["device", "pm_round"]),
        ]

    def __str__(self):
        return f"{self.device.serial_number} @ {self.plant.code} ({self.pm_round})"

    @property
    def is_borrowed_situation(self):
        """plant ปัจจุบัน ≠ home_plant = situation ของการยืม"""
        if not self.device.home_plant_id:
            return False
        return self.plant_id != self.device.home_plant_id


# ─────────────────────────────────────────────────────────────────────────────
# Auxiliary
# ─────────────────────────────────────────────────────────────────────────────

class PlantRoundNote(models.Model):
    """โน้ตระดับ plant + รอบ ที่ไม่ผูกกับเครื่องตัวใดตัวหนึ่ง
    (เช่น 'เปลี่ยน UPS 2 Plug 2' ที่ merge หลายแถวในไฟล์เดิม)"""

    plant = models.ForeignKey(
        Plant, on_delete=models.PROTECT,
        related_name="round_notes",
    )
    pm_round = models.ForeignKey(
        PMRound, on_delete=models.PROTECT,
        related_name="plant_notes",
    )
    note = models.TextField()
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["plant", "pm_round"],
                name="unique_plantroundnote",
            ),
        ]

    def __str__(self):
        return f"Note {self.plant.code} {self.pm_round}"
