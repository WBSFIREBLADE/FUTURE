# Generated migration for TableSchema and updated Upload models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('upload', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TableSchema',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('table_name', models.CharField(max_length=255, unique=True)),
                ('schema', models.JSONField()),
                ('column_names', models.JSONField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='table_schemas', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddField(
            model_name='upload',
            name='schema',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='upload',
            name='rows_inserted',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='upload',
            name='table_schema',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='uploads', to='upload.tableschema'),
        ),
    ]
