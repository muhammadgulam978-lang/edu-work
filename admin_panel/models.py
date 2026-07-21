from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from student_profile.models import Student
from datetime import datetime, timedelta
from student_profile.models import Student
import uuid
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
import random
import string



from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Sum
from decimal import Decimal
from datetime import date



# admin_panel/models.py
from django.db import models
from django.contrib.auth.models import User, Group

class UserRole(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} → {self.role.name if self.role else 'No Role'}"

class RoleActivityLog(models.Model):
    ACTION_ROLE_CREATED = "role_created"
    ACTION_USER_CREATED = "user_created"
    ACTION_ROLE_ASSIGNED = "role_assigned"
    ACTION_VALIDATION_FAILED = "validation_failed"

    ACTION_CHOICES = [
        (ACTION_ROLE_CREATED, "Role Created"),
        (ACTION_USER_CREATED, "User Created"),
        (ACTION_ROLE_ASSIGNED, "Role Assigned"),
        (ACTION_VALIDATION_FAILED, "Validation Failed"),
    ]

    action_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="role_activity_actions",
    )
    action_type = models.CharField(max_length=50, choices=ACTION_CHOICES)
    target_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="role_activity_targets",
    )
    target_role = models.ForeignKey(
        Group,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="role_activity_logs",
    )
    message = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_action_type_display()} - {self.created_at:%Y-%m-%d %H:%M}"


# -----------------------------------------------

class AcademicYear(models.Model):
    year = models.CharField(max_length=9)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.year

class ClassGroup(models.Model):
    group_name = models.CharField(max_length=50)

    def __str__(self):
        return self.group_name
    
class Stream(models.Model):
    stream_name = models.CharField(max_length=100)

    def __str__(self):
        return self.stream_name


class Class(models.Model):
    class_name = models.CharField(max_length=50, unique=True)
    total_students = models.IntegerField(default=0)
    group = models.ForeignKey(ClassGroup, on_delete=models.SET_NULL, null=True, blank=True)


    def save(self, *args, **kwargs):
        if self.pk is not None:
            original = Class.objects.get(pk=self.pk)
            if original.total_students != self.total_students:
                Admission.objects.filter(class_name=self.class_name).update(total_students=self.total_students)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.class_name


class Section(models.Model):
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    class_fk = models.ForeignKey(Class, on_delete=models.CASCADE)
    section_name = models.CharField(max_length=50)
    capacity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.class_fk.class_name} - {self.section_name}"

    @property
    def admitted_students(self):
        from .models import Admission
        return Admission.objects.filter(section=self).count()

    @property
    def remaining_seats(self):
        return self.capacity - self.admitted_students

    def has_space(self):
        return self.remaining_seats > 0

class Admission(models.Model):
    student_id = models.CharField(max_length=20, unique=True, blank=True, null=True, editable=False)
    campus = models.CharField(max_length=100)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True, blank=True)
    branch = models.CharField(max_length=50)
    ref_no = models.CharField(max_length=50)
    name = models.CharField(max_length=100)
    class_fk = models.ForeignKey(Class, on_delete=models.CASCADE, null=True, blank=True)
    dob = models.DateField()
    gender = models.CharField(
        max_length=10,
        choices=[
            ('male', 'Male'),
            ('female', 'Female'),
        ],
        blank=True,
        null=True
    )
    email = models.EmailField(blank=True)
    contact = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    admission_date = models.DateField()
    father_name = models.CharField(max_length=100)
    mother_name = models.CharField(max_length=100, default='Unknown')
    father_contact = models.CharField(max_length=20, blank=True, null=True)
    father_cnic = models.CharField(max_length=20, blank=True, null=True)
    father_email = models.EmailField(blank=True, null=True)
    father_occupation = models.CharField(max_length=255, blank=True, null=True)
    nationality = models.CharField(max_length=100, blank=True, null=True)
    admission_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected')
        ],
        default='pending'
    )
    rejection_reason = models.TextField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # 1. Student ID Generation
        if not self.student_id:
            last_id = Admission.objects.exclude(student_id__isnull=True).order_by('-id').first()
            if last_id and last_id.student_id:
                try:
                    # Assumes IDs are like 'STD####'
                    last_number = int(last_id.student_id.replace('STD', ''))
                except:
                    # Fallback if student_id format is unexpected
                    last_number = Admission.objects.exclude(student_id__isnull=True).count()
            else:
                last_number = 0
            self.student_id = f'STD{last_number + 1:04d}'

        # 2. Automatic Section Assignment
        if not self.section and self.class_fk and self.academic_year:
            sections = Section.objects.filter(
                class_fk=self.class_fk,
                academic_year=self.academic_year
            )
            for sec in sections:
                admitted = Admission.objects.filter(section=sec).count()
                if admitted < sec.capacity:
                    self.section = sec
                    break
            else:
                raise ValidationError("No available section with capacity for this class and academic year.")

        # ❗ NO STUDENT CREATION HERE ANYMORE (This comment is part of the original logic)
        super().save(*args, **kwargs)

       
