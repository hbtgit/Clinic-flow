from django.db import models


class Clinic(models.Model):
    """A clinic tenant. Every clinic's data is kept apart from every other clinic's (FR-001)."""

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    phone = models.CharField(max_length=32, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
