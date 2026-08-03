
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from .models import (
    Student, StudentFeeAssignment, FeeVoucher, FeeVoucherItem, 
    FeePlanDetail, StudentBalance, NotificationQueue, FeeGenerationLog,
    AutomationJob, AutomationJobDetail, Teacher, SalaryVoucher, SalaryStructure,
    SalaryAutomationJob, SalaryAutomationJobDetail, FeeGenerationSettings,
    Announcement, AnnouncementNotification, AnnouncementRead
)
from student_profile.models import Student as PortalStudent
from teacher_dashboard.models import Teacher as PortalTeacher
from .canonical_sync import ensure_legacy_student, ensure_legacy_teacher
from .progress import AutomationProgressService
from reportlab.pdfgen import canvas
from django.conf import settings
import os
from datetime import datetime, timedelta
from decimal import Decimal

def money(value):
    if value in (None, ''):
        return Decimal('0')
    return Decimal(str(value))


class AnnouncementService:
    @staticmethod
    def get_target_recipients(audience, target_class=None):
        from django.contrib.auth.models import User
        if audience == 'ADMINS':
            return User.objects.filter(is_active=True, is_staff=True)
        if audience == 'STUDENTS':
            return User.objects.filter(is_active=True, student__isnull=False)
        if audience == 'TEACHERS':
            return User.objects.filter(is_active=True, teacher__isnull=False)
        if audience == 'PARENTS':
            return User.objects.filter(is_active=True, parent__isnull=False)
        if audience == 'CLASS' and target_class:
            return User.objects.filter(is_active=True, student__class_fk=target_class)
        return User.objects.filter(is_active=True)

    @staticmethod
    def create_announcement(*, created_by, cleaned_data):
        now = timezone.now()
        publish_date = cleaned_data.get('publish_date') or now
        status = 'SCHEDULED' if publish_date > now else 'PUBLISHED'
        announcement = Announcement.objects.create(created_by=created_by, status=status, **cleaned_data)
        recipients = AnnouncementService.get_target_recipients(
            announcement.audience, announcement.target_class
        ).distinct()
        announcement.total_intended_recipients = recipients.count()
        announcement.save(update_fields=['total_intended_recipients', 'updated_at'])
        if status == 'PUBLISHED':
            AnnouncementNotification.objects.bulk_create([
                AnnouncementNotification(announcement=announcement, user=user, status='SENT', sent_at=now)
                for user in recipients
            ], ignore_conflicts=True)
        return announcement

    @staticmethod
    def publish_due_announcements():
        now = timezone.now()
        due = Announcement.objects.filter(status='SCHEDULED', publish_date__lte=now)
        for announcement in due.select_related('target_class'):
            recipients = AnnouncementService.get_target_recipients(
                announcement.audience, announcement.target_class
            ).distinct()
            AnnouncementNotification.objects.bulk_create([
                AnnouncementNotification(
                    announcement=announcement,
                    user=user,
                    status='SENT',
                    sent_at=now,
                )
                for user in recipients
            ], ignore_conflicts=True)
            announcement.status = 'PUBLISHED'
            announcement.total_intended_recipients = recipients.count()
            announcement.save(update_fields=['status', 'total_intended_recipients', 'updated_at'])

    @staticmethod
    def visible_for_user(user):
        AnnouncementService.publish_due_announcements()
        now = timezone.now()
        audience_filter = Q(audience='ALL')

        if user.is_staff:
            audience_filter |= Q(audience='ADMINS')

        student = getattr(user, 'student', None)
        if student is not None:
            audience_filter |= Q(audience='STUDENTS')
            if student.class_fk_id:
                audience_filter |= Q(audience='CLASS', target_class_id=student.class_fk_id)

        if getattr(user, 'teacher', None) is not None:
            audience_filter |= Q(audience='TEACHERS')

        if getattr(user, 'parent', None) is not None:
            audience_filter |= Q(audience='PARENTS')

        return Announcement.objects.filter(
            audience_filter,
            status='PUBLISHED',
            publish_date__lte=now,
        ).filter(
            Q(expiry_date__isnull=True) | Q(expiry_date__gt=now)
        ).select_related('created_by', 'target_class')

    @staticmethod
    def mark_read(announcement, user):
        _, created = AnnouncementRead.objects.get_or_create(
            announcement=announcement,
            user=user,
        )
        if created:
            Announcement.objects.filter(pk=announcement.pk).update(view_count=F('view_count') + 1)
        return created

