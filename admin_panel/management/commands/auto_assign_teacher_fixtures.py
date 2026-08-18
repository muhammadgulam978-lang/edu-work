from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from admin_panel.models import TeacherAbsence
from admin_panel.services import FixtureAutomationService
from teacher_dashboard.models import Teacher


class Command(BaseCommand):
    help = 'Automatically assign substitute fixtures for absent teachers on a date.'

    def add_arguments(self, parser):
        parser.add_argument('--date', required=True, help='Absence date in YYYY-MM-DD format.')
        parser.add_argument('--teacher-id', type=int, help='Run for one absent teacher id. If omitted, retries recorded absences for the date.')

    def handle(self, *args, **options):
        try:
            target_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
        except ValueError as exc:
            raise CommandError('Use --date in YYYY-MM-DD format.') from exc

        if options.get('teacher_id'):
            teachers = Teacher.objects.filter(status='active', id=options['teacher_id'])
            if not teachers.exists():
                raise CommandError('No matching active teacher found.')
            absence_inputs = [{'teacher': teacher, 'source': 'manual', 'leave_application': None} for teacher in teachers]
        else:
            absences = TeacherAbsence.objects.filter(absence_date=target_date).select_related('teacher', 'leave_application')
            if not absences.exists():
                raise CommandError('No recorded teacher absences found for this date. Pass --teacher-id to run for one teacher.')
            absence_inputs = [
                {
                    'teacher': absence.teacher,
                    'source': 'auto_leave' if absence.source == 'leave' else 'manual',
                    'leave_application': absence.leave_application,
                }
                for absence in absences
            ]

        total_assigned = 0
        total_unassigned = 0
        total_skipped = 0

        for item in absence_inputs:
            teacher = item['teacher']
            result = FixtureAutomationService.run_for_absence(
                teacher=teacher,
                target_date=target_date,
                source=item['source'],
                leave_application=item['leave_application'],
            )
            assigned = len(result.get('assigned', []))
            unassigned = len(result.get('unassigned', []))
            skipped = len(result.get('skipped', []))
            total_assigned += assigned
            total_unassigned += unassigned
            total_skipped += skipped
            self.stdout.write(
                f'{teacher.name}: {assigned} assigned, {unassigned} unassigned, {skipped} skipped'
            )

        self.stdout.write(self.style.SUCCESS(
            f'Completed: {total_assigned} assigned, {total_unassigned} unassigned, {total_skipped} skipped'
        ))
