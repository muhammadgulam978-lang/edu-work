
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Sum
from decimal import Decimal
from datetime import date

# --- PHASE 0: USER ---
# class User(AbstractUser):
#     ROLE_CHOICES = (
#         ('admin', 'Admin'),
#         ('student', 'Student'),
#         ('parent', 'Parent'),
#         ('teacher', 'Teacher'),
#     )
#     role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')

# --- CORE MODELS ---
class FeeHead(models.Model):
    FREQUENCY_CHOICES = [('one_time', 'One Time'), ('monthly', 'Monthly'), ('yearly', 'Yearly')]
    name = models.CharField(max_length=100)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    status = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.frequency})"

class FeePlan(models.Model):
    name = models.CharField(max_length=100)
    class_name = models.CharField(max_length=50)
    session = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.name} - {self.class_name}"

class FeePlanDetail(models.Model):
    fee_plan = models.ForeignKey(FeePlan, on_delete=models.CASCADE)
    fee_head = models.ForeignKey(FeeHead, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

class TransportRoute(models.Model):
    route_name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.route_name

class Scholarship(models.Model):
    DISCOUNT_TYPES = [('percentage', 'Percentage'), ('fixed', 'Fixed Amount')]
    name = models.CharField(max_length=100)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES)
    value = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name

class Student(models.Model):
    full_name = models.CharField(max_length=100)
    admission_number = models.CharField(max_length=50, unique=True)
    current_class = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    admission_date = models.DateField(auto_now_add=True)
    campus = models.CharField(max_length=50, blank=True)
    student_id = models.CharField(max_length=50, blank=True)
    canonical_student = models.OneToOneField(
        'student_profile.Student',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='automation_legacy_record',
    )

    def __str__(self):
        return self.full_name

class StudentFeeAssignment(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='fee_assignment')
    canonical_student = models.OneToOneField(
        'student_profile.Student', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='automation_fee_assignment',
    )
    fee_plan = models.ForeignKey(FeePlan, on_delete=models.PROTECT)
    transport_route = models.ForeignKey(TransportRoute, on_delete=models.SET_NULL, null=True, blank=True)
    scholarship = models.ForeignKey(Scholarship, on_delete=models.SET_NULL, null=True, blank=True)

class StudentLedger(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    canonical_student = models.ForeignKey(
        'student_profile.Student', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='automation_ledger_entries',
    )
    date = models.DateField(auto_now_add=True)
    description = models.CharField(max_length=255)
    debit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    credit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    reference_no = models.CharField(max_length=50, blank=True, null=True)

class StudentBalance(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE)
    canonical_student = models.OneToOneField(
        'student_profile.Student', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='automation_balance',
    )
    outstanding_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

# Add this to your models.py - Update the FeeVoucher model

class FeeVoucher(models.Model):
    STATUS_CHOICES = [('UNPAID', 'Unpaid'), ('PARTIAL', 'Partial'), ('PAID', 'Paid'), ('OVERDUE', 'Overdue')]
    voucher_no = models.CharField(max_length=50, unique=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    canonical_student = models.ForeignKey(
        'student_profile.Student', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='automation_fee_vouchers',
    )
    month = models.CharField(max_length=20)
    year = models.IntegerField(default=2024)  # ✅ ADD THIS LINE
    issue_date = models.DateField()
    due_date = models.DateField()
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fine = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    previous_due = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UNPAID')
    
    class Meta:
        unique_together = ('student', 'month', 'year')  # ✅ ADD THIS FOR DUPLICATE PREVENTION
    
    def __str__(self):
        return f"{self.voucher_no} - {self.student.full_name}"
class FeeVoucherItem(models.Model):
    voucher = models.ForeignKey(FeeVoucher, on_delete=models.CASCADE, related_name='items')
    fee_head = models.ForeignKey(FeeHead, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

# --- AUTOMATION & LOGGING MODELS ---
class FeeGenerationSettings(models.Model):
    auto_enabled = models.BooleanField(default=False)
    generation_day = models.PositiveIntegerField(default=1) 
    generation_time = models.TimeField(default="09:00:00") 
    send_notifications = models.BooleanField(default=True)

class FeeGenerationLog(models.Model):
    month = models.CharField(max_length=20)
    year = models.IntegerField()
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    students_processed = models.IntegerField(default=0)
    success_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default='Running')

class AutomationJob(models.Model):
    STATUS_CHOICES = (('PENDING', 'Pending'), ('RUNNING', 'Running'), ('COMPLETED', 'Completed'), ('FAILED', 'Failed'))
    job_type = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    processed_count = models.IntegerField(default=0)
    success_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)

class AutomationJobDetail(models.Model):
    job = models.ForeignKey(AutomationJob, on_delete=models.CASCADE, related_name='details')
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    canonical_student = models.ForeignKey(
        'student_profile.Student', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='automation_job_details',
    )
    status = models.CharField(max_length=20)
    error_message = models.TextField(null=True, blank=True)

# class NotificationQueue(models.Model):
#     STATUS_CHOICES = (('PENDING', 'Pending'), ('SENT', 'Sent'), ('FAILED', 'Failed'))
#     student = models.ForeignKey(Student, on_delete=models.CASCADE)
#     notification_type = models.CharField(max_length=10, choices=(('SMS', 'SMS'), ('EMAIL', 'Email')))
#     content = models.TextField()
#     status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
#     created_at = models.DateTimeField(auto_now_add=True)

class NotificationQueue(models.Model):
    STATUS_CHOICES = (('PENDING', 'Pending'), ('SENT', 'Sent'), ('FAILED', 'Failed'))
    student = models.ForeignKey(Student, on_delete=models.CASCADE, null=True, blank=True)  # ← null=True, blank=True add kiya
    teacher = models.ForeignKey('Teacher', on_delete=models.CASCADE, null=True, blank=True)  # ← YE NAYI LINE ADD KARO
    canonical_student = models.ForeignKey(
        'student_profile.Student', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='automation_notifications',
    )
    canonical_teacher = models.ForeignKey(
        'teacher_dashboard.Teacher', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='automation_notifications',
    )
    notification_type = models.CharField(max_length=10, choices=(('SMS', 'SMS'), ('EMAIL', 'Email')))
    content = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)