class Subject(models.Model):
    GRADING_CHOICES = [
        ('gpa', 'GPA'),
        ('percentage', 'Percentage'),
        ('letter', 'Letter Grade'),
    ]

    FORMAT_CHOICES = [
        ('Optional', 'Optional'),
        ('Compulsory', 'Compulsory'),
    ]
    CORE_TYPE_CHOICES = [
        ('core', 'Core'),
        ('non_core', 'Non-Core'),
    ]

    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    class_fk = models.ForeignKey(Class, on_delete=models.CASCADE, null=True, blank=True)
    stream = models.ForeignKey("Stream", on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=50)
    subject_format = models.CharField(max_length=20, choices=FORMAT_CHOICES, default='Compulsory')
    subject_type = models.CharField(max_length=20, choices=CORE_TYPE_CHOICES, default='core')
    grading_type = models.CharField(max_length=20, choices=GRADING_CHOICES)
    short_code = models.CharField(max_length=10, unique=True)
    sort_order = models.PositiveIntegerField()
    course_description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.short_code})"


from django.db import models
from datetime import datetime, timedelta

DAYS_OF_WEEK = [
    ('Monday', 'Monday'),
    ('Tuesday', 'Tuesday'),
    ('Wednesday', 'Wednesday'),
    ('Thursday', 'Thursday'),
    ('Friday', 'Friday'),
    ('Saturday', 'Saturday'),
    ('Sunday', 'Sunday'),
]

class CreatePeriod(models.Model):
    day = models.CharField(max_length=10, choices=DAYS_OF_WEEK)
    period_name = models.CharField(max_length=50)  # New field for period name
    start_time = models.TimeField()
    end_time = models.TimeField()
    duration_minutes = models.PositiveIntegerField(editable=False)

    def save(self, *args, **kwargs):
        dt_start = datetime.combine(datetime.today(), self.start_time)
        dt_end = datetime.combine(datetime.today(), self.end_time)
        if dt_end < dt_start:
            dt_end += timedelta(days=1)
        self.duration_minutes = int((dt_end - dt_start).total_seconds() / 60)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.day} - {self.period_name}: {self.start_time.strftime('%I:%M %p')} - {self.end_time.strftime('%I:%M %p')} ({self.duration_minutes} mins)"

class SubjectPeriod(models.Model):
    group = models.ForeignKey(ClassGroup, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    day = models.CharField(max_length=10, choices=DAYS_OF_WEEK)
    periods = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('group', 'subject', 'day')


    # def __str__(self):
    #     return f"{self.subject.name} - {self.group.name} - {self.day} ({self.periods} periods)"
    def __str__(self):
          return f"{self.subject.name} - {self.group.group_name} - {self.day} ({self.periods} periods)"


class AssignedPeriod(models.Model):
    class_fk = models.ForeignKey(Class, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    day = models.CharField(max_length=10, choices=DAYS_OF_WEEK)
    period = models.ForeignKey(CreatePeriod, on_delete=models.CASCADE)
    teacher = models.ForeignKey('teacher_dashboard.Teacher', on_delete=models.CASCADE)
    is_bypass = models.BooleanField(default=False)
    timetable_version = models.ForeignKey('TimetableVersion', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_periods')

    def __str__(self):
        return f"{self.day} - {self.period} - {self.subject.name} - {self.teacher.name}"


class TimetableVersion(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('archived', 'Archived'),
    ]

    name = models.CharField(max_length=120, default='Default Timetable')
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.SET_NULL, null=True, blank=True)
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-effective_from', '-created_at']

    def __str__(self):
        return self.name

#-----------------------Working on class teacher ------------------------------------------------------------

class ClassTeacher(models.Model):
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    class_fk = models.ForeignKey(Class, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    teacher = models.ForeignKey('teacher_dashboard.Teacher', on_delete=models.CASCADE)
    assigned_date = models.DateField(auto_now_add=True)

    class Meta:
        # UNIQUE constraint: Ek section per sirf ek teacher
        unique_together = ('academic_year', 'class_fk', 'section')

    def __str__(self):
        return f"{self.teacher.name} - {self.class_fk.class_name} ({self.section.section_name})"


# results/models.py

class ExamResult(models.Model):
    TERM_CHOICES = [
        ('midterm', 'Midterm'),
        ('final', 'Final Term'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    class_fk = models.ForeignKey(Class, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    teacher = models.ForeignKey("teacher_dashboard.Teacher", on_delete=models.SET_NULL, null=True)
    term = models.CharField(max_length=20, choices=TERM_CHOICES)
    marks_obtained = models.FloatField()
    total_marks = models.FloatField()
    date_uploaded = models.DateTimeField(auto_now_add=True)
    teacher_remarks = models.TextField(blank=True, null=True)


    class Meta:
        unique_together = ('student', 'subject', 'term')  # to prevent duplicates


class Diary(models.Model):
    teacher = models.ForeignKey('teacher_dashboard.Teacher', on_delete=models.CASCADE)
    class_fk = models.ForeignKey('admin_panel.Class', on_delete=models.CASCADE)
    section = models.ForeignKey('admin_panel.Section', on_delete=models.CASCADE)
    subject = models.ForeignKey('admin_panel.Subject', on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    content = models.TextField()  # diary ka content, ya file agar chahiye ho to FileField
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.teacher.user.username} - {self.class_fk.name} - {self.date}"


# -----------------------------------------------------------------

class ExamFormat(models.Model):
    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, default=1)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    format_name = models.CharField(max_length=255, default="Default Format")
    num_mcqs = models.PositiveIntegerField(default=0)
    num_short = models.PositiveIntegerField(default=0)
    num_long = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.format_name} - {self.class_obj.class_name} - {self.subject.name}"


class Question(models.Model):
    QUESTION_TYPES = [
        ('MCQ', 'Multiple Choice'),
        ('SHORT', 'Short Question'),
        ('LONG', 'Long Question'),
    ]

    exam_format = models.ForeignKey(
        ExamFormat,
        on_delete=models.CASCADE,
        related_name="questions"
    )
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPES)
    text = models.TextField()

    option_a = models.CharField(max_length=255, null=True, blank=True)
    option_b = models.CharField(max_length=255, null=True, blank=True)
    option_c = models.CharField(max_length=255, null=True, blank=True)
    option_d = models.CharField(max_length=255, null=True, blank=True)

    correct_answer = models.CharField(
        max_length=1,
        choices=[("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")],
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.question_type} - {self.text[:30]}"


# =======================================================================================
from django.db import models
from django.conf import settings
from django.utils import timezone

class CurriculumSource(models.Model):
    name = models.CharField(max_length=200)
    website_url = models.URLField(blank=True, null=True)
    def __str__(self):
        return self.name

class GuideBook(models.Model):
    name = models.CharField(max_length=512)
    subject = models.ForeignKey("Subject", on_delete=models.CASCADE)
    school_class = models.ForeignKey("Class", on_delete=models.CASCADE)
    source = models.ForeignKey(CurriculumSource, null=True, blank=True, on_delete=models.SET_NULL)
    guide_url = models.URLField(blank=True)
    def __str__(self):
        return self.name

class Book(models.Model):
    title = models.CharField(max_length=255)
    class_for = models.ForeignKey(Class, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to='books/')
    parsed = models.BooleanField(default=False)

    def __str__(self):
        return self.title

from django.db import models


class Chapter(models.Model):
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name="chapters"
    )
    title = models.CharField(max_length=255)
    pdf_file = models.FileField(upload_to="chapters/")
    class_for = models.ForeignKey(Class, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    uploaded_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True)


    
    def __str__(self):
        return self.title

class Topic(models.Model):
    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.CASCADE,
        related_name="topics"
    )
    title = models.CharField(max_length=255)

    def __str__(self):
        return self.title


class SubTopic(models.Model):
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name="subtopics"
    )
    title = models.CharField(max_length=255)

    def __str__(self):
        return self.title