class PDFGeneratorService:
    @staticmethod
    def generate_voucher_pdf(voucher):
        folder_path = os.path.join(settings.MEDIA_ROOT, 'vouchers')
        if not os.path.exists(folder_path): os.makedirs(folder_path)
        file_path = os.path.join(folder_path, f"voucher_{voucher.voucher_no}.pdf")
        c = canvas.Canvas(file_path)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 800, "SCHOOL FEE VOUCHER")
        c.setFont("Helvetica", 12)
        c.drawString(100, 770, f"Voucher No: {voucher.voucher_no}")
        student_name = voucher.canonical_student.name if voucher.canonical_student_id else voucher.student.full_name
        c.drawString(100, 750, f"Student: {student_name}")
        c.drawString(100, 730, f"Month: {voucher.month}")
        c.drawString(100, 710, f"Issue Date: {voucher.issue_date}")
        c.drawString(100, 690, f"Due Date: {voucher.due_date}")
        c.drawString(100, 670, f"Gross Amount: {voucher.gross_amount}")
        c.drawString(100, 650, f"Discount: {voucher.discount}")
        c.drawString(100, 630, f"Previous Due: {voucher.previous_due}")
        c.drawString(100, 610, f"NET PAYABLE: {voucher.net_amount}")
        c.save()
        return file_path

class SalaryPDFGeneratorService:
    @staticmethod
    def generate_salary_pdf(voucher):
        try:
            folder_path = os.path.join(settings.MEDIA_ROOT, 'salary_vouchers')
            if not os.path.exists(folder_path): os.makedirs(folder_path)
            teacher_id = voucher.teacher.teacher_id
            file_path = os.path.join(folder_path, f"salary_{teacher_id}_{voucher.month}_{voucher.year}.pdf")
            c = canvas.Canvas(file_path)
            c.setFont("Helvetica-Bold", 16)
            c.drawString(100, 800, "TEACHER SALARY VOUCHER")
            c.setFont("Helvetica", 12)
            teacher_name = voucher.canonical_teacher.name if voucher.canonical_teacher_id else voucher.teacher.name
            c.drawString(100, 770, f"Teacher: {teacher_name}")
            c.drawString(100, 750, f"Month: {voucher.month} - {voucher.year}")
            c.drawString(100, 730, f"Net Salary: {voucher.net_salary}")
            c.save()
            return file_path
        except Exception as e:
            print(f"CRITICAL ERROR: {e}")
            return None

class NotificationService:
    @staticmethod
    def queue_notifications(voucher):
        content = f"Dear Parent, Fee Voucher {voucher.voucher_no} for {voucher.month} is generated. Amount: {voucher.net_amount}. Due by {voucher.due_date}."
        NotificationQueue.objects.create(
            student=voucher.student,
            canonical_student=voucher.canonical_student,
            notification_type='SMS', 
            content=content, 
            status='PENDING'
        )

class NotificationDispatcherService:
    @staticmethod
    def send_pending_notifications(progress_run_id=None):
        notifications = NotificationQueue.objects.filter(status='PENDING').select_related(
            'student', 'teacher', 'canonical_student', 'canonical_teacher'
        )
        for notif in notifications:
            recipient = notif.canonical_student or notif.student or notif.canonical_teacher or notif.teacher
            recipient_name = getattr(recipient, 'name', None) or getattr(recipient, 'full_name', None) or 'Unassigned recipient'
            recipient_identifier = (
                getattr(recipient, 'student_id', None) or getattr(recipient, 'admission_number', None) or
                getattr(recipient, 'teacher_id', None) or ''
            )
            if progress_run_id:
                AutomationProgressService.set_current(
                    progress_run_id, recipient_name, recipient_identifier,
                    status='PROCESSING', channel=notif.notification_type,
                )
            try:
                print(f"--- Sending SMS to {notif.student}: {notif.content} ---")
                notif.status = 'SENT'
                notif.save(update_fields=['status'])
                if progress_run_id:
                    AutomationProgressService.record(
                        progress_run_id, recipient_name, recipient_identifier,
                        status='SENT', channel=notif.notification_type,
                        message='Notification sent.',
                    )
            except Exception as e:
                notif.status = 'FAILED'
                notif.save(update_fields=['status'])
                if progress_run_id:
                    AutomationProgressService.record(
                        progress_run_id, recipient_name, recipient_identifier,
                        status='FAILED', channel=notif.notification_type,
                        message=str(e),
                    )
        if progress_run_id:
            AutomationProgressService.complete(progress_run_id)