class Announcement(models.Model):
    CATEGORY_CHOICES = [
        ('ACADEMIC', 'Academic'), ('EVENT', 'Event'), ('HOLIDAY', 'Holiday'),
        ('ALERT', 'Alert / Warning'), ('NOTICE', 'Administrative Notice'),
        ('MAINTENANCE', 'System Maintenance'),
    ]
    PRIORITY_CHOICES = [('HIGH', 'High Priority'), ('MEDIUM', 'Medium Priority'), ('LOW', 'Low Priority')]
    AUDIENCE_CHOICES = [
        ('ALL', 'All Users'), ('STUDENTS', 'Students Only'), ('TEACHERS', 'Teachers Only'),
        ('PARENTS', 'Parents Only'), ('ADMINS', 'Administrators Only'), ('CLASS', 'Specific Class'),
    ]
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'), ('SCHEDULED', 'Scheduled'), ('PUBLISHED', 'Published'),
        ('ARCHIVED', 'Archived'), ('EXPIRED', 'Expired'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='NOTICE')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM')
    audience = models.CharField(max_length=20, choices=AUDIENCE_CHOICES, default='ALL')
    target_class = models.ForeignKey('admin_panel.Class', on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='announcements')
    attachment = models.FileField(upload_to='announcements/', null=True, blank=True)
    publish_date = models.DateTimeField()
    expiry_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    is_pinned = models.BooleanField(default=False)
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='created_announcements')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    view_count = models.PositiveIntegerField(default=0)
    total_intended_recipients = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-is_pinned', '-publish_date']
        indexes = [
            models.Index(fields=['status', '-publish_date']),
            models.Index(fields=['audience', 'status']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"


class AnnouncementRead(models.Model):
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='reads')
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['announcement', 'user'], name='unique_announcement_read')]
        indexes = [models.Index(fields=['announcement', 'user']), models.Index(fields=['read_at'])]


class AnnouncementNotification(models.Model):
    NOTIFICATION_TYPES = [('IN_APP', 'In-app'), ('EMAIL', 'Email'), ('SMS', 'SMS'), ('PUSH', 'Push')]
    STATUS_CHOICES = [('PENDING', 'Pending'), ('SENT', 'Sent'), ('FAILED', 'Failed'), ('SKIPPED', 'Skipped')]

    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='notifications')
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='IN_APP')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['announcement', 'user', 'notification_type'],
                                                name='unique_announcement_notification')]
        indexes = [models.Index(fields=['announcement', 'user']), models.Index(fields=['status'])]
    
# --- TEACHER SALARY MODELS ---
class Teacher(models.Model):
    name = models.CharField(max_length=100)
    teacher_id = models.CharField(max_length=50, unique=True, default='000')
    cnic = models.CharField(max_length=20, default='', null=True, blank=True)
    email = models.EmailField(default='', null=True, blank=True)
    phone = models.CharField(max_length=20, default='', null=True, blank=True)
    address = models.TextField(default='', null=True, blank=True)
    department = models.CharField(max_length=100, default='', null=True, blank=True)
    designation = models.CharField(max_length=100, default='', null=True, blank=True)
    joining_date = models.DateField(null=True, blank=True)
    employment_type = models.CharField(max_length=50, default='', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    house_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    medical_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    transport_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    utility_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    special_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    overtime = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    canonical_teacher = models.OneToOneField(
        'teacher_dashboard.Teacher',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='automation_legacy_record',
    )

    def __str__(self):
        return f"{self.name} ({self.teacher_id})"

class SalaryStructure(models.Model):
    teacher = models.OneToOneField(Teacher, on_delete=models.CASCADE)
    canonical_teacher = models.OneToOneField(
        'teacher_dashboard.Teacher', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='automation_salary_structure',
    )
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)

