"""
PASS Inventory — Django Admin (v1)

ลงทะเบียน 7 ตารางใน Django Admin เพื่อให้ทีม support กรอกข้อมูลได้ทันที
"""

from django.contrib import admin

from .models import (
    Plant, AssetType, PMRound, SnPrefix,
    Device, PMSnapshot, PlantRoundNote,
)


@admin.register(Plant)
class PlantAdmin(admin.ModelAdmin):
    list_display = ("code", "name_th", "name_en", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name_th", "name_en")
    ordering = ("code",)


@admin.register(AssetType)
class AssetTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "default_warranty_months")
    search_fields = ("code", "name")


@admin.register(PMRound)
class PMRoundAdmin(admin.ModelAdmin):
    list_display = (
        "year", "quarter",
        "field_start_date", "field_end_date", "document_due_date",
    )
    list_filter = ("year", "quarter")
    ordering = ("-year", "quarter")


@admin.register(SnPrefix)
class SnPrefixAdmin(admin.ModelAdmin):
    list_display = ("prefix", "year")
    search_fields = ("prefix",)


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = (
        "serial_number", "asset_type", "home_plant",
        "current_plant_display", "warranty_end_display",
        "pm_responsibility_display", "is_active_display",
    )
    list_filter = ("asset_type", "home_plant", "is_retired")
    search_fields = ("serial_number", "notes")
    raw_id_fields = ("replaced_predecessor",)
    readonly_fields = (
        "warranty_start_display", "warranty_end_display",
        "pm_responsibility_display", "current_plant_display",
        "created_at", "updated_at",
    )
    fieldsets = (
        ("ข้อมูลเครื่อง", {
            "fields": ("serial_number", "asset_type", "home_plant", "notes"),
        }),
        ("การรับเครื่อง / ประกัน", {
            "fields": ("received_round", "warranty_months_override", "replaced_predecessor"),
        }),
        ("เลิกใช้งาน", {
            "fields": ("is_retired", "retired_round"),
        }),
        ("Derived (อ่านอย่างเดียว)", {
            "fields": (
                "warranty_start_display", "warranty_end_display",
                "pm_responsibility_display", "current_plant_display",
            ),
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    # ─── Derived field display methods ─────────────────────────────────────
    @admin.display(description="In Service", boolean=True)
    def is_active_display(self, obj):
        return not obj.is_retired

    @admin.display(description="Plant ปัจจุบัน")
    def current_plant_display(self, obj):
        return obj.current_plant or "—"

    @admin.display(description="เริ่มประกัน")
    def warranty_start_display(self, obj):
        return obj.warranty_start_date or "—"

    @admin.display(description="หมดประกัน")
    def warranty_end_display(self, obj):
        return obj.warranty_end_date or "—"

    @admin.display(description="ใคร PM")
    def pm_responsibility_display(self, obj):
        return obj.pm_responsibility()


@admin.register(PMSnapshot)
class PMSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "device", "pm_round", "plant", "status",
        "is_borrowed_display", "recorded_at",
    )
    list_filter = (
        "pm_round__year", "pm_round__quarter",
        "plant", "status",
    )
    search_fields = ("device__serial_number", "note")
    autocomplete_fields = ("device",)
    readonly_fields = ("recorded_at",)

    @admin.display(description="เป็นการยืม", boolean=True)
    def is_borrowed_display(self, obj):
        return obj.is_borrowed_situation


@admin.register(PlantRoundNote)
class PlantRoundNoteAdmin(admin.ModelAdmin):
    list_display = ("plant", "pm_round", "recorded_at")
    list_filter = ("pm_round__year", "plant")
    readonly_fields = ("recorded_at",)
