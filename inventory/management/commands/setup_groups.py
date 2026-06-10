"""
สร้าง/อัปเดต Django Groups สำหรับ 3 roles: support, inspector, customer

Re-run ได้เรื่อยๆ (idempotent) — ใช้ตอน deploy ครั้งแรก หรือถ้าเพิ่ม model ใหม่ทีหลัง
แล้วอยากให้ permission อัปเดตตาม
"""

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from inventory.models import (
    AssetType, Device, Plant, PlantRoundNote, PMRound, PMSnapshot, SnPrefix,
)

# Groups ที่ได้ view + add + change บนทุก model ของ inventory app
# (ไม่มี delete — กันลบ history โดยไม่ตั้งใจ ถ้าต้องลบจริงให้ superuser ทำ)
WRITE_GROUPS = ["support", "inspector"]

INVENTORY_MODELS = [
    AssetType, Plant, PMRound, SnPrefix, Device, PMSnapshot, PlantRoundNote,
]

WRITE_ACTIONS = ["view", "add", "change"]


class Command(BaseCommand):
    help = "สร้าง/อัปเดต Groups: support, inspector (write), customer (read-only, no admin permission)"

    def handle(self, *args, **options):
        write_permissions = self._collect_permissions(INVENTORY_MODELS, WRITE_ACTIONS)

        for group_name in WRITE_GROUPS:
            group, created = Group.objects.get_or_create(name=group_name)
            group.permissions.set(write_permissions)
            status = "created" if created else "updated"
            self.stdout.write(self.style.SUCCESS(
                f"{status}: '{group_name}' — {len(write_permissions)} permissions "
                f"(view/add/change x {len(INVENTORY_MODELS)} models)"
            ))

        # customer: group ว่าง — ไม่มี permission ใน admin
        # (read-only ผ่าน /devices/ เท่านั้น, login ได้ต้องตั้ง is_staff=True เอง — ดู docs/04)
        customer_group, created = Group.objects.get_or_create(name="customer")
        customer_group.permissions.clear()
        status = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(f"{status}: 'customer' — 0 permissions (read-only via /devices/)"))

    def _collect_permissions(self, models, actions):
        permissions = []
        for model in models:
            content_type = ContentType.objects.get_for_model(model)
            for action in actions:
                codename = f"{action}_{model._meta.model_name}"
                try:
                    permissions.append(Permission.objects.get(content_type=content_type, codename=codename))
                except Permission.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"Permission not found: {codename} ({model._meta.model_name})"))
        return permissions
