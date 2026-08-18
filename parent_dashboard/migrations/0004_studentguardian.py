from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('parent_dashboard', '0003_alter_parent_phone_alter_parent_students'),
        ('student_profile', '0003_student_admission_profile_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentGuardian',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('relationship', models.CharField(max_length=40)),
                ('is_primary', models.BooleanField(default=False)),
                ('portal_access', models.BooleanField(default=True)),
                ('notifications_enabled', models.BooleanField(default=True)),
                ('parent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='guardian_links', to='parent_dashboard.parent')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='guardian_links', to='student_profile.student')),
            ],
        ),
        migrations.AddConstraint(
            model_name='studentguardian',
            constraint=models.UniqueConstraint(fields=('parent', 'student'), name='unique_parent_student_guardian'),
        ),
        migrations.AddConstraint(
            model_name='studentguardian',
            constraint=models.UniqueConstraint(condition=models.Q(('is_primary', True)), fields=('student',), name='one_primary_guardian_per_student'),
        ),
    ]
