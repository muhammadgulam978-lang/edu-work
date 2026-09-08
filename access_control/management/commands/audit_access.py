"""Read-only identity/relationship audit. Never fixes claims by guessing a role."""
import json

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.core.management.base import BaseCommand

from access_control.identity import effective_role


class Command(BaseCommand):
    help = 'Report conflicting identities and unverified guardian relationships without changing data.'

    def handle(self, *args, **options):
        from parent_dashboard.models import StudentGuardian, Parent
        conflicts, unassigned = [], []
        for user in get_user_model().objects.filter(is_active=True).iterator():
            try:
                if not effective_role(user):
                    unassigned.append(user.pk)
            except PermissionDenied:
                conflicts.append(user.pk)
        pending = list(StudentGuardian.objects.filter(verified_at__isnull=True).values_list('pk', flat=True))
        legacy = []
        for parent in Parent.objects.prefetch_related('students'):
            linked = set(parent.guardian_links.values_list('student_id', flat=True))
            legacy.extend({'parent_id': parent.pk, 'student_id': s.pk} for s in parent.students.all() if s.pk not in linked)
        self.stdout.write(json.dumps({'role_conflicts': conflicts, 'unassigned_accounts': unassigned,
                                      'unverified_guardian_links': pending, 'legacy_links_to_reconcile': legacy}, indent=2))