class ContentBlock(models.Model):
    """
    Har actual syllabus ka paragraph / explanation / theory yahan ayegi
    """
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name="content_blocks",
        null=True,
        blank=True
    )
    subtopic = models.ForeignKey(
        SubTopic,
        on_delete=models.CASCADE,
        related_name="content_blocks",
        null=True,
        blank=True
    )
    text = models.TextField()

    def __str__(self):
        if self.subtopic:
            return f"Content for {self.subtopic.title}"
        return f"Content for {self.topic.title}"

class LessonPlanRequest(models.Model):
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE)
    topics = models.ManyToManyField(Topic)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)

    total_periods = models.PositiveIntegerField()
    planning_style = models.CharField(max_length=50, default="rule-based")

    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("generated", "Generated"),
        ],
        default="pending"
    )

    created_at = models.DateTimeField(auto_now_add=True)



class LessonDay(models.Model):
    plan = models.ForeignKey(
        'LessonPlanRequest',
        on_delete=models.CASCADE,
        related_name="lessons",
        null=True, blank=True
    )
    day_number = models.PositiveIntegerField(default=1)
    learning_objectives = models.TextField(blank=True)
    teaching_content = models.TextField(blank=True)
    practice_work = models.TextField(blank=True)
    assessment_tasks = models.TextField(blank=True)
    homework_tasks = models.TextField(blank=True)

    class Meta:
        ordering = ['day_number']

    def __str__(self):
        return f"Day {self.day_number} - {self.plan}"

    
class Worksheet(models.Model):
    lesson_plan = models.ForeignKey(LessonPlanRequest, on_delete=models.CASCADE, related_name='worksheets')
    created_at = models.DateTimeField(default=timezone.now)
    pdf_file = models.FileField(upload_to='worksheets/', null=True, blank=True)
    raw_content = models.TextField(blank=True)
    def __str__(self):
        return f"Worksheet {self.id} for {self.lesson_plan.topic_title}"


# Fixture Model (Place this at the END of admin_panel/models.py)