class SalaryVoucher(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    canonical_teacher = models.ForeignKey(
        'teacher_dashboard.Teacher', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='automation_salary_vouchers',
    )
    month = models.CharField(max_length=20)
    year = models.IntegerField()
    net_salary = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, default='UNPAID')
    generated_at = models.DateTimeField(auto_now_add=True)

# --- SALARY AUTOMATION MODELS (NEW) ---
class SalaryAutomationSettings(models.Model):
    auto_enabled = models.BooleanField(default=False)
    generation_day = models.PositiveIntegerField(default=30)
    generation_time = models.TimeField(default="18:00:00")
    send_notifications = models.BooleanField(default=True)

class SalaryAutomationJob(models.Model):
    STATUS_CHOICES = (('PENDING', 'Pending'), ('RUNNING', 'Running'), ('COMPLETED', 'Completed'), ('FAILED', 'Failed'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    success_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)

class SalaryAutomationJobDetail(models.Model):
    job = models.ForeignKey(SalaryAutomationJob, on_delete=models.CASCADE, related_name='details')
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    canonical_teacher = models.ForeignKey(
        'teacher_dashboard.Teacher', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='automation_salary_job_details',
    )
    status = models.CharField(max_length=20)
    error_message = models.TextField(null=True, blank=True)

# --- OTHER MODELS ---
class Staff(models.Model):
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

class StudentPerformance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    attendance_percentage = models.FloatField()
    average_test_score = models.FloatField()
    risk_level = models.CharField(max_length=20)

class Transaction(models.Model):
    title = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(max_length=20)
    date = models.DateField()


class CanonicalMappingAudit(models.Model):
    ENTITY_CHOICES = [('STUDENT', 'Student'), ('TEACHER', 'Teacher')]
    STATUS_CHOICES = [
        ('MATCHED', 'Matched'),
        ('AMBIGUOUS', 'Ambiguous'),
        ('UNMATCHED', 'Unmatched'),
        ('INVALID', 'Invalid'),
    ]

    entity_type = models.CharField(max_length=10, choices=ENTITY_CHOICES)
    legacy_pk = models.PositiveBigIntegerField()
    canonical_pk = models.PositiveBigIntegerField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES)
    matched_by = models.CharField(max_length=30, blank=True)
    details = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['entity_type', 'legacy_pk'],
                name='unique_canonical_mapping_audit',
            )
        ]

    def __str__(self):
        return f"{self.entity_type} {self.legacy_pk}: {self.status}"


# --- ADMIN DASHBOARD HELPER ---
def get_dashboard_stats():
    from student_profile.models import Student as PortalStudent
    from teacher_dashboard.models import Teacher as PortalTeacher

    return {
        "total_students": PortalStudent.objects.count(),
        "monthly_revenue": Transaction.objects.filter(type='INCOME', date__month=date.today().month).aggregate(Sum('amount'))['amount__sum'] or 0,
        "total_expenses": Transaction.objects.filter(type='EXPENSE').aggregate(Sum('amount'))['amount__sum'] or 0,
        "high_risk_students": StudentPerformance.objects.filter(risk_level='HIGH').count(),
        "total_teachers": PortalTeacher.objects.filter(status='active').count(),
        "total_staff": Staff.objects.filter(is_active=True).count(),
        "recent_transactions": Transaction.objects.all().order_by('-date')[:5]
    }

# --- SIGNALS ---
@receiver(post_save, sender=FeeVoucher)
def create_ledger_entry(sender, instance, created, **kwargs):
    if created:
        StudentLedger.objects.create(
            student=instance.student,
            canonical_student=instance.canonical_student or instance.student.canonical_student,
            description=f"Fee Voucher Generated: {instance.voucher_no}",
            debit=instance.net_amount,
            balance=instance.net_amount,
            reference_no=instance.voucher_no
        )
        balance_obj, _ = StudentBalance.objects.get_or_create(
            student=instance.student,
            defaults={'canonical_student': instance.canonical_student or instance.student.canonical_student},
        )
        if not balance_obj.canonical_student_id:
            balance_obj.canonical_student = instance.canonical_student or instance.student.canonical_student
        balance_obj.outstanding_amount += Decimal(str(instance.net_amount))
        balance_obj.save()
class Period(models.Model):
    class_name = models.CharField(max_length=50)
    section = models.CharField(max_length=50)
    subject = models.CharField(max_length=100)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    day = models.CharField(max_length=20)
    period_number = models.IntegerField()
    start_time = models.TimeField()
    end_time = models.TimeField()

class AssignedPeriods(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    period = models.ForeignKey(Period, on_delete=models.CASCADE)

class Fixture(models.Model):
    absent_teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='absent_fixtures')
    replacement_teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='replacement_fixtures')
    period = models.ForeignKey(Period, on_delete=models.CASCADE)
    fixture_date = models.DateField()
    status = models.CharField(max_length=20, default='PENDING')

class Absence(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    absence_date = models.DateField()
    period = models.ForeignKey(Period, on_delete=models.CASCADE)
