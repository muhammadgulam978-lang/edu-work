
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from django.utils import timezone
from .automation_runner import start_fee_generation, start_notification_dispatch, start_salary_generation
from .models import FeeGenerationSettings, SalaryAutomationSettings
from .email_delivery import kick_email_dispatch

def run_scheduled_job():
    settings_obj = FeeGenerationSettings.objects.first()
    if settings_obj and settings_obj.auto_enabled:
        now = timezone.now()
        start_fee_generation(now.strftime("%B"), now.year, job_type='AUTO_GENERATION')

def check_and_run_job():
    settings_obj = FeeGenerationSettings.objects.first()
    if settings_obj and settings_obj.auto_enabled:
        now = timezone.now()
        if now.day == settings_obj.generation_day and \
           now.hour == settings_obj.generation_time.hour and \
           now.minute == settings_obj.generation_time.minute:
            run_scheduled_job()
           
def check_salary_job():
    settings_obj = SalaryAutomationSettings.objects.first()
    if settings_obj and settings_obj.auto_enabled:
        now = timezone.now()
        if now.day == settings_obj.generation_day and \
        now.hour == settings_obj.generation_time.hour and \
        now.minute == settings_obj.generation_time.minute :
         start_salary_generation(now.strftime("%B"), now.year)

def start():
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")
    
    # 1. Fee Generation Job (Har 1 minute)
    scheduler.add_job(
        check_and_run_job, 
        'interval', 
        minutes=1, 
        id="check_fee_generation_job", 
        replace_existing=True
    )

    # 2. Salary Automation Job (Har 1 minute)
    scheduler.add_job(
        check_salary_job, 
        'interval', 
        minutes=1, 
        id="check_salary_generation_job", 
        replace_existing=True
    )

    # 3. SMS Dispatcher Job (Har 5 minute)
    scheduler.add_job(
        start_notification_dispatch,
        'interval', 
        minutes=5, 
        id="sms_dispatcher_job", 
        replace_existing=True
    )

    scheduler.add_job(
        kick_email_dispatch,
        'interval',
        minutes=1,
        id='email_outbox_dispatcher',
        replace_existing=True,
    )
    
    scheduler.start()
