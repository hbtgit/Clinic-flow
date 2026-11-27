from rest_framework import serializers

from .models import Practitioner, Service


class PractitionerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Practitioner
        fields = ["id", "display_name", "title", "is_active", "user"]

    def validate_user(self, user):
        if user and user.clinic_id != self.context["request"].user.clinic_id:
            raise serializers.ValidationError("That staff account is not in this clinic.")
        return user


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["id", "name", "duration_minutes", "is_active"]
