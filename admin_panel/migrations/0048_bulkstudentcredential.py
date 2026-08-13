from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('admin_panel', '0047_alter_admissiondocument_document_type'),
        ('student_profile', '0003_student_admission_profile_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BulkStudentCredential',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('encrypted_password', models.TextField()),
                ('password_fingerprint', models.CharField(db_index=True, max_length=64, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('last_viewed_at', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='bulk_student_credentials_created', to=settings.AUTH_USER_MODEL)),
                ('student', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='bulk_credential', to='student_profile.student')),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
