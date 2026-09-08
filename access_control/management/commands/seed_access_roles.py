from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from access_control.models import Institution, RoleDefinition, RoleGrant

ROLES = [
    'SIS Platform Administrator', 'Institution Super Admin', 'Institution Admin',
    'Principal', 'Academic Head', 'HOD', 'Teacher', 'Student', 'Parent',
    'Admissions Officer', 'Examination Controller', 'Invigilator', 'Finance Officer',
    'HR and Payroll Officer', 'Librarian', 'Laboratory Manager', 'Health Officer',
    'Procurement Officer', 'Transport Manager', 'Auditor', 'Support Engineer', 'Reception',
]

# Explicit resource grants. Absent resources/actions remain denied.
TEMPLATES = {
    'Librarian': {'school_operations.librarybook': ('view', 'create', 'edit'),
                  'school_operations.libraryloan': ('view', 'create', 'edit'),
                  'student_profile.student': ('view',)},
    'Laboratory Manager': {'school_operations.labasset': ('view', 'create', 'edit'),
                           'school_operations.labbooking': ('view', 'create', 'edit', 'approve')},
    'Health Officer': {'school_operations.healthcase': ('view', 'create', 'edit'),
                       'student_profile.student': ('view',)},
    'Finance Officer': {'edupilot_core.feevoucher': ('view', 'create', 'edit', 'submit', 'export'),
                        'edupilot_core.studentledger': ('view', 'export')},
    'HR and Payroll Officer': {'admin_panel.employee': ('view', 'create', 'edit', 'submit'),
                              'edupilot_core.salaryvoucher': ('view', 'create', 'submit')},
    'Teacher': {'teacher_dashboard.attendance': ('view', 'create', 'edit'),
                'teacher_dashboard.assignment': ('view', 'create', 'edit', 'submit'),
                'exam_system.generatedpaper': ('view', 'create', 'edit', 'submit')},
    'HOD': {'exam_system.generatedpaper': ('view', 'review', 'approve')},
    'Examination Controller': {'exam_system.generatedpaper': ('view', 'review', 'publish', 'export'),
                               'exam_system.centralizedresult': ('view', 'publish')},
    'Principal': {'edupilot_core.feevoucher': ('view', 'approve'),
                  'edupilot_core.salaryvoucher': ('view', 'approve'),
                  'exam_system.centralizedresult': ('view', 'approve'),
                  'admin_panel.purchaserequest': ('view', 'approve')},
    'Admissions Officer': {'admin_panel.admission': ('view', 'create', 'edit', 'submit')},
    'Procurement Officer': {'admin_panel.purchaserequest': ('view', 'create', 'edit', 'submit')},
    'Transport Manager': {'admin_panel.transporttrip': ('view', 'create', 'edit'),
                          'admin_panel.vehicle': ('view', 'create', 'edit')},
    'Parent': {'student_profile.student': ('view',), 'edupilot_core.feevoucher': ('view', 'export')},
    'Student': {'student_profile.student': ('view',), 'edupilot_core.feevoucher': ('view', 'export')},
}


class Command(BaseCommand):
    help = 'Seed conservative role definitions for an existing institution; does not grant user access.'

    def add_arguments(self, parser):
        parser.add_argument('--institution', required=True, type=int)

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            institution = Institution.objects.get(pk=options['institution'])
        except Institution.DoesNotExist:
            raise CommandError('Create and verify the institution before seeding roles.')
        for name in ROLES:
            role, _ = RoleDefinition.objects.get_or_create(institution=institution, name=name,
                                                           defaults={'system': True, 'requires_mfa': name in {
                                                               'Health Officer', 'Finance Officer', 'HR and Payroll Officer',
                                                               'Institution Super Admin', 'SIS Platform Administrator'}})
            for resource, actions in TEMPLATES.get(name, {}).items():
                for action in actions:
                    RoleGrant.objects.get_or_create(role=role, resource=resource, action=action)
        self.stdout.write('Role definitions created. Missing capabilities remain denied; assign reviewed scopes explicitly.')
