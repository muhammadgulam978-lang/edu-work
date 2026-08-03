# Generated manually for the reusable automation progress tracker.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('edupilot_core', '0021_announcement_announcementnotification_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='AutomationProgressRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('task_type', models.CharField(max_length=60)),
                ('label', models.CharField(max_length=160)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('RUNNING', 'Running'), ('COMPLETED', 'Completed'), ('COMPLETED_WITH_ERRORS', 'Completed with errors'), ('FAILED', 'Failed')], default='PENDING', max_length=30)),
                ('total_items', models.PositiveIntegerField(default=0)),
                ('processed_items', models.PositiveIntegerField(default=0)),
                ('successful_items', models.PositiveIntegerField(default=0)),
                ('failed_items', models.PositiveIntegerField(default=0)),
                ('skipped_items', models.PositiveIntegerField(default=0)),
                ('current_name', models.CharField(blank=True, max_length=255)),
                ('current_identifier', models.CharField(blank=True, max_length=100)),
                ('current_channel', models.CharField(blank=True, max_length=30)),
                ('current_status', models.CharField(blank=True, max_length=30)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('error_message', models.TextField(blank=True)),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={'ordering': ['-started_at']},
        ),
        migrations.CreateModel(
            name='AutomationProgressEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sequence', models.PositiveIntegerField()),
                ('item_name', models.CharField(max_length=255)),
                ('item_identifier', models.CharField(blank=True, max_length=100)),
                ('channel', models.CharField(blank=True, max_length=30)),
                ('status', models.CharField(max_length=30)),
                ('message', models.TextField(blank=True)),
                ('occurred_at', models.DateTimeField(auto_now_add=True)),
                ('run', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='events', to='edupilot_core.automationprogressrun')),
            ],
            options={'ordering': ['-sequence']},
        ),
        migrations.AddIndex(
            model_name='automationprogressrun',
            index=models.Index(fields=['task_type', 'status'], name='edupilot_co_task_ty_65d9aa_idx'),
        ),
        migrations.AddIndex(
            model_name='automationprogressrun',
            index=models.Index(fields=['-started_at'], name='edupilot_co_started_964c6a_idx'),
        ),
        migrations.AddIndex(
            model_name='automationprogressevent',
            index=models.Index(fields=['run', '-sequence'], name='edupilot_co_run_id_93138b_idx'),
        ),
        migrations.AddConstraint(
            model_name='automationprogressevent',
            constraint=models.UniqueConstraint(fields=('run', 'sequence'), name='unique_automation_progress_event_sequence'),
        ),
    ]
