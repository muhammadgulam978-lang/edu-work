from concurrent.futures import ThreadPoolExecutor

from django.db import close_old_connections, transaction

from student_profile.models import Student as PortalStudent
from teacher_dashboard.models import Teacher as PortalTeacher

from .models import AutomationJob, SalaryVoucher
from .progress import AutomationProgressService


# One bounded worker keeps PDF/database-heavy automation from exhausting the web process.
_AUTOMATION_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix='edupilot-automation')


def _submit(run, worker, *args, **kwargs):
    def execute():
        close_old_connections()
        try:
            AutomationProgressService.start(run.id)
            worker(*args, progress_run_id=run.id, **kwargs)
        except Exception as exc:
            AutomationProgressService.fail(run.id, exc)
        finally:
            close_old_connections()

    transaction.on_commit(lambda: _AUTOMATION_EXECUTOR.submit(execute))
    return run


def start_fee_generation(month_name, year, job_type='MANUAL_GENERATION'):
    from .services import FeeGenerationService

    total = PortalStudent.objects.count()
    job = AutomationJob.objects.create(job_type=job_type, status='PENDING')
    run = AutomationProgressService.create_run(
        'FEE_GENERATION',
        f'Fee vouchers for {month_name} {year}',
        total,
        {'month': month_name, 'year': year, 'automation_job_id': job.id},
    )
    return _submit(run, FeeGenerationService.generate_monthly_fees, month_name, year, job_id=job.id)


def start_salary_generation(month_name, year):
    from .services import SalaryAutomationService

    total = 1 if SalaryVoucher.objects.filter(month=month_name, year=year).exists() else PortalTeacher.objects.filter(status='active').count()
    run = AutomationProgressService.create_run(
        'SALARY_GENERATION',
        f'Salary vouchers for {month_name} {year}',
        total,
        {'month': month_name, 'year': year},
    )
    return _submit(run, SalaryAutomationService.generate_salaries, month_name, year)


def start_notification_dispatch():
    from .models import NotificationQueue
    from .services import NotificationDispatcherService

    total = NotificationQueue.objects.filter(status='PENDING').count()
    run = AutomationProgressService.create_run(
        'NOTIFICATION_DISPATCH',
        'Pending notification delivery',
        total,
        {'channels': ['SMS', 'EMAIL']},
    )
    return _submit(run, NotificationDispatcherService.send_pending_notifications)
