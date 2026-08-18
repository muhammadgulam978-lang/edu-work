from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('admin_panel', '0043_dutyevent_teacherduty_event'),
        ('parent_dashboard', '0004_studentguardian'),
        ('student_profile', '0003_student_admission_profile_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentAdmissionWorkflow',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('DRAFT', 'Draft'), ('PENDING', 'Pending Review'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')], default='DRAFT', max_length=12)),
                ('current_step', models.PositiveSmallIntegerField(default=1)),
                ('payload', models.JSONField(blank=True, default=dict)),
                ('student_username', models.CharField(blank=True, max_length=150)),
                ('student_password_hash', models.CharField(blank=True, max_length=128)),
                ('completeness', models.PositiveSmallIntegerField(default=0)),
                ('rejection_reason', models.TextField(blank=True)),
                ('last_error', models.TextField(blank=True)),
                ('initial_voucher_pk', models.PositiveBigIntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('submitted_at', models.DateTimeField(blank=True, null=True)),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                ('enrolled_at', models.DateTimeField(blank=True, null=True)),
                ('admission', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='enrollment_workflow', to='admin_panel.admission')),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_admission_workflows', to=settings.AUTH_USER_MODEL)),
                ('canonical_student', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='admission_workflow', to='student_profile.student')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_admission_workflows', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='updated_admission_workflows', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-updated_at']},
        ),
        migrations.CreateModel(
            name='AdmissionGuardian',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_name', models.CharField(max_length=100)),
                ('relationship', models.CharField(max_length=40)),
                ('cnic', models.CharField(blank=True, max_length=20)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('occupation', models.CharField(blank=True, max_length=100)),
                ('address', models.TextField(blank=True)),
                ('is_primary', models.BooleanField(default=False)),
                ('portal_access', models.BooleanField(default=True)),
                ('notifications_enabled', models.BooleanField(default=True)),
                ('username', models.CharField(blank=True, max_length=150)),
                ('password_hash', models.CharField(blank=True, max_length=128)),
                ('existing_parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='admission_guardian_drafts', to='parent_dashboard.parent')),
                ('workflow', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='guardians', to='admin_panel.studentadmissionworkflow')),
            ],
        ),
        migrations.CreateModel(
            name='AdmissionDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('document_type', models.CharField(choices=[('B_FORM', 'B-Form'), ('BIRTH_CERTIFICATE', 'Birth Certificate'), ('GUARDIAN_CNIC', 'Guardian CNIC'), ('PREVIOUS_REPORT', 'Previous School Report'), ('TRANSFER_CERTIFICATE', 'Transfer Certificate'), ('OTHER', 'Other')], max_length=30)),
                ('file', models.FileField(upload_to='admission_documents/%Y/%m/')),
                ('document_number', models.CharField(blank=True, max_length=60)),
                ('is_required', models.BooleanField(default=False)),
                ('verified', models.BooleanField(default=False)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('canonical_student', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='admission_documents', to='student_profile.student')),
                ('uploaded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('workflow', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='admin_panel.studentadmissionworkflow')),
            ],
        ),
        migrations.AddConstraint(
            model_name='admissiondocument',
            constraint=models.UniqueConstraint(fields=('workflow', 'document_type'), name='unique_workflow_document_type'),
        ),
    ]
