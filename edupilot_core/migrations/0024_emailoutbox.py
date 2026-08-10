from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('edupilot_core', '0023_portalnotification_voucherdelivery')]

    operations = [
        migrations.CreateModel(
            name='EmailOutbox',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recipient', models.EmailField(max_length=254)),
                ('subject', models.CharField(max_length=255)),
                ('body', models.TextField()),
                ('attachment_path', models.CharField(blank=True, max_length=500)),
                ('dedupe_key', models.CharField(max_length=180, unique=True)),
                ('sensitive', models.BooleanField(default=False)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('SENDING', 'Sending'), ('SENT', 'Sent'), ('FAILED', 'Failed')], default='PENDING', max_length=10)),
                ('attempts', models.PositiveSmallIntegerField(default=0)),
                ('last_error', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'ordering': ['created_at'],
                'indexes': [models.Index(fields=['status', 'created_at'], name='email_outbox_pending_idx')],
            },
        ),
    ]
