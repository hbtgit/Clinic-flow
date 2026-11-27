from rest_framework import viewsets

from .audit import record
from .permissions import IsClinicStaff


class ClinicScopedViewSet(viewsets.ModelViewSet):
    """Every query is limited to the signed-in user's clinic, and new records are stamped with it.

    Looking up another clinic's record by ID returns 404, so IDs reveal nothing (FR-001).
    """

    permission_classes = [IsClinicStaff]
    audit_writes = True

    def get_queryset(self):
        return super().get_queryset().filter(clinic_id=self.request.user.clinic_id)

    def perform_create(self, serializer):
        obj = serializer.save(clinic_id=self.request.user.clinic_id)
        if self.audit_writes:
            record(self.request, f"{obj._meta.model_name}.create", target=obj)

    def perform_update(self, serializer):
        obj = serializer.save()
        if self.audit_writes:
            record(
                self.request,
                f"{obj._meta.model_name}.update",
                target=obj,
                fields=sorted(serializer.validated_data),
            )

    def perform_destroy(self, instance):
        if self.audit_writes:
            record(self.request, f"{instance._meta.model_name}.delete", target=instance)
        instance.delete()