class TeacherFixture(models.Model):            # FIXED SYNTAX
    SOURCE_CHOICES = [
        ('manual', 'Manual'),
        ('auto_absence', 'Auto Absence'),
        ('auto_leave', 'Auto Leave'),
    ]
    AUTOMATION_STATUS_CHOICES = [
        ('assigned', 'Assigned'),
        ('unassigned', 'Unassigned'),
        ('notification_failed', 'Notification Failed'),
    ]
    FIXTURE_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('assigned', 'Assigned'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('reassigned', 'Reassigned'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('uncovered', 'Uncovered'),
    ]
    ASSIGNMENT_MODE_CHOICES = [
        ('auto', 'Auto'),
        ('manual', 'Manual'),
        ('overridden', 'Overridden'),
    ]
    RESPONSE_STATUS_CHOICES = [
        ('final', 'Final'),
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    ]

    class_fk = models.ForeignKey(Class, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True)
    period = models.ForeignKey(CreatePeriod, on_delete=models.CASCADE)
    assigned_period = models.ForeignKey('AssignedPeriod', on_delete=models.SET_NULL, null=True, blank=True, related_name='fixtures')
    timetable_version = models.ForeignKey('TimetableVersion', on_delete=models.SET_NULL, null=True, blank=True, related_name='fixtures')

    absent_teacher = models.ForeignKey('teacher_dashboard.Teacher', related_name="absent_fixtures", on_delete=models.CASCADE)
    substitute_teacher = models.ForeignKey('teacher_dashboard.Teacher', related_name="substitute_fixtures", on_delete=models.CASCADE)
    original_substitute_teacher = models.ForeignKey('teacher_dashboard.Teacher', related_name="original_substitute_fixtures", on_delete=models.SET_NULL, null=True, blank=True)

    day = models.CharField(max_length=20)
    date = models.DateField(auto_now_add=True)
    fixture_date = models.DateField(default=timezone.localdate)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='manual')
    automation_status = models.CharField(max_length=30, choices=AUTOMATION_STATUS_CHOICES, default='assigned')
    fixture_status = models.CharField(max_length=20, choices=FIXTURE_STATUS_CHOICES, default='assigned')
    assignment_mode = models.CharField(max_length=20, choices=ASSIGNMENT_MODE_CHOICES, default='manual')
    automation_note = models.TextField(blank=True, default='')
    override_reason = models.TextField(blank=True, default='')
    overridden_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='overridden_teacher_fixtures')
    overridden_at = models.DateTimeField(null=True, blank=True)
    selection_score = models.IntegerField(default=0)
    selection_reason = models.TextField(blank=True, default='')
    candidate_count = models.PositiveIntegerField(default=0)
    response_required = models.BooleanField(default=False)
    response_status = models.CharField(max_length=20, choices=RESPONSE_STATUS_CHOICES, default='final')
    response_deadline = models.DateTimeField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    decline_reason = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['fixture_date', 'assigned_period'],
                name='uniq_fixture_date_assigned_period',
            )
        ]

    def __str__(self):
        return f"{self.class_fk.class_name} - {self.section.section_name} ({self.day})"


from django.db import models
from django.contrib.auth.models import User
from datetime import date
from dateutil.relativedelta import relativedelta

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Designation(models.Model):
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="designations"
    )
    title = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.title} ({self.department.name})"

class StaffCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class JobType(models.Model):
    name = models.CharField(max_length=50, unique=True)
    probation_months = models.PositiveIntegerField(default=0)
    is_leave_eligible = models.BooleanField(default=True)
    has_benefits = models.BooleanField(default=True)

    allowed_leave_types = models.ManyToManyField(
        'LeaveType',
        blank=True,
        related_name='job_types'
    )

    def __str__(self):
        return self.name

class Employee(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)

    staff_category = models.ForeignKey(
        StaffCategory,
        on_delete=models.SET_NULL,
        null=True
    )

    job_type = models.ForeignKey(
        JobType,
        on_delete=models.SET_NULL,
        null=True
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True
    )

    designation = models.ForeignKey(
        Designation,
        on_delete=models.SET_NULL,
        null=True
    )

    joining_date = models.DateField()
    is_teacher = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        permissions = [
            ("view_all_employee", "Can view all employees"),
        ]

    def can_apply_leave(self):
        if not self.job_type.is_leave_eligible:
            return False

        probation_end = self.joining_date + relativedelta(
            months=self.job_type.probation_months
        )
        return date.today() >= probation_end

    def __str__(self):
        return self.name

from django.db import models

class LeaveType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    yearly_quota = models.PositiveIntegerField(default=0)
    is_paid = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class LeaveApplication(models.Model):

    class Meta:
        permissions = [
            ("view_all_leaveapplication", "Can view all leave applications"),
        ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='leaves'
    )

    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.SET_NULL,
        null=True
    )

    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    applied_at = models.DateTimeField(auto_now_add=True)
    action_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.employee.name} - {self.leave_type.name}"


class TeacherAbsence(models.Model):
    SOURCE_CHOICES = [
        ('manual', 'Manual'),
        ('leave', 'Leave'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processed', 'Processed'),
        ('partial', 'Partial'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    teacher = models.ForeignKey('teacher_dashboard.Teacher', on_delete=models.CASCADE, related_name='automation_absences')
    absence_date = models.DateField()
    day = models.CharField(max_length=20)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='manual')
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.SET_NULL, null=True, blank=True, related_name='teacher_absences')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_teacher_absences')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('teacher', 'absence_date', 'source', 'leave_application')
        ordering = ['-absence_date', '-created_at']

    def __str__(self):
        return f"{self.teacher.name} absent on {self.absence_date}"


class TeacherAbsenceResult(models.Model):
    STATUS_CHOICES = [
        ('assigned', 'Assigned'),
        ('unassigned', 'Unassigned'),
        ('skipped', 'Skipped'),
        ('cancelled', 'Cancelled'),
    ]

    absence = models.ForeignKey(TeacherAbsence, on_delete=models.CASCADE, related_name='results')
    assigned_period = models.ForeignKey('AssignedPeriod', on_delete=models.CASCADE)
    fixture = models.ForeignKey(TeacherFixture, on_delete=models.SET_NULL, null=True, blank=True, related_name='automation_results')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    note = models.TextField(blank=True, default='')
    selection_score = models.IntegerField(default=0)
    selection_reason = models.TextField(blank=True, default='')
    candidate_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('absence', 'assigned_period')
        ordering = ['assigned_period__period__start_time', 'id']

    def __str__(self):
        return f"{self.absence} - {self.assigned_period} - {self.status}"


class TeacherNotification(models.Model):
    TYPE_CHOICES = [
        ('fixture_assigned', 'Fixture Assigned'),
        ('absence_covered', 'Absence Covered'),
        ('fixture_unassigned', 'Fixture Unassigned'),
    ]

    teacher = models.ForeignKey('teacher_dashboard.Teacher', on_delete=models.CASCADE, related_name='fixture_notifications')
    title = models.CharField(max_length=180)
    message = models.TextField()
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    related_fixture = models.ForeignKey(TeacherFixture, on_delete=models.SET_NULL, null=True, blank=True, related_name='teacher_notifications')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.teacher.name}: {self.title}"


