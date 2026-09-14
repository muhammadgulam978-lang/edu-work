from django.core.management.base import BaseCommand

from helpdesk.services import escalate_overdue_tickets


class Command(BaseCommand):
    help = 'Escalate open helpdesk tickets that have breached their resolution SLA.'

    def handle(self, *args, **options):
        count = escalate_overdue_tickets()
        self.stdout.write(self.style.SUCCESS(f'{count} overdue ticket(s) escalated.'))
