from django.db import models

class TimestampedModel(models.Model):
    """Abstract model with common timestamp fields."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)  # For soft deletion

    class Meta:
        abstract = True  # No table will be created for this model
