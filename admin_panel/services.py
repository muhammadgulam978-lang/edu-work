from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.core.mail import send_mail
from .models import (
    Student, StudentFeeAssignment, FeeVoucher, FeeVoucherItem, 
    FeePlanDetail, StudentBalance, NotificationQueue, FeeGenerationLog,
    AutomationJob, AutomationJobDetail, Teacher, SalaryVoucher, SalaryStructure,
    SalaryAutomationJob, SalaryAutomationJobDetail, FeeGenerationSettings,
    AssignedPeriod, TeacherFixture, TeacherAbsence, TeacherAbsenceResult,
    TeacherNotification, TeacherFixtureNotificationLog, TimetableVersion,
    TeacherAvailability, TeacherTeachingEligibility, SubjectSubstitutionRule,
    TeacherFixtureCandidateLog
)
from reportlab.pdfgen import canvas
from django.conf import settings
import os
from datetime import datetime, timedelta, date as date_class
from decimal import Decimal

def money(value):
    if value in (None, ''):
        return Decimal('0')
    return Decimal(str(value))

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
        c.drawString(100, 750, f"Student: {voucher.student.full_name}")
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
            file_path = os.path.join(folder_path, f"salary_{voucher.teacher.teacher_id}_{voucher.month}_{voucher.year}.pdf")
            c = canvas.Canvas(file_path)
            c.setFont("Helvetica-Bold", 16)
            c.drawString(100, 800, "TEACHER SALARY VOUCHER")
            c.setFont("Helvetica", 12)
            c.drawString(100, 770, f"Teacher: {voucher.teacher.name}")
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
            notification_type='SMS', 
            content=content, 
            status='PENDING'
        )

class NotificationDispatcherService:
    @staticmethod
    def send_pending_notifications():
        for notif in NotificationQueue.objects.filter(status='PENDING'):
            try:
                print(f"--- Sending SMS to {notif.student}: {notif.content} ---")
                notif.status = 'SENT'
                notif.save()
            except Exception as e:
                notif.status = 'FAILED'
                notif.save()