class TeacherFixtureNotificationLog(models.Model):
    CHANNEL_CHOICES = [
        ('email', 'Email'),
        ('in_app', 'In App'),
        ('sms', 'SMS'),
        ('whatsapp', 'WhatsApp'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]

    fixture = models.ForeignKey(TeacherFixture, on_delete=models.CASCADE, null=True, blank=True, related_name='notification_logs')
    recipient_teacher = models.ForeignKey('teacher_dashboard.Teacher', on_delete=models.CASCADE, related_name='fixture_notification_logs')
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    error_message = models.TextField(blank=True, default='')
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient_teacher.name} {self.channel} {self.status}"


class TeacherAvailability(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('unavailable', 'Unavailable'),
        ('meeting', 'Meeting'),
        ('training', 'Training'),
        ('exam_duty', 'Exam Duty'),
        ('leave', 'Leave'),
        ('manual_block', 'Manual Block'),
    ]

    teacher = models.ForeignKey('teacher_dashboard.Teacher', on_delete=models.CASCADE, related_name='availability_records')
    date = models.DateField()
    period = models.ForeignKey(CreatePeriod, on_delete=models.SET_NULL, null=True, blank=True)
    availability_status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='unavailable')
    reason = models.CharField(max_length=255, blank=True, default='')
    source = models.CharField(max_length=50, blank=True, default='manual')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', 'teacher__name']

    def __str__(self):
        return f"{self.teacher.name} - {self.date} - {self.availability_status}"


class TeacherTeachingEligibility(models.Model):
    teacher = models.ForeignKey('teacher_dashboard.Teacher', on_delete=models.CASCADE, related_name='teaching_eligibilities')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    class_fk = models.ForeignKey(Class, on_delete=models.SET_NULL, null=True, blank=True)
    faculty_group = models.CharField(max_length=100, blank=True, default='')
    campus = models.CharField(max_length=100, blank=True, default='')
    priority = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('teacher', 'subject', 'class_fk', 'faculty_group', 'campus')
        ordering = ['teacher__name', 'subject__name']

    def __str__(self):
        return f"{self.teacher.name} - {self.subject.name}"


class SubjectSubstitutionRule(models.Model):
    source_subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='substitution_sources')
    eligible_subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='substitution_targets')
    priority = models.PositiveIntegerField(default=50)
    class_fk = models.ForeignKey(Class, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('source_subject', 'eligible_subject', 'class_fk')
        ordering = ['source_subject__name', 'priority']

    def __str__(self):
        return f"{self.source_subject.name} -> {self.eligible_subject.name}"


class TeacherFixtureCandidateLog(models.Model):
    DECISION_CHOICES = [
        ('selected', 'Selected'),
        ('eligible', 'Eligible'),
        ('excluded', 'Excluded'),
    ]

    absence = models.ForeignKey(TeacherAbsence, on_delete=models.CASCADE, related_name='candidate_logs')
    absence_result = models.ForeignKey(TeacherAbsenceResult, on_delete=models.SET_NULL, null=True, blank=True, related_name='candidate_logs')
    assigned_period = models.ForeignKey(AssignedPeriod, on_delete=models.CASCADE, related_name='candidate_logs')
    teacher = models.ForeignKey('teacher_dashboard.Teacher', on_delete=models.CASCADE, related_name='fixture_candidate_logs')
    decision = models.CharField(max_length=20, choices=DECISION_CHOICES)
    score = models.IntegerField(default=0)
    reason = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-score', 'teacher__name']

    def __str__(self):
        return f"{self.teacher.name} - {self.decision} - {self.score}"


class TeacherFixtureHandover(models.Model):
    fixture = models.OneToOneField(TeacherFixture, on_delete=models.CASCADE, related_name='handover')
    lesson_topic = models.CharField(max_length=255, blank=True, default='')
    instructions = models.TextField(blank=True, default='')
    homework = models.TextField(blank=True, default='')
    attachment = models.FileField(upload_to='fixture_handovers/', null=True, blank=True)
    submitted_by = models.ForeignKey('teacher_dashboard.Teacher', on_delete=models.SET_NULL, null=True, blank=True, related_name='submitted_fixture_handovers')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Handover for fixture {self.fixture_id}"

#===================================================================

from django.db import models
from django.utils.timezone import now
from django.contrib.auth.models import User



class AppraisalCycle(models.Model):
    name = models.CharField(max_length=120)  # "2026 Annual"
    start_date = models.DateField()
    end_date = models.DateField()
    is_open = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class GradePolicy(models.Model):
    """
    Convert ExamResult % -> A/B/C/D/E/F
    """
    name = models.CharField(max_length=120, default="Default Grade Policy")
    a_min = models.FloatField(default=80)
    b_min = models.FloatField(default=70)
    c_min = models.FloatField(default=60)
    d_min = models.FloatField(default=50)
    e_min = models.FloatField(default=40)

    def __str__(self):
        return self.name


class KpiTemplate(models.Model):
    name = models.CharField(max_length=120)
    cycle = models.ForeignKey(AppraisalCycle, on_delete=models.CASCADE, related_name="kpi_templates")
    grade_policy = models.ForeignKey(GradePolicy, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.cycle.name})"