class FeeGenerationService:
    @staticmethod
    def generate_monthly_fees(month_name, year, job_id=None, progress_run_id=None):
        """
        Generate monthly fee vouchers for all active students
        """
        print(f"\n{'='*60}")
        print(f"FEE GENERATION STARTED: {month_name}-{year}")
        print(f"{'='*60}\n")
        
        log = FeeGenerationLog.objects.create(month=month_name, year=year, status='Running')
        job = AutomationJob.objects.filter(id=job_id).first() if job_id else None
        
        if job: 
            job.status = 'RUNNING'
            job.save()

        success_count = 0
        failed_count = 0
        
        # Get all active students
        students = PortalStudent.objects.select_related('user', 'class_fk').all()
        print(f"Total Active Students: {students.count()}\n")

        for canonical_student in students:
            student_name = canonical_student.name
            student_identifier = canonical_student.student_id
            if progress_run_id:
                AutomationProgressService.set_current(
                    progress_run_id, student_name, student_identifier, status='PROCESSING'
                )
            try:
                student = ensure_legacy_student(canonical_student)
                # ✅ CHECK 1: Prevent duplicate vouchers
                existing = FeeVoucher.objects.filter(
                    month=month_name,
                    year=year,
                ).filter(
                    Q(canonical_student=canonical_student) | Q(student=student)
                ).exists()
                
                if existing:
                    print(f"SKIP: {student.full_name} - Voucher already exists")
                    if progress_run_id:
                        AutomationProgressService.record(
                            progress_run_id, student_name, student_identifier,
                            status='SKIPPED', message='Voucher already exists for this period.',
                        )
                    continue
                
                # ✅ CHECK 2: Get fee assignment
                assignment = StudentFeeAssignment.objects.filter(
                    canonical_student=canonical_student
                ).first() or StudentFeeAssignment.objects.filter(student=student).first()
                if not assignment:
                    raise Exception(f"No fee assignment found")
                
                # ✅ CHECK 3: Get fee plan items
                plan_items = FeePlanDetail.objects.filter(fee_plan=assignment.fee_plan)
                if not plan_items.exists():
                    raise Exception(f"No fee heads in plan")
                
                # ✅ CALCULATE: Gross Amount
                gross = sum((money(item.amount) for item in plan_items), Decimal('0'))
                
                # ✅ ADD: Transport fee if assigned
                if assignment.transport_route:
                    gross += money(assignment.transport_route.amount)

                # ✅ GET: Previous outstanding
                balance_obj, _ = StudentBalance.objects.get_or_create(
                    student=student,
                    defaults={'canonical_student': canonical_student},
                )
                if not balance_obj.canonical_student_id:
                    balance_obj.canonical_student = canonical_student
                    balance_obj.save(update_fields=['canonical_student'])
                prev_due = money(balance_obj.outstanding_amount)
                
                # ✅ CALCULATE: Discount (scholarship)
                discount = Decimal('0')
                if assignment.scholarship:
                    if assignment.scholarship.discount_type == 'percentage':
                        discount = (gross * money(assignment.scholarship.value)) / Decimal('100')
                    else:
                        discount = money(assignment.scholarship.value)
                
                # ✅ FINAL: Net Amount
                net_amount = gross + prev_due - discount
                
                # ✅ DATES
                now = datetime.now()
                issue_date = now.date()
                due_date = issue_date + timedelta(days=15)
                
                # ✅ CREATE VOUCHER (with ALL fields)
                with transaction.atomic():
                    voucher = FeeVoucher.objects.create(
                        voucher_no=f"V-{student.admission_number}-{month_name}-{year}",
                        student=student,
                        canonical_student=canonical_student,
                        month=month_name,
                        year=year,
                        issue_date=issue_date,
                        due_date=due_date,
                        gross_amount=gross,
                        discount=discount,
                        fine=Decimal('0'),
                        previous_due=prev_due,
                        net_amount=net_amount,
                        status='UNPAID'
                    )
                    
                    # Add fee line items
                    for item in plan_items:
                        FeeVoucherItem.objects.create(
                            voucher=voucher,
                            fee_head=item.fee_head,
                            amount=item.amount
                        )
                    
                    # Add transport item if applicable
                    if assignment.transport_route:
                        from .models import FeeHead
                        transport_head, _ = FeeHead.objects.get_or_create(
                            name='Transport',
                            defaults={'frequency': 'monthly', 'status': True}
                        )
                        FeeVoucherItem.objects.create(
                            voucher=voucher,
                            fee_head=transport_head,
                            amount=assignment.transport_route.amount
                        )
                    
                    # Generate PDF
                    PDFGeneratorService.generate_voucher_pdf(voucher)
                    
                    # Queue SMS/Email notification
                    fee_settings = FeeGenerationSettings.objects.first()
                    if not fee_settings or fee_settings.send_notifications:
                        NotificationService.queue_notifications(voucher)
                    
                    # Log success
                    if job:
                        AutomationJobDetail.objects.create(
                            job=job,
                            student=student,
                            canonical_student=canonical_student,
                            status='SUCCESS'
                        )
                    
                    success_count += 1
                    print(f"SUCCESS: {student.full_name}: Rs.{net_amount} (Voucher: {voucher.voucher_no})")
                    if progress_run_id:
                        AutomationProgressService.record(
                            progress_run_id, student_name, student_identifier,
                            status='COMPLETED', message=f'Voucher {voucher.voucher_no} generated.',
                        )
                    
            except Exception as e:
                failed_count += 1
                error_msg = str(e)
                print(f"FAILED: {student.full_name}: {error_msg}")
                
                if job:
                    AutomationJobDetail.objects.create(
                        job=job,
                        student=student,
                        canonical_student=canonical_student,
                        status='FAILED',
                        error_message=error_msg
                    )
                if progress_run_id:
                    AutomationProgressService.record(
                        progress_run_id, student_name, student_identifier,
                        status='FAILED', message=error_msg,
                    )
        
        # ✅ FINALIZE LOG
        log.status = 'Completed'
        log.students_processed = success_count + failed_count
        log.success_count = success_count
        log.failed_count = failed_count
        log.completed_at = timezone.now()
        log.save()
        
        # ✅ FINALIZE JOB
        if job:
            job.status = 'COMPLETED'
            job.processed_count = success_count + failed_count
            job.success_count = success_count
            job.failed_count = failed_count
            job.completed_at = timezone.now()
            job.save()

        if progress_run_id:
            AutomationProgressService.complete(progress_run_id)
        
        print(f"\n{'='*60}")
        print(f"COMPLETED: {success_count} Success | {failed_count} Failed")
        print(f"{'='*60}\n")
        
        return success_count

    @staticmethod
    def retry_failed_records(job_id, month, year):
        """Retry failed voucher generations"""
        job = AutomationJob.objects.get(id=job_id)
        failed_details = AutomationJobDetail.objects.filter(job=job, status='FAILED')
        
        for detail in failed_details:
            try:
                # Retry logic
                assignment = None
                if detail.canonical_student_id:
                    assignment = StudentFeeAssignment.objects.filter(
                        canonical_student=detail.canonical_student
                    ).first()
                assignment = assignment or StudentFeeAssignment.objects.filter(
                    student=detail.student
                ).first()
                if not assignment:
                    raise Exception("No fee assignment")
                                                         
                plan_items = FeePlanDetail.objects.filter(fee_plan=assignment.fee_plan)
                existing = FeeVoucher.objects.filter(
                    student=detail.student,
                    month=month,
                    year=year
                ).exists()
                if existing:
                    detail.status = 'SUCCESS'
                    detail.error_message = 'Voucher already exists'
                    detail.save()
                    continue

                gross = sum((money(item.amount) for item in plan_items), Decimal('0'))
                if assignment.transport_route:
                    gross += money(assignment.transport_route.amount)

                balance_obj, _ = StudentBalance.objects.get_or_create(student=detail.student)
                prev_due = money(balance_obj.outstanding_amount)

                discount = Decimal('0')
                if assignment.scholarship:
                    if assignment.scholarship.discount_type == 'percentage':
                        discount = (gross * money(assignment.scholarship.value)) / Decimal('100')
                    else:
                        discount = money(assignment.scholarship.value)

                net_amount = gross + prev_due - discount
                
                voucher = FeeVoucher.objects.create(
                    voucher_no=f"V-{detail.student.admission_number}-{month}-{year}",
                    student=detail.student,
                    canonical_student=detail.canonical_student or detail.student.canonical_student,
                    month=month,
                    year=year,
                    issue_date=datetime.now().date(),
                    due_date=datetime.now().date() + timedelta(days=15),
                    gross_amount=gross,
                    discount=discount,
                    fine=Decimal('0'),
                    previous_due=prev_due,
                    net_amount=net_amount,
                    status='UNPAID'
                )
                
                for item in plan_items:
                    FeeVoucherItem.objects.create(voucher=voucher, fee_head=item.fee_head, amount=item.amount)

                if assignment.transport_route:
                    from .models import FeeHead
                    transport_head, _ = FeeHead.objects.get_or_create(
                        name='Transport',
                        defaults={'frequency': 'monthly', 'status': True}
                    )
                    FeeVoucherItem.objects.create(
                        voucher=voucher,
                        fee_head=transport_head,
                        amount=assignment.transport_route.amount
                    )

                PDFGeneratorService.generate_voucher_pdf(voucher)

                fee_settings = FeeGenerationSettings.objects.first()
                if not fee_settings or fee_settings.send_notifications:
                    NotificationService.queue_notifications(voucher)
                
                detail.status = 'SUCCESS'
                detail.error_message = None
                detail.save()
            except Exception as e:
                detail.error_message = str(e)
                detail.save()