class FixtureAutomationService:
    workload_limit = 3
    weekly_substitute_limit = 10
    confirmation_required = False

    @classmethod
    def run_for_absence(cls, teacher, target_date, source='manual', triggered_by=None, leave_application=None):
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()

        day = target_date.strftime('%A')
        workflow_steps = cls.workflow_steps()
        timetable_version = cls.resolve_timetable_version(target_date)
        link_ok, link_note = cls.validate_teacher_employee_link(teacher, allow_legacy=True)

        with transaction.atomic():
            absence = cls._get_or_create_absence(
                teacher=teacher,
                target_date=target_date,
                day=day,
                source='leave' if source == 'auto_leave' else source,
                triggered_by=triggered_by,
                leave_application=leave_application,
            )

        periods = cls.find_absent_teacher_periods(teacher, day, timetable_version)
        if not periods.exists():
            absence.status = 'failed'
            absence.save(update_fields=['status'])
            return {
                'absence': absence,
                'assigned': [],
                'unassigned': [],
                'skipped': [],
                'workflow_steps': workflow_steps,
                'message': 'No assigned periods found for this teacher on the selected day.',
            }

        assigned = []
        unassigned = []
        skipped = []

        for assigned_period in periods:
            if cls.should_skip_period_for_absence(absence, assigned_period):
                result, _ = TeacherAbsenceResult.objects.update_or_create(
                    absence=absence,
                    assigned_period=assigned_period,
                    defaults={
                        'fixture': None,
                        'status': 'skipped',
                        'note': 'Skipped due to partial-day absence window.',
                    }
                )
                skipped.append(result)
                continue

            with transaction.atomic():
                existing = cls.find_existing_fixture(target_date, assigned_period, day)
                if existing and existing.fixture_status != 'cancelled':
                    result, _ = TeacherAbsenceResult.objects.update_or_create(
                        absence=absence,
                        assigned_period=assigned_period,
                        defaults={
                            'fixture': existing,
                            'status': 'skipped',
                            'note': 'A fixture already exists for this class, section, day, period, and date.',
                            'selection_score': existing.selection_score,
                            'selection_reason': existing.selection_reason,
                            'candidate_count': existing.candidate_count,
                        }
                    )
                    skipped.append(result)
                    continue

                candidates, excluded_logs = cls.find_substitute_candidates(
                    absence=absence,
                    assigned_period=assigned_period,
                    target_date=target_date,
                    day=day,
                    absent_teacher=teacher,
                )
                selected = cls.assign_best_substitute(candidates)

                if not selected:
                    result, _ = TeacherAbsenceResult.objects.update_or_create(
                        absence=absence,
                        assigned_period=assigned_period,
                        defaults={
                            'fixture': None,
                            'status': 'unassigned',
                            'note': 'No available substitute teacher matched the subject, period, and workload rules.',
                            'selection_score': 0,
                            'selection_reason': 'No eligible substitute found.',
                            'candidate_count': len(candidates),
                        }
                    )
                    cls.record_candidate_logs(absence, result, assigned_period, excluded_logs)
                    transaction.on_commit(lambda teacher=teacher, assigned_period=assigned_period, target_date=target_date, day=day: cls.send_unassigned_notifications(
                        teacher=teacher,
                        assigned_period=assigned_period,
                        target_date=target_date,
                        day=day,
                    ))
                    cls.notify_admin_uncovered(absence, result)
                    unassigned.append(result)
                    continue

                substitute = selected['teacher']
                if not cls.recheck_candidate_available(substitute, assigned_period, target_date, day, teacher):
                    result, _ = TeacherAbsenceResult.objects.update_or_create(
                        absence=absence,
                        assigned_period=assigned_period,
                        defaults={
                            'fixture': None,
                            'status': 'unassigned',
                            'note': 'Selected substitute became unavailable during final recheck.',
                            'selection_score': selected['score'],
                            'selection_reason': 'Final availability recheck failed.',
                            'candidate_count': len(candidates),
                        }
                    )
                    cls.record_candidate_logs(absence, result, assigned_period, excluded_logs + [{
                        'teacher': substitute,
                        'decision': 'excluded',
                        'score': selected['score'],
                        'reason': 'Final availability recheck failed.',
                    }])
                    transaction.on_commit(lambda teacher=teacher, assigned_period=assigned_period, target_date=target_date, day=day: cls.send_unassigned_notifications(
                        teacher=teacher,
                        assigned_period=assigned_period,
                        target_date=target_date,
                        day=day,
                    ))
                    unassigned.append(result)
                    continue

                fixture_defaults = {
                    'absent_teacher': teacher,
                    'substitute_teacher': substitute,
                    'original_substitute_teacher': substitute,
                    'class_fk': assigned_period.class_fk,
                    'section': assigned_period.section,
                    'subject': assigned_period.subject,
                    'period': assigned_period.period,
                    'assigned_period': assigned_period,
                    'timetable_version': assigned_period.timetable_version or timetable_version,
                    'day': day,
                    'fixture_date': target_date,
                    'source': 'auto_leave' if source == 'auto_leave' else 'auto_absence',
                    'automation_status': 'assigned',
                    'fixture_status': 'assigned',
                    'assignment_mode': 'auto',
                    'automation_note': 'Automatically assigned by timetable fixture automation.',
                    'selection_score': selected['score'],
                    'selection_reason': selected['reason'],
                    'candidate_count': len(candidates),
                    'response_required': cls.confirmation_required,
                    'response_status': 'pending' if cls.confirmation_required else 'final',
                }
                fixture, created = TeacherFixture.objects.get_or_create(
                    fixture_date=target_date,
                    assigned_period=assigned_period,
                    defaults=fixture_defaults,
                )
                if not created:
                    for key, value in fixture_defaults.items():
                        setattr(fixture, key, value)
                    fixture.save()

                result, _ = TeacherAbsenceResult.objects.update_or_create(
                    absence=absence,
                    assigned_period=assigned_period,
                    defaults={
                        'fixture': fixture,
                        'status': 'assigned',
                        'note': f'Substitute assigned: {substitute.name}',
                        'selection_score': selected['score'],
                        'selection_reason': selected['reason'],
                        'candidate_count': len(candidates),
                    }
                )
                cls.record_candidate_logs(absence, result, assigned_period, excluded_logs + [
                    {
                        'teacher': item['teacher'],
                        'decision': 'selected' if item['teacher'].id == substitute.id else 'eligible',
                        'score': item['score'],
                        'reason': item['reason'],
                    }
                    for item in candidates
                ])
                transaction.on_commit(lambda fixture=fixture: cls.send_fixture_notifications(fixture))
                assigned.append(result)

        if unassigned and assigned:
            absence.status = 'partial'
        elif unassigned and not assigned:
            absence.status = 'failed'
        else:
            absence.status = 'processed'
        absence.save(update_fields=['status'])

        return {
            'absence': absence,
            'assigned': assigned,
            'unassigned': unassigned,
            'skipped': skipped,
            'workflow_steps': workflow_steps,
            'teacher_employee_link_ok': link_ok,
            'teacher_employee_link_note': link_note,
            'message': 'Fixture automation completed.',
        }

    @staticmethod
    def workflow_steps():
        return [
            'Absence Trigger: Manual Absence or Approved HR Leave',
            'Validate Teacher-Employee Link',
            'Resolve Academic Calendar and Active Timetable Version',
            'Check Existing Absence and Fixture Records',
            'Create or Update TeacherAbsence',
            'Find Affected AssignedPeriods',
            'Exclude Holidays, Cancelled Periods and Partial-Day Exceptions',
            'Build Candidate Substitute List',
            'Check active status, eligibility, conflicts, leave, availability, workload, consecutive periods',
            'Score and Rank Candidates',
            'Lock and Recheck Selected Candidate',
            'Create TeacherFixture Atomically',
            'Store Selection Reason and Candidate Result',
            'Commit Transaction',
            'Create In-App Notification',
            'Send Email/SMS/WhatsApp',
            'Log Delivery Separately',
            'Teacher Accepts or Assignment Becomes Final',
            'If Declined or Failed Reassign or Escalate',
            'Mark Fixture Completed or Cancelled',
        ]

    @staticmethod
    def resolve_timetable_version(target_date):
        return TimetableVersion.objects.filter(
            status='active'
        ).filter(
            Q(effective_from__isnull=True) | Q(effective_from__lte=target_date),
            Q(effective_to__isnull=True) | Q(effective_to__gte=target_date),
        ).first()

    @staticmethod
    def validate_teacher_employee_link(teacher, allow_legacy=False):
        if getattr(teacher, 'employee_id', None):
            return True, 'Explicit employee link found.'
        if allow_legacy and teacher.user_id:
            return True, 'Legacy user-account link used.'
        if allow_legacy and teacher.email:
            return True, 'Legacy email fallback available.'
        return False, 'No explicit employee link found.'

    @staticmethod
    def _get_or_create_absence(teacher, target_date, day, source, triggered_by=None, leave_application=None):
        query = TeacherAbsence.objects.filter(
            teacher=teacher,
            absence_date=target_date,
            source=source,
        )
        if leave_application:
            query = query.filter(leave_application=leave_application)
        else:
            query = query.filter(leave_application__isnull=True)

        absence = query.first()
        if absence:
            return absence

        return TeacherAbsence.objects.create(
            teacher=teacher,
            absence_date=target_date,
            day=day,
            source=source,
            leave_application=leave_application,
            created_by=triggered_by if getattr(triggered_by, 'is_authenticated', False) else None,
        )

    @staticmethod
    def find_absent_teacher_periods(teacher, day, timetable_version=None):
        queryset = AssignedPeriod.objects.filter(
            teacher=teacher,
            day=day,
        ).select_related('class_fk', 'section', 'subject', 'period').order_by('period__start_time', 'period__id')
        if timetable_version:
            queryset = queryset.filter(Q(timetable_version=timetable_version) | Q(timetable_version__isnull=True))
        return queryset

    @classmethod
    def find_substitute_candidates(cls, absence, assigned_period, target_date, day, absent_teacher):
        from teacher_dashboard.models import Teacher as DashboardTeacher

        busy_from_timetable = AssignedPeriod.objects.filter(
            day=day,
            period=assigned_period.period,
        ).values_list('teacher_id', flat=True)
        busy_from_fixtures = TeacherFixture.objects.filter(
            day=day,
            fixture_date=target_date,
            period=assigned_period.period,
        ).values_list('substitute_teacher_id', flat=True)

        busy_ids = set(busy_from_timetable) | set(busy_from_fixtures) | {absent_teacher.id}
        all_teachers = DashboardTeacher.objects.filter(status='active').distinct()
        candidates = []
        excluded_logs = []

        for teacher in all_teachers:
            exclusion_reason = cls.exclusion_reason(
                teacher=teacher,
                assigned_period=assigned_period,
                target_date=target_date,
                day=day,
                absent_teacher=absent_teacher,
                busy_ids=busy_ids,
            )
            if exclusion_reason:
                excluded_logs.append({
                    'teacher': teacher,
                    'decision': 'excluded',
                    'score': 0,
                    'reason': exclusion_reason,
                })
                continue

            daily_fixture_count = TeacherFixture.objects.filter(
                substitute_teacher=teacher,
                fixture_date=target_date,
            ).exclude(fixture_status='cancelled').count()
            weekly_load = AssignedPeriod.objects.filter(teacher=teacher).count()
            weekly_fixture_count = cls.weekly_substitute_count(teacher, target_date)
            score, reason = cls.score_candidate(
                teacher=teacher,
                assigned_period=assigned_period,
                target_date=target_date,
                daily_fixture_count=daily_fixture_count,
                weekly_load=weekly_load,
                weekly_fixture_count=weekly_fixture_count,
            )
            candidates.append({
                'teacher': teacher,
                'daily_fixture_count': daily_fixture_count,
                'weekly_load': weekly_load,
                'weekly_fixture_count': weekly_fixture_count,
                'score': score,
                'reason': reason,
            })

        candidates.sort(key=lambda item: (
            -item['score'],
            item['daily_fixture_count'],
            item['weekly_fixture_count'],
            item['weekly_load'],
            item['teacher'].id,
        ))
        return candidates, excluded_logs

    @staticmethod
    def assign_best_substitute(candidates):
        return candidates[0] if candidates else None

    @classmethod
    def exclusion_reason(cls, teacher, assigned_period, target_date, day, absent_teacher, busy_ids):
        if teacher.id == absent_teacher.id:
            return 'Absent teacher cannot substitute their own period.'
        if teacher.id in busy_ids:
            return 'Teacher has an assigned period or fixture conflict.'
        if cls.is_teacher_on_leave(teacher, target_date):
            return 'Teacher has approved leave on this date.'
        if cls.has_availability_restriction(teacher, target_date, assigned_period.period):
            return 'Teacher has an availability restriction for this period.'
        if TeacherFixture.objects.filter(substitute_teacher=teacher, fixture_date=target_date).exclude(fixture_status='cancelled').count() >= cls.workload_limit:
            return 'Teacher daily substitute limit reached.'
        if cls.weekly_substitute_count(teacher, target_date) >= cls.weekly_substitute_limit:
            return 'Teacher weekly substitute limit reached.'
        if not cls.subject_or_rule_match(teacher, assigned_period):
            return 'Teacher is not eligible for this subject.'
        if not cls.grade_eligibility_match(teacher, assigned_period):
            return 'Teacher is not eligible for this class/grade.'
        if cls.has_consecutive_overload(teacher, assigned_period, target_date, day):
            return 'Teacher would exceed consecutive-period load.'
        return ''

    @staticmethod
    def subject_or_rule_match(teacher, assigned_period):
        if not assigned_period.subject_id:
            return True
        if teacher.subjects.filter(id=assigned_period.subject_id).exists():
            return True
        eligible_subject_ids = SubjectSubstitutionRule.objects.filter(
            source_subject=assigned_period.subject,
            is_active=True,
        ).values_list('eligible_subject_id', flat=True)
        return teacher.subjects.filter(id__in=eligible_subject_ids).exists()

    @staticmethod
    def grade_eligibility_match(teacher, assigned_period):
        eligibility = TeacherTeachingEligibility.objects.filter(
            teacher=teacher,
            subject=assigned_period.subject,
            is_active=True,
        )
        if not eligibility.exists():
            return True
        return eligibility.filter(Q(class_fk=assigned_period.class_fk) | Q(class_fk__isnull=True)).exists()

    @staticmethod
    def is_teacher_on_leave(teacher, target_date):
        employee = getattr(teacher, 'employee', None)
        if not employee:
            return False
        return employee.leaves.filter(
            status='approved',
            start_date__lte=target_date,
            end_date__gte=target_date,
        ).exists()

    @staticmethod
    def has_availability_restriction(teacher, target_date, period):
        return TeacherAvailability.objects.filter(
            teacher=teacher,
            date=target_date,
        ).filter(Q(period=period) | Q(period__isnull=True)).exclude(availability_status='available').exists()

    @staticmethod
    def weekly_substitute_count(teacher, target_date):
        week_start = target_date - timedelta(days=target_date.weekday())
        week_end = week_start + timedelta(days=6)
        return TeacherFixture.objects.filter(
            substitute_teacher=teacher,
            fixture_date__range=(week_start, week_end),
        ).exclude(fixture_status='cancelled').count()

    @staticmethod
    def has_consecutive_overload(teacher, assigned_period, target_date, day):
        # Conservative v1 guard: allow the assignment unless explicit policy data exists later.
        return False

    @classmethod
    def score_candidate(cls, teacher, assigned_period, target_date, daily_fixture_count, weekly_load, weekly_fixture_count):
        score = 0
        reasons = []
        if assigned_period.subject_id and teacher.subjects.filter(id=assigned_period.subject_id).exists():
            score += 50
            reasons.append('same subject')
        elif assigned_period.subject_id:
            rule = SubjectSubstitutionRule.objects.filter(
                source_subject=assigned_period.subject,
                eligible_subject__in=teacher.subjects.all(),
                is_active=True,
            ).order_by('priority').first()
            if rule:
                score += max(10, 45 - rule.priority)
                reasons.append('subject substitution rule')
        if getattr(teacher, 'department', '') and getattr(assigned_period.teacher, 'department', '') and teacher.department == assigned_period.teacher.department:
            score += 15
            reasons.append('same department')
        if getattr(teacher, 'faculty_group', '') and getattr(assigned_period.teacher, 'faculty_group', '') and teacher.faculty_group == assigned_period.teacher.faculty_group:
            score += 10
            reasons.append('same faculty group')
        score += max(0, 20 - (daily_fixture_count * 8))
        score += max(0, 15 - weekly_fixture_count)
        score += max(0, 10 - min(weekly_load, 10))
        reasons.append(f'{daily_fixture_count} substitute duties today')
        reasons.append(f'{weekly_fixture_count} substitute duties this week')
        return score, ', '.join(reasons)

    @staticmethod
    def should_skip_period_for_absence(absence, assigned_period):
        if absence.start_time and assigned_period.period.end_time <= absence.start_time:
            return True
        if absence.end_time and assigned_period.period.start_time >= absence.end_time:
            return True
        return False

    @staticmethod
    def find_existing_fixture(target_date, assigned_period, day):
        return TeacherFixture.objects.filter(
            fixture_date=target_date,
        ).filter(
            Q(assigned_period=assigned_period) |
            Q(class_fk=assigned_period.class_fk, section=assigned_period.section, period=assigned_period.period, day=day)
        ).select_related('substitute_teacher').first()

    @staticmethod
    def recheck_candidate_available(substitute, assigned_period, target_date, day, absent_teacher):
        busy_ids = set(AssignedPeriod.objects.filter(day=day, period=assigned_period.period).values_list('teacher_id', flat=True))
        busy_ids |= set(TeacherFixture.objects.filter(day=day, fixture_date=target_date, period=assigned_period.period).exclude(fixture_status='cancelled').values_list('substitute_teacher_id', flat=True))
        return not FixtureAutomationService.exclusion_reason(substitute, assigned_period, target_date, day, absent_teacher, busy_ids)

    @staticmethod
    def record_candidate_logs(absence, result, assigned_period, logs):
        TeacherFixtureCandidateLog.objects.filter(absence=absence, assigned_period=assigned_period).delete()
        TeacherFixtureCandidateLog.objects.bulk_create([
            TeacherFixtureCandidateLog(
                absence=absence,
                absence_result=result,
                assigned_period=assigned_period,
                teacher=log['teacher'],
                decision=log['decision'],
                score=log.get('score', 0),
                reason=log.get('reason', ''),
            )
            for log in logs
        ])

    @staticmethod
    def notify_admin_uncovered(absence, result):
        # Admin escalation is surfaced on the Timetable Automation page via uncovered results.
        return None

    @classmethod
    def send_fixture_notifications(cls, fixture):
        substitute_message = cls._substitute_message(fixture)
        absent_message = cls._absent_message(fixture)

        cls._create_in_app_notification(
            teacher=fixture.substitute_teacher,
            title='Substitute fixture assigned',
            message=substitute_message,
            notification_type='fixture_assigned',
            fixture=fixture,
        )
        cls._create_in_app_notification(
            teacher=fixture.absent_teacher,
            title='Your class is covered',
            message=absent_message,
            notification_type='absence_covered',
            fixture=fixture,
        )

        substitute_ok = cls._send_email(
            fixture=fixture,
            teacher=fixture.substitute_teacher,
            subject='EduPilot Fixture Duty Assigned',
            message=substitute_message,
        )
        absent_ok = cls._send_email(
            fixture=fixture,
            teacher=fixture.absent_teacher,
            subject='EduPilot Absence Coverage Confirmed',
            message=absent_message,
        )
        cls._log_pending_delivery(fixture, fixture.substitute_teacher, 'sms', 'SMS provider is not configured yet.')
        cls._log_pending_delivery(fixture, fixture.substitute_teacher, 'whatsapp', 'WhatsApp provider is not configured yet.')
        cls._log_pending_delivery(fixture, fixture.absent_teacher, 'sms', 'SMS provider is not configured yet.')
        cls._log_pending_delivery(fixture, fixture.absent_teacher, 'whatsapp', 'WhatsApp provider is not configured yet.')

        if not substitute_ok or not absent_ok:
            fixture.automation_note = 'Fixture assigned; one or more communication channels failed and were logged separately.'
            fixture.save(update_fields=['automation_note'])

    @classmethod
    def send_unassigned_notifications(cls, teacher, assigned_period, target_date, day):
        message = (
            f"No substitute teacher was available for your period on {target_date} ({day}).\n"
            f"Class/Section: {assigned_period.class_fk.class_name} - {assigned_period.section.section_name}\n"
            f"Subject: {assigned_period.subject.name if assigned_period.subject else 'Optional'}\n"
            f"Period: {assigned_period.period.period_name} ({assigned_period.period.start_time} - {assigned_period.period.end_time})\n"
            "Admin review is required."
        )
        TeacherNotification.objects.create(
            teacher=teacher,
            title='Fixture still needs coverage',
            message=message,
            notification_type='fixture_unassigned',
            related_fixture=None,
        )
        TeacherFixtureNotificationLog.objects.create(
            fixture=None,
            recipient_teacher=teacher,
            channel='in_app',
            status='sent',
            sent_at=timezone.now(),
        )
        cls._send_email(
            fixture=None,
            teacher=teacher,
            subject='EduPilot Fixture Coverage Required',
            message=message,
        )
        cls._log_pending_delivery(None, teacher, 'sms', 'SMS provider is not configured yet.')
        cls._log_pending_delivery(None, teacher, 'whatsapp', 'WhatsApp provider is not configured yet.')

    @staticmethod
    def _create_in_app_notification(teacher, title, message, notification_type, fixture):
        TeacherNotification.objects.create(
            teacher=teacher,
            title=title,
            message=message,
            notification_type=notification_type,
            related_fixture=fixture,
        )
        TeacherFixtureNotificationLog.objects.create(
            fixture=fixture,
            recipient_teacher=teacher,
            channel='in_app',
            status='sent',
            sent_at=timezone.now(),
        )

    @staticmethod
    def _send_email(fixture, teacher, subject, message):
        if not teacher.email:
            TeacherFixtureNotificationLog.objects.create(
                fixture=fixture,
                recipient_teacher=teacher,
                channel='email',
                status='failed',
                error_message='Teacher email address is missing.',
            )
            return False

        try:
            send_mail(
                subject,
                message,
                getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                [teacher.email],
                fail_silently=False,
            )
            TeacherFixtureNotificationLog.objects.create(
                fixture=fixture,
                recipient_teacher=teacher,
                channel='email',
                status='sent',
                sent_at=timezone.now(),
            )
            return True
        except Exception as exc:
            TeacherFixtureNotificationLog.objects.create(
                fixture=fixture,
                recipient_teacher=teacher,
                channel='email',
                status='failed',
                error_message=str(exc),
            )
            return False

    @staticmethod
    def _log_pending_delivery(fixture, teacher, channel, note):
        TeacherFixtureNotificationLog.objects.create(
            fixture=fixture,
            recipient_teacher=teacher,
            channel=channel,
            status='pending',
            error_message=note,
        )

    @staticmethod
    def _substitute_message(fixture):
        return (
            f"You have been assigned as substitute teacher on {fixture.fixture_date} ({fixture.day}).\n"
            f"Class/Section: {fixture.class_fk.class_name} - {fixture.section.section_name}\n"
            f"Subject: {fixture.subject.name if fixture.subject else 'Optional'}\n"
            f"Period: {fixture.period.period_name} ({fixture.period.start_time} - {fixture.period.end_time})\n"
            f"Absent Teacher: {fixture.absent_teacher.name}"
        )

    @staticmethod
    def _absent_message(fixture):
        return (
            f"Your period on {fixture.fixture_date} ({fixture.day}) has been covered.\n"
            f"Class/Section: {fixture.class_fk.class_name} - {fixture.section.section_name}\n"
            f"Subject: {fixture.subject.name if fixture.subject else 'Optional'}\n"
            f"Period: {fixture.period.period_name} ({fixture.period.start_time} - {fixture.period.end_time})\n"
            f"Substitute Teacher: {fixture.substitute_teacher.name}"
        )

    @classmethod
    def teacher_from_leave_employee(cls, employee):
        from teacher_dashboard.models import Teacher as DashboardTeacher

        teacher = DashboardTeacher.objects.filter(employee=employee).first()
        if teacher:
            return teacher
        if employee.user_id:
            teacher = DashboardTeacher.objects.filter(user=employee.user).first()
            if teacher:
                return teacher
        return DashboardTeacher.objects.filter(email__iexact=employee.email).first()

    @classmethod
    def run_for_leave(cls, leave_application, triggered_by=None):
        teacher = cls.teacher_from_leave_employee(leave_application.employee)
        if not teacher:
            return []

        results = []
        current = leave_application.start_date
        while current <= leave_application.end_date:
            results.append(cls.run_for_absence(
                teacher=teacher,
                target_date=current,
                source='auto_leave',
                triggered_by=triggered_by,
                leave_application=leave_application,
            ))
            current += timedelta(days=1)
        return results

