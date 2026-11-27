from rest_framework import serializers

from .models import User


class MeSerializer(serializers.ModelSerializer):
    clinic_name = serializers.CharField(source="clinic.name", default=None, read_only=True)
    practitioner = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "role",
            "clinic",
            "clinic_name",
            "preferred_language",
            "practitioner",
        ]
        read_only_fields = fields

    def get_practitioner(self, user):
        """The practitioner profile linked to this account, if any."""
        practitioner = getattr(user, "practitioner", None)
        return practitioner.pk if practitioner else None
