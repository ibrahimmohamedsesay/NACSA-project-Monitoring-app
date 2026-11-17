from django.db import models


class TimeStampedModel(models.Model):
    """
    Abstract base model that adds created/updated timestamps to any model
    that inherits from it. Used across every app so every record can show
    when it was created and last changed, without repeating the same two
    fields in every model.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
