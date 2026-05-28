from django.db import models
from django.contrib.auth.models import User
import json

class TableSchema(models.Model):
    """Stores metadata about dynamically created tables"""
    user = models.ForeignKey(User, related_name="table_schemas", on_delete=models.CASCADE)
    table_name = models.CharField(max_length=255, unique=True)
    schema = models.JSONField()  # stores {"column_name": "DATA_TYPE"}
    column_names = models.JSONField()  # stores list of column names in order
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.table_name} (User: {self.user.username})"


class Upload(models.Model):
    user = models.ForeignKey(User, related_name="uploads", on_delete=models.CASCADE)
    upload_file = models.FileField(upload_to="uploads/%Y/%m/%d/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    original_filename = models.CharField(max_length=255, blank=True)
    is_valid = models.BooleanField(default=False)
    schema = models.JSONField(null=True, blank=True)  # stores AI-detected schema
    table_schema = models.ForeignKey(TableSchema, null=True, blank=True, on_delete=models.SET_NULL, related_name="uploads")
    rows_inserted = models.IntegerField(default=0)  # track how many rows were inserted

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.user.username} — {self.original_filename} ({self.uploaded_at:%Y-%m-%d})"