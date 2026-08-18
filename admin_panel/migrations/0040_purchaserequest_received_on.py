from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("admin_panel", "0039_transporttrip"),
    ]

    operations = [
        migrations.AddField(
            model_name="purchaserequest",
            name="received_on",
            field=models.DateField(blank=True, null=True),
        ),
    ]
