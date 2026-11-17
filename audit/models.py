from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """
    A single audit trail entry. Deliberately has no foreign key to the
    record it describes (only a module name and record id as plain text),
    so that an audit entry survives even if the underlying record is later
    deleted — the whole point of an audit trail is that it doesn't
    disappear when the thing it describes does.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=255)
    module = models.CharField(max_length=50)
    record_id = models.CharField(max_length=50, blank=True)
    description = models.CharField(max_length=500, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["module"]),
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self):
        who = self.user if self.user else "System"
        return f"{self.timestamp:%Y-%m-%d %H:%M} — {who} — {self.action}"
