from django.db import migrations


def align_status(apps, schema_editor):
    year = apps.get_model('admin_panel', 'AcademicYear')
    year.objects.filter(is_active=True).update(status='active')


class Migration(migrations.Migration):
    dependencies = [('admin_panel', '0049_alter_purchaserequest_options_academicyear_ends_on_and_more')]
    operations = [migrations.RunPython(align_status, migrations.RunPython.noop)]
