from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import CsrfView, LoginView, LogoutView, MeView
from apps.core.views import health
from apps.scheduling.views import (
    AppointmentViewSet,
    PractitionerViewSet,
    ServiceViewSet,
    TimeOffViewSet,
    WorkingHoursViewSet,
)

router = DefaultRouter()
router.register("practitioners", PractitionerViewSet)
router.register("services", ServiceViewSet)
router.register("working-hours", WorkingHoursViewSet)
router.register("time-off", TimeOffViewSet)
router.register("appointments", AppointmentViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health),
    path("api/auth/csrf/", CsrfView.as_view()),
    path("api/auth/login/", LoginView.as_view()),
    path("api/auth/logout/", LogoutView.as_view()),
    path("api/auth/me/", MeView.as_view()),
    path("api/", include(router.urls)),
]
