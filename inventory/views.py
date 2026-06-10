from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, ListView

from .models import Device, Plant, PMSnapshot

STATUS_LABELS = dict(PMSnapshot.Status.choices)

PM_RESPONSIBILITY_LABELS = {
    "vendor": "Vendor (อยู่ในประกัน)",
    "on_site": "ทีม IT (หมดประกันแล้ว)",
}


class DeviceListView(LoginRequiredMixin, ListView):
    template_name = "inventory/device_list.html"
    context_object_name = "rows"

    def get_queryset(self):
        devices = (
            Device.objects.select_related("asset_type", "home_plant")
            .prefetch_related("pm_snapshots__plant", "pm_snapshots__pm_round")
            .order_by("serial_number")
        )

        plant_code = self.request.GET.get("plant")
        status = self.request.GET.get("status")

        rows = []
        for device in devices:
            current_plant = device.current_plant
            current_status = device.current_status

            if plant_code and (not current_plant or current_plant.code != plant_code):
                continue
            if status and current_status != status:
                continue

            responsibility = device.pm_responsibility()
            rows.append({
                "device": device,
                "current_plant": current_plant,
                "current_status": current_status,
                "current_status_label": STATUS_LABELS.get(current_status, "—"),
                "warranty_end": device.warranty_end_date,
                "pm_responsibility_label": PM_RESPONSIBILITY_LABELS.get(responsibility, "—"),
            })
        return rows

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["plants"] = Plant.objects.filter(is_active=True)
        ctx["statuses"] = PMSnapshot.Status.choices
        ctx["selected_plant"] = self.request.GET.get("plant", "")
        ctx["selected_status"] = self.request.GET.get("status", "")
        return ctx


class DeviceDetailView(LoginRequiredMixin, DetailView):
    model = Device
    context_object_name = "device"
    template_name = "inventory/device_detail.html"

    def get_queryset(self):
        return Device.objects.select_related(
            "asset_type", "home_plant", "received_round",
            "replaced_predecessor", "replaced_by",
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        snapshots = (
            self.object.pm_snapshots
            .select_related("plant", "pm_round")
            .order_by("pm_round__year", "pm_round__quarter")
        )
        ctx["snapshots"] = [
            {"snapshot": s, "status_label": STATUS_LABELS.get(s.status, "—")}
            for s in snapshots
        ]
        ctx["current_plant"] = self.object.current_plant
        ctx["warranty_end"] = self.object.warranty_end_date
        ctx["pm_responsibility_label"] = PM_RESPONSIBILITY_LABELS.get(
            self.object.pm_responsibility(), "—"
        )
        return ctx