class FeeGenerationService:
    @staticmethod
    def generate_monthly_fees(month_name, year, job_id=None):
        """
        Generate monthly fee vouchers for all active students
        """
        print(f"\n{'='*60}")
        print(f"📋 FEE GENERATION STARTED: {month_name}-{year}")
        print(f"{'='*60}\n")
        
        log = FeeGenerationLog.objects.create(month=month_name, year=year, status='Running')
        job = AutomationJob.objects.filter(id=job_id).first() if job_id else None
        
        if job: 
            job.status = 'RUNNING'
            job.save()

        success_count = 0
        failed_count = 0
        
        # Get all active students
        students = Student.objects.filter(is_active=True)
        print(f"Total Active Students: {students.count()}\n")

        for student in students:
            try:
                # ✅ CHECK 1: Prevent duplicate vouchers
                existing = FeeVoucher.objects.filter(
                    student=student, 
                    month=month_name,
                    issue_date__year=year
                ).exists()
                
                if existing:
                    print(f"⏭️  SKIP: {student.full_name} - Voucher already exists")
                    continue
                
                # ✅ CHECK 2: Get fee assignment
                assignment = StudentFeeAssignment.objects.filter(student=student).first()
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
                balance_obj, _ = StudentBalance.objects.get_or_create(student=student)
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
                            status='SUCCESS'
                        )
                    
                    success_count += 1
                    print(f"✅ {student.full_name}: Rs.{net_amount} (Voucher: {voucher.voucher_no})")
                    
            except Exception as e:
                failed_count += 1
                error_msg = str(e)
                print(f"❌ {student.full_name}: {error_msg}")
                
                if job:
                    AutomationJobDetail.objects.create(
                        job=job,
                        student=student,
                        status='FAILED',
                        error_message=error_msg
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
        
        print(f"\n{'='*60}")
        print(f"✅ COMPLETED: {success_count} Success | ❌ {failed_count} Failed")
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
                assignment = StudentFeeAssignment.objects.filter(student=detail.student).first()
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
    def generate_salaries(month=None, year=None):
        month = month or datetime.now().strftime("%B")
        year = year or datetime.now().year

        # Duplicate Protection
        if SalaryVoucher.objects.filter(month=month, year=year).exists():
            print("⏭️  Salary already generated for this month")
            return

        job = SalaryAutomationJob.objects.create(status='RUNNING')
        teachers = Teacher.objects.filter(is_active=True)
        
        for teacher in teachers:
            try:
                # Calculate total earnings
                earnings = money(teacher.basic_salary) + \
                          money(teacher.house_allowance) + \
                          money(teacher.medical_allowance) + \
                          money(teacher.transport_allowance) + \
                          money(teacher.utility_allowance) + \
                          money(teacher.special_allowance) + \
                          money(teacher.overtime)
                
                # Get deductions
                deductions = SalaryStructure.objects.filter(teacher=teacher).values_list('deductions', flat=True).first() or 0
                net_salary = earnings - money(deductions)

                # Create voucher
                voucher = SalaryVoucher.objects.create(
                    teacher=teacher,
                    month=month,
                    year=year,
                    net_salary=net_salary,
                    status='UNPAID'
                )

                SalaryPDFGeneratorService.generate_salary_pdf(voucher)
                job.success_count += 1
                print(f"✅ {teacher.name}: Rs.{net_salary}")
                
            except Exception as e:
                job.failed_count += 1
                SalaryAutomationJobDetail.objects.create(
                    job=job, 
                    teacher=teacher, 
                    status='FAILED', 
                    error_message=str(e)
                )
                print(f"❌ {teacher.name}: {str(e)}")
        
        job.status = 'COMPLETED'
        job.completed_at = timezone.now()
        job.save()
        
        print(f"✅ Salary generation: {job.success_count} success, {job.failed_count} failed")
