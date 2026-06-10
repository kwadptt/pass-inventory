from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("devices/", views.DeviceListView.as_view(), name="device_list"),
    path("devices/<int:pk>/", views.DeviceDetailView.as_view(), name="device_detail"),
]