from django.db import models
from django.utils.text import slugify
from django.utils.timezone import now


class KpiTemplate(models.Model):
    name = models.CharField(max_length=120)
    cycle = models.ForeignKey("AppraisalCycle", on_delete=models.CASCADE, related_name="kpi_templates")
    grade_policy = models.ForeignKey("GradePolicy", on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.cycle.name})"


class KpiRule(models.Model):
    SCORING_METHOD = [
        ("linear", "Linear (actual/target)"),
        ("threshold", "Threshold (bands)"),
    ]

    # ✅ Auto KPIs fixed (same as your current)
    AUTO_KPI_KEYS = [
        ("pass_rate", "Pass Rate (%)"),
        ("ab_rate", "A+B Rate (%)"),
        ("a_rate", "A Rate (%)"),
        ("results_count", "Results Count"),
        ("classes_taught", "Classes Taught (unique class-section-subject)"),
        ("fixtures_substitute", "Substitute Fixtures Count"),
        ("fixtures_absent", "Absent Fixtures Count"),
        ("workshops_attended", "Workshops Attended"),
        ("trainings_given", "Trainings Given"),
        ("extra_curricular", "Extra Curricular Activities"),
        ("diary_submissions", "Diary Submission Regularity"),
        ("lesson_plans_created", "Lesson Plan Completion"),
        ("lesson_days_created", "Lesson Days Generated"),
        ("lecture_notes_uploaded", "Lecture Notes Upload"),
        ("assignments_uploaded", "Assignments Uploaded"),
        ("quizzes_created", "Quizzes Created"),
    ]

    template = models.ForeignKey(KpiTemplate, on_delete=models.CASCADE, related_name="rules")

    # show name
    title = models.CharField(max_length=255)

    # ✅ IMPORTANT:
    # Auto KPI rules => kpi_key will be one of fixed auto keys above
    # Manual KPI rules => kpi_key will be generated from title (conducting_workshop etc.)
    kpi_key = models.CharField(max_length=120, db_index=True)

    # ✅ manual flag
    is_manual = models.BooleanField(default=False)

    # optional: keep stable slug (same as kpi_key for manual)
    slug = models.CharField(max_length=180, null=True, blank=True, db_index=True)

    weight = models.FloatField(default=10)       # 0..100 contribution
    target_value = models.FloatField(default=0)
    scoring_method = models.CharField(max_length=20, choices=SCORING_METHOD, default="linear")

    thresholds = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # ✅ unique per template (so 1 template ke andar duplicate key na banay)
        unique_together = ("template", "kpi_key")

    def save(self, *args, **kwargs):
        # ✅ Manual KPI: generate kpi_key ONCE from title (spaces -> underscore)
        # Title edit allowed, but key stable rahe (once generated, change nahi hoga)
        if self.is_manual:
            # if key missing -> generate
            if not (self.kpi_key or "").strip():
                base = slugify(self.title or "").replace("-", "_").strip("_")
                if not base:
                    base = "manual_kpi"

                # auto keys se clash na ho
                auto_keys = {k for k, _ in self.AUTO_KPI_KEYS}
                if base in auto_keys:
                    base = f"{base}_manual"

                key = base
                i = 1
                while KpiRule.objects.filter(template=self.template, kpi_key=key).exclude(pk=self.pk).exists():
                    i += 1
                    key = f"{base}_{i}"

                self.kpi_key = key

            # slug = kpi_key (manual)
            if not (self.slug or "").strip():
                self.slug = (self.kpi_key or "").strip()

            # default manual target = 10 (0-10 score)
            if not self.target_value or float(self.target_value) <= 0:
                self.target_value = 10

        else:
            # Auto KPI: slug optional blank
            if self.slug:
                self.slug = None

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.kpi_key})"