class SalaryAutomationService:
    @staticmethod
    def generate_salaries(month=None, year=None, progress_run_id=None):
        month = month or datetime.now().strftime("%B")
        year = year or datetime.now().year

        # Duplicate Protection
        if SalaryVoucher.objects.filter(month=month, year=year).exists():
            print("SKIP: Salary already generated for this month")
            if progress_run_id:
                AutomationProgressService.record(
                    progress_run_id, 'Salary generation', f'{month} {year}', status='SKIPPED',
                    message='Salary vouchers already exist for this period.',
                )
                AutomationProgressService.complete(progress_run_id)
            return

        job = SalaryAutomationJob.objects.create(status='RUNNING')
        teachers = PortalTeacher.objects.filter(status='active').select_related('user', 'employee')
        
        for canonical_teacher in teachers:
            teacher_name = canonical_teacher.name
            teacher_identifier = canonical_teacher.email or ''
            if progress_run_id:
                AutomationProgressService.set_current(
                    progress_run_id, teacher_name, teacher_identifier, status='PROCESSING'
                )
            teacher = None
            try:
                teacher = ensure_legacy_teacher(canonical_teacher)
                # Calculate total earnings
                earnings = money(teacher.basic_salary) + \
                          money(teacher.house_allowance) + \
                          money(teacher.medical_allowance) + \
                          money(teacher.transport_allowance) + \
                          money(teacher.utility_allowance) + \
                          money(teacher.special_allowance) + \
                          money(teacher.overtime)
                
                # Get deductions
                deductions = SalaryStructure.objects.filter(
                    canonical_teacher=canonical_teacher
                ).values_list('deductions', flat=True).first()
                if deductions is None:
                    deductions = SalaryStructure.objects.filter(
                        teacher=teacher
                    ).values_list('deductions', flat=True).first() or 0
                net_salary = earnings - money(deductions)

                # Create voucher
                voucher = SalaryVoucher.objects.create(
                    teacher=teacher,
                    canonical_teacher=canonical_teacher,
                    month=month,
                    year=year,
                    net_salary=net_salary,
                    status='UNPAID'
                )

                SalaryPDFGeneratorService.generate_salary_pdf(voucher)
                job.success_count += 1
                print(f"SUCCESS: {teacher.name}: Rs.{net_salary}")
                if progress_run_id:
                    AutomationProgressService.record(
                        progress_run_id, teacher_name, teacher_identifier,
                        status='COMPLETED', message=f'Salary voucher generated for {month} {year}.',
                    )
                
            except Exception as e:
                job.failed_count += 1
                if teacher:
                    SalaryAutomationJobDetail.objects.create(
                        job=job,
                        teacher=teacher,
                        canonical_teacher=canonical_teacher,
                        status='FAILED',
                        error_message=str(e)
                    )
                print(f"FAILED: {teacher_name}: {str(e)}")
                if progress_run_id:
                    AutomationProgressService.record(
                        progress_run_id, teacher_name, teacher_identifier,
                        status='FAILED', message=str(e),
                    )
        
        job.status = 'COMPLETED'
        job.completed_at = timezone.now()
        job.save()

        if progress_run_id:
            AutomationProgressService.complete(progress_run_id)
        
        print(f"Salary generation: {job.success_count} success, {job.failed_count} failed")
from edupilot_core.models import Fixture, Absence, Period, Teacher, NotificationQueue

class FixtureAutomationService:
    @staticmethod
    def auto_assign_fixture(absence_id):
        absence = Absence.objects.get(id=absence_id)
        period = absence.period
        
        # Find replacement teacher with same subject
        replacement = Teacher.objects.filter(
            is_active=True
        ).exclude(id=absence.teacher.id).first()
        
        if replacement:
            fixture = Fixture.objects.create(
                absent_teacher=absence.teacher,
                replacement_teacher=replacement,
                period=period,
                fixture_date=absence.absence_date,
                status='PENDING'
            )
            
            # Send notification
            msg = f"Cover Class {period.class_name}, Period {period.period_number} for {absence.teacher.name}"
            NotificationQueue.objects.create(
                content=msg,
                notification_type='SMS',
                status='PENDING'
            )
            
            return fixture
        return None
