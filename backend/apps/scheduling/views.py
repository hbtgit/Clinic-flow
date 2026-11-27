from apps.core.permissions import MANAGERS, roles_can_write
from apps.core.viewsets import ClinicScopedViewSet

from .models import Practitioner, Service
from .serializers import PractitionerSerializer, ServiceSerializer


class PractitionerViewSet(ClinicScopedViewSet):
    queryset = Practitioner.objects.all()
    serializer_class = PractitionerSerializer
    permission_classes = [roles_can_write(*MANAGERS)]


class ServiceViewSet(ClinicScopedViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [roles_can_write(*MANAGERS)]
