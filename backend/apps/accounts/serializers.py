from rest_framework import serializers

from .models import User


class MeSerializer(serializers.ModelSerializer):
    clinic_name = serializers.CharField(source="clinic.name", default=None, read_only=True)

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
        ]
        read_only_fields = fields
