from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import AutomationProgressEvent, AutomationProgressRun


class AutomationProgressService:
    """Small shared API used by every automation service to expose live state."""

    FINAL_STATUSES = {'COMPLETED', 'COMPLETED_WITH_ERRORS', 'FAILED'}

    @staticmethod
    def create_run(task_type, label, total_items=0, metadata=None):
        return AutomationProgressRun.objects.create(
            task_type=task_type,
            label=label,
            total_items=max(int(total_items or 0), 0),
            metadata=metadata or {},
        )

    @staticmethod
    def start(run_id):
        AutomationProgressRun.objects.filter(id=run_id, status='PENDING').update(status='RUNNING')

    @staticmethod
    def set_current(run_id, name, identifier='', status='PROCESSING', channel=''):
        AutomationProgressRun.objects.filter(id=run_id).update(
            current_name=(name or '')[:255],
            current_identifier=(identifier or '')[:100],
            current_status=status,
            current_channel=(channel or '')[:30],
        )

    @staticmethod
    def record(run_id, name, identifier='', status='COMPLETED', channel='', message=''):
        """Persist one feed row and atomically update aggregate progress counters."""
        status = status.upper()
        with transaction.atomic():
            run = AutomationProgressRun.objects.select_for_update().get(id=run_id)
            sequence = run.processed_items + 1
            AutomationProgressEvent.objects.create(
                run=run,
                sequence=sequence,
                item_name=(name or 'Unknown record')[:255],
                item_identifier=(identifier or '')[:100],
                channel=(channel or '')[:30],
                status=status,
                message=message or '',
            )
            run.processed_items = sequence
            if status in {'COMPLETED', 'SUCCESS', 'SENT'}:
                run.successful_items += 1
            elif status == 'SKIPPED':
                run.skipped_items += 1
            else:
                run.failed_items += 1
            run.current_name = (name or '')[:255]
            run.current_identifier = (identifier or '')[:100]
            run.current_channel = (channel or '')[:30]
            run.current_status = status
            run.save(update_fields=[
                'processed_items', 'successful_items', 'failed_items', 'skipped_items',
                'current_name', 'current_identifier', 'current_channel', 'current_status', 'updated_at',
            ])

    @staticmethod
    def complete(run_id):
        run = AutomationProgressRun.objects.get(id=run_id)
        run.status = 'COMPLETED_WITH_ERRORS' if run.failed_items else 'COMPLETED'
        run.completed_at = timezone.now()
        run.save(update_fields=['status', 'completed_at', 'updated_at'])

    @staticmethod
    def fail(run_id, error_message):
        AutomationProgressRun.objects.filter(id=run_id).update(
            status='FAILED',
            error_message=str(error_message),
            completed_at=timezone.now(),
        )

    @staticmethod
    def snapshot(run_id, event_limit=60):
        run = AutomationProgressRun.objects.get(id=run_id)
        processed = run.processed_items
        total = run.total_items
        percentage = round((processed / total) * 100, 1) if total else (100 if run.status in AutomationProgressService.FINAL_STATUSES else 0)
        remaining = max(total - processed, 0)
        eta_seconds = None
        if processed and remaining and run.status == 'RUNNING':
            elapsed = max((timezone.now() - run.started_at).total_seconds(), 0)
            eta_seconds = int((elapsed / processed) * remaining)

        events = list(run.events.all()[:event_limit])
        return {
            'id': run.id,
            'task_type': run.task_type,
            'label': run.label,
            'status': run.status,
            'total_items': total,
            'processed_items': processed,
            'remaining_items': remaining,
            'successful_items': run.successful_items,
            'failed_items': run.failed_items,
            'skipped_items': run.skipped_items,
            'percentage': percentage,
            'eta_seconds': eta_seconds,
            'current': {
                'name': run.current_name,
                'identifier': run.current_identifier,
                'channel': run.current_channel,
                'status': run.current_status,
            },
            'error_message': run.error_message,
            'events': [
                {
                    'sequence': event.sequence,
                    'name': event.item_name,
                    'identifier': event.item_identifier,
                    'channel': event.channel,
                    'status': event.status,
                    'message': event.message,
                    'occurred_at': event.occurred_at.isoformat(),
                }
                for event in events
            ],
        }
