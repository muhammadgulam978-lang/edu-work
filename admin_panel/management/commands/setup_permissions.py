import os, re
from django.core.management.base import BaseCommand
from admin_panel.models import Permission

class Command(BaseCommand):
    help = "Scan all views for @role_required decorators and auto-create missing permissions."

    def handle(self, *args, **kwargs):
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        pattern = re.compile(r"@role_required\(['\"]([\w_]+)['\"]\)")
        created = 0
        existing = 0

        print(f"🔍 Scanning for @role_required(...) in {project_root}")

        for root, _, files in os.walk(project_root):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        matches = pattern.findall(content)
                        for code in matches:
                            perm, is_created = Permission.objects.get_or_create(
                                code=code,
                                defaults={'name': code.replace('_', ' ').title()}
                            )
                            if is_created:
                                created += 1
                                print(f"✅ Created: {code}")
                            else:
                                existing += 1

        print(f"\n🎯 Sync Complete — {created} new, {existing} already existed.")
