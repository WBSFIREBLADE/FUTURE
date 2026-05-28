from rest_framework import serializers
from .models import Upload

class UploadSerializer(serializers.ModelSerializer):

    class Meta:
        model = Upload
        fields = ["id", "user", "upload_file", "original_filename", "is_valid", "uploaded_at"]
        read_only_fields = ["user", "original_filename", "is_valid", "uploaded_at"]

    # Function 1 — check file extension
    def validate_upload_file(self, value):
        allowed_extensions = [".xlsx"]
        if not any(value.name.lower().endswith(ext) for ext in allowed_extensions):
            raise serializers.ValidationError("Only .xlsx files are supported at this time.")
        return value

    # Function 2 — save with auto-filled fields
    def create(self, validated_data):
        file = validated_data.get("upload_file")
        validated_data["original_filename"] = file.name  # "employees.xlsx"
        validated_data["user"] = self.context["request"].user
        validated_data["is_valid"] = True
        return super().create(validated_data)