class TeacherAppraisalSubmission(models.Model):
    STATUS = [("draft", "Draft"), ("submitted", "Submitted")]

    teacher = models.ForeignKey("teacher_dashboard.Teacher", on_delete=models.CASCADE)
    cycle = models.ForeignKey(AppraisalCycle, on_delete=models.CASCADE)
    kpi_template = models.ForeignKey(KpiTemplate, on_delete=models.SET_NULL, null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS, default="draft")
    submitted_at = models.DateTimeField(null=True, blank=True)

    # auto snapshots (from your models)
    auto_metrics = models.JSONField(default=dict, blank=True)      # numeric metrics used by KPIs/ML
    results_summary = models.JSONField(default=dict, blank=True)   # A/B/C/D/E/F breakdown etc.

    # teacher manual
    achievements = models.TextField(blank=True)
    challenges = models.TextField(blank=True)
    improvement_plan = models.TextField(blank=True)
    evidence_links = models.JSONField(default=list, blank=True)
    manual_ratings = models.JSONField(default=dict, blank=True)


    # admin final label (THIS is what we train RF on)
    final_band = models.CharField(
        max_length=30,
        blank=True,
        choices=[
            ("Outstanding", "Outstanding"),
            ("Excellent", "Excellent"),
            ("Good", "Good"),
            ("Fair", "Fair"),
            ("Average", "Average"),
            ("Below Average", "Below Average"),
        ],
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("teacher", "cycle")

    def __str__(self):
        return f"{self.teacher.name} - {self.cycle.name}"


# admin_panel/models.py  (TeacherActivity model update)

from django.db import models

class TeacherActivity(models.Model):
    ACT_TYPE = [
        ("EXTRA", "Extra Curricular"),
        ("WORKSHOP_ATTEND", "Workshop Attended"),
        ("TRAINING_GIVEN", "Training Given"),
    ]

    ENTRY_KIND = [
        ("ACTIVITY", "Activity / Training / Workshop"),
        ("MANUAL_KPI", "Manual KPI (Auto Rated)"),
    ]

    submission = models.ForeignKey(
        "admin_panel.TeacherAppraisalSubmission",
        on_delete=models.CASCADE,
        related_name="appraisal_activities",
    )

    entry_kind = models.CharField(max_length=20, choices=ENTRY_KIND, default="ACTIVITY")

    # normal activities (old)
    activity_type = models.CharField(max_length=30, choices=ACT_TYPE, blank=True, default="")

    # manual KPI mapping (NEW)
    manual_rule = models.ForeignKey(
        "admin_panel.KpiRule",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="activity_evidences",
    )

    title = models.CharField(max_length=200)
    date = models.DateField(null=True, blank=True)
    hours = models.FloatField(default=0, blank=True)
    notes = models.TextField(blank=True)

    # optional: persist computed score per row (NEW)
    system_score = models.IntegerField(null=True, blank=True)

    def __str__(self):
        if self.entry_kind == "MANUAL_KPI" and self.manual_rule:
            return f"Manual KPI: {self.manual_rule.title} - {self.title}"
        return f"{self.activity_type} - {self.title}"


class AppraisalScore(models.Model):
    submission = models.OneToOneField(TeacherAppraisalSubmission, on_delete=models.CASCADE, related_name="score")
    total_score = models.FloatField(default=0)
    band = models.CharField(max_length=30, default="Pending")   # system band
    breakdown = models.JSONField(default=dict, blank=True)
    predicted_band = models.CharField(max_length=30, blank=True)  # RF prediction
    generated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.submission.teacher.name} - {self.band} ({self.total_score})"


class MLModelArtifact(models.Model):
    """
    Stores trained RandomForest model info (path on disk) + feature keys used.
    """
    algorithm = models.CharField(max_length=50, default="RandomForest")
    model_path = models.CharField(max_length=255)
    trained_at = models.DateTimeField(default=now)
    is_active = models.BooleanField(default=True)

    # ✅ NEW: model kis feature list pe train hua tha
    feature_keys = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"{self.algorithm} ({self.trained_at.date()})"


from django.db import models

class AcademicCalendarEvent(models.Model):
    EVENT_TYPES = (
        ("gazetted", "Gazetted Holidays"),
        ("college_assess", "College Assess/Admin"),
        ("college_event", "College Events"),
        ("mat_camb_assess", "Mat/Camb Assess"),
        ("pre_primary", "Pre-Primary"),
        ("speaker_train", "Speaker/Ses/Train"),
        ("eca_cca", "ECA/CCA"),
        ("ptm", "PTM"),
        ("other", "Other"),
    )

    title = models.CharField(max_length=250)
    start = models.DateTimeField()
    end = models.DateTimeField(null=True, blank=True)

    all_day = models.BooleanField(default=False)
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES, default="other")

    streams = models.CharField(max_length=250, blank=True, default="")
    responsibility = models.CharField(max_length=250, blank=True, default="")

    description = models.TextField(blank=True, default="")
    color = models.CharField(max_length=20, blank=True, default="")  # optional override

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start"]

    def __str__(self):
        return f"{self.title} - {self.start}"




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

class ProcurementCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Procurement categories"

    def __str__(self):
        return self.name

class Vendor(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
    ]

    name = models.CharField(max_length=120, unique=True)
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

class PurchaseRequest(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("pending", "Pending Approval"),
        ("approved", "Approved"),
        ("ordered", "Ordered"),
        ("received", "Received"),
        ("rejected", "Rejected"),
    ]
    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("normal", "Normal"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]

    title = models.CharField(max_length=160)
    category = models.ForeignKey(ProcurementCategory, on_delete=models.SET_NULL, null=True, blank=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True, blank=True)
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    needed_by = models.DateField(null=True, blank=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="normal")
    estimated_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

class InventoryItem(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
    ]

    name = models.CharField(max_length=140)
    sku = models.CharField(max_length=60, unique=True, null=True, blank=True)
    category = models.ForeignKey(ProcurementCategory, on_delete=models.SET_NULL, null=True, blank=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=0)
    unit = models.CharField(max_length=30, default="pcs")
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

class StockMovement(models.Model):
    MOVEMENT_CHOICES = [
        ("in", "Stock In"),
        ("out", "Stock Out"),
        ("adjustment", "Adjustment"),
    ]

    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="stock_movements")
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_CHOICES)
    quantity = models.PositiveIntegerField(default=1)
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.item} - {self.get_movement_type_display()} ({self.quantity})"

class Vehicle(models.Model):
    TYPE_CHOICES = [
        ("bus", "Bus"),
        ("van", "Van"),
        ("car", "Car"),
        ("other", "Other"),
    ]
    STATUS_CHOICES = [
        ("active", "Active"),
        ("maintenance", "Under Maintenance"),
        ("inactive", "Inactive"),
    ]

    vehicle_no = models.CharField(max_length=50, unique=True)
    vehicle_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="bus")
    capacity = models.PositiveIntegerField(default=0)
    driver_name = models.CharField(max_length=100, blank=True)
    driver_phone = models.CharField(max_length=30, blank=True)
    registration_expiry = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["vehicle_no"]

    def __str__(self):
        return self.vehicle_no

class RouteVehicleAssignment(models.Model):
    route = models.ForeignKey(TransportRoute, on_delete=models.CASCADE, related_name="vehicle_assignments")
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="route_assignments")
    driver_name = models.CharField(max_length=100, blank=True)
    start_date = models.DateField(default=date.today)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-is_active", "route__route_name"]

    def __str__(self):
        return f"{self.route} - {self.vehicle}"


class TransportTrip(models.Model):
    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("on_time", "On Time"),
        ("delayed", "Delayed"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    route = models.ForeignKey(TransportRoute, on_delete=models.CASCADE, related_name="trips")
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="trips")
    service_date = models.DateField(default=date.today)
    scheduled_departure = models.TimeField()
    actual_departure = models.TimeField(null=True, blank=True)
    students_transported = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="scheduled")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-service_date", "scheduled_departure"]

    def __str__(self):
        return f"{self.route} - {self.vehicle} ({self.service_date})"

class VehicleMaintenance(models.Model):
    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="maintenance_records")
    maintenance_type = models.CharField(max_length=100)
    service_date = models.DateField()
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="scheduled")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-service_date"]

    def __str__(self):
        return f"{self.vehicle} - {self.maintenance_type}"

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

    def __str__(self):
        return self.full_name

class StudentFeeAssignment(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='fee_assignment')
    fee_plan = models.ForeignKey(FeePlan, on_delete=models.PROTECT)
    transport_route = models.ForeignKey(TransportRoute, on_delete=models.SET_NULL, null=True, blank=True)
    scholarship = models.ForeignKey(Scholarship, on_delete=models.SET_NULL, null=True, blank=True)

class StudentLedger(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    description = models.CharField(max_length=255)
    debit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    credit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    reference_no = models.CharField(max_length=50, blank=True, null=True)

class StudentBalance(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE)
    outstanding_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

# Add this to your models.py - Update the FeeVoucher model

class FeeVoucher(models.Model):
    STATUS_CHOICES = [('UNPAID', 'Unpaid'), ('PARTIAL', 'Partial'), ('PAID', 'Paid'), ('OVERDUE', 'Overdue')]
    voucher_no = models.CharField(max_length=50, unique=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
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
    status = models.CharField(max_length=20)
    error_message = models.TextField(null=True, blank=True)

class NotificationQueue(models.Model):
    STATUS_CHOICES = (('PENDING', 'Pending'), ('SENT', 'Sent'), ('FAILED', 'Failed'))
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=10, choices=(('SMS', 'SMS'), ('EMAIL', 'Email')))
    content = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

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

    def __str__(self):
        return f"{self.name} ({self.teacher_id})"

class SalaryStructure(models.Model):
    teacher = models.OneToOneField(Teacher, on_delete=models.CASCADE)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)

class SalaryVoucher(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
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

# --- ADMIN DASHBOARD HELPER ---
def get_dashboard_stats():
    return {
        "total_students": Student.objects.count(),
        "monthly_revenue": Transaction.objects.filter(type='INCOME', date__month=date.today().month).aggregate(Sum('amount'))['amount__sum'] or 0,
        "total_expenses": Transaction.objects.filter(type='EXPENSE').aggregate(Sum('amount'))['amount__sum'] or 0,
        "high_risk_students": StudentPerformance.objects.filter(risk_level='HIGH').count(),
        "total_teachers": Teacher.objects.filter(is_active=True).count(),
        "total_staff": Staff.objects.filter(is_active=True).count(),
        "recent_transactions": Transaction.objects.all().order_by('-date')[:5]
    }

# --- SIGNALS ---
@receiver(post_save, sender=FeeVoucher)
def create_ledger_entry(sender, instance, created, **kwargs):
    if created:
        StudentLedger.objects.create(
            student=instance.student,
            description=f"Fee Voucher Generated: {instance.voucher_no}",
            debit=instance.net_amount,
            balance=instance.net_amount,
            reference_no=instance.voucher_no
        )
        balance_obj, _ = StudentBalance.objects.get_or_create(student=instance.student)
        balance_obj.outstanding_amount += Decimal(str(instance.net_amount))
        balance_obj.save()
        
        
        
