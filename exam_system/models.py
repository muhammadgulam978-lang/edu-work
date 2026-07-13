from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


from teacher_dashboard.models import Teacher
from student_profile.models import Student
from admin_panel.models import (
    Class, Section, Subject,
    AcademicYear
)


# =============================================================
# QUESTION BANK
# =============================================================

class QuestionBank(models.Model):
    subject        = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='question_banks')
    class_fk       = models.ForeignKey(Class, on_delete=models.CASCADE)
    academic_year  = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    created_by     = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('subject', 'class_fk', 'academic_year')

    def __str__(self):
        return f"{self.subject.name} - Class {self.class_fk.class_name}"


class Question(models.Model):
    QUESTION_TYPES = [
        ('MCQ',        'Multiple Choice'),
        ('SHORT',      'Short Question'),
        ('LONG',       'Long Question'),
        ('CONCEPTUAL', 'Conceptual'),
        ('CASE_BASED', 'Case Based'),
        ('PRACTICAL',  'Practical'),
    ]
    DIFFICULTY_LEVELS = [
        ('EASY',   'Easy'),
        ('MEDIUM', 'Medium'),
        ('HARD',   'Hard'),
    ]
    BLOOM_LEVELS = [
        ('REMEMBER',   'Remember'),
        ('UNDERSTAND', 'Understand'),
        ('APPLY',      'Apply'),
        ('ANALYZE',    'Analyze'),
        ('EVALUATE',   'Evaluate'),
        ('CREATE',     'Create'),
    ]

    bank           = models.ForeignKey(QuestionBank, on_delete=models.CASCADE, related_name='questions')
    question_type  = models.CharField(max_length=20, choices=QUESTION_TYPES)
    text           = models.TextField()
    marks          = models.PositiveIntegerField(default=1)
    difficulty     = models.CharField(max_length=10, choices=DIFFICULTY_LEVELS, default='MEDIUM')
    bloom_level    = models.CharField(max_length=20, choices=BLOOM_LEVELS, default='UNDERSTAND')
    topic_tag      = models.CharField(max_length=100, blank=True)
    option_a       = models.CharField(max_length=255, blank=True, null=True)
    option_b       = models.CharField(max_length=255, blank=True, null=True)
    option_c       = models.CharField(max_length=255, blank=True, null=True)
    option_d       = models.CharField(max_length=255, blank=True, null=True)
    correct_answer = models.TextField(blank=True)
    ai_generated   = models.BooleanField(default=False)
    human_approved = models.BooleanField(default=False)
    approved_by    = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='approved_questions'
    )
    created_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.question_type}] {self.text[:60]}"


# =============================================================
# EXAM PLAN
# =============================================================

class ExamPlan(models.Model):
    EXAM_TYPES = [
        ('MONTHLY', 'Monthly Test'),
        ('MIDTERM', 'Mid Term'),
        ('FINAL',   'Final Term'),
        ('WEEKLY',  'Weekly Test'),
    ]

    title          = models.CharField(max_length=200)
    academic_year  = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    exam_type      = models.CharField(max_length=20, choices=EXAM_TYPES)
    class_fk       = models.ForeignKey(Class, on_delete=models.CASCADE)
    start_date     = models.DateField()
    end_date       = models.DateField()
    created_by     = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    is_published   = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} - {self.exam_type}"


class ExamSchedule(models.Model):
    exam_plan   = models.ForeignKey(ExamPlan, on_delete=models.CASCADE, related_name='schedules')
    subject     = models.ForeignKey(Subject, on_delete=models.CASCADE)
    exam_date   = models.DateField()
    start_time  = models.TimeField()
    end_time    = models.TimeField()
    room        = models.CharField(max_length=50, blank=True)

    class Meta:
        unique_together = ('exam_plan', 'subject')

    def __str__(self):
        return f"{self.subject.name} - {self.exam_date}"


class PaperBlueprint(models.Model):
    exam_plan     = models.ForeignKey(ExamPlan, on_delete=models.CASCADE, related_name='blueprints')
    subject       = models.ForeignKey(Subject, on_delete=models.CASCADE)
    total_marks   = models.PositiveIntegerField(default=100)
    passing_marks = models.PositiveIntegerField(default=40)
    created_by    = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Blueprint: {self.subject.name} - {self.exam_plan.title}"


class BlueprintRule(models.Model):
    blueprint      = models.ForeignKey(PaperBlueprint, on_delete=models.CASCADE, related_name='rules')
    question_type  = models.CharField(max_length=20, choices=Question.QUESTION_TYPES)
    count          = models.PositiveIntegerField()
    marks_each     = models.PositiveIntegerField()
    easy_percent   = models.PositiveIntegerField(default=30)
    medium_percent = models.PositiveIntegerField(default=50)
    hard_percent   = models.PositiveIntegerField(default=20)

    def __str__(self):
        return f"{self.question_type} x{self.count}"


class GeneratedPaper(models.Model):
    SET_CHOICES = [
        ('A',      'Set A'),
        ('B',      'Set B'),
        ('C',      'Set C'),
        ('SINGLE', 'Single Paper'),
    ]
    STATUS_CHOICES = [
        ('DRAFT',    'Draft'),
        ('REVIEW',   'Under Review'),
        ('APPROVED', 'Approved'),
        ('LOCKED',   'Locked & Ready'),
        ('REJECTED', 'Rejected'),
    ]

    blueprint      = models.ForeignKey(PaperBlueprint, on_delete=models.CASCADE, related_name='papers')
    section        = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True, blank=True)
    paper_set      = models.CharField(max_length=10, choices=SET_CHOICES, default='SINGLE')
    questions      = models.ManyToManyField(Question, related_name='papers', blank=True)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    unlock_time    = models.DateTimeField(null=True, blank=True)
    pdf_file       = models.FileField(upload_to='exam_papers/', null=True, blank=True)
    watermark_text = models.CharField(max_length=200, blank=True)
    generated_by   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='generated_papers')
    created_at     = models.DateTimeField(auto_now_add=True)

    def is_unlocked(self):
        if not self.unlock_time:
            return True
        return timezone.now() >= self.unlock_time

    def __str__(self):
        return f"{self.blueprint.subject.name} - {self.paper_set} [{self.status}]"


class PaperApproval(models.Model):
    STAGE_CHOICES = [
    ('TEACHER', 'Teacher'),
    ('COORDINATOR', 'Subject Coordinator'),
    ('ACADEMIC_HEAD', 'HOD / Academic Head'),
    ('CONTROLLER', 'Examination Controller'),
]
    STATUS_CHOICES = [
        ('PENDING',  'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    paper       = models.ForeignKey(GeneratedPaper, on_delete=models.CASCADE, related_name='approvals')
    stage       = models.CharField(max_length=20, choices=STAGE_CHOICES)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    status      = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    remarks     = models.TextField(blank=True)
    timestamp   = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('paper', 'stage')

    def __str__(self):
        return f"{self.paper} | {self.stage} → {self.status}"


class PaperAccessLog(models.Model):
    paper       = models.ForeignKey(GeneratedPaper, on_delete=models.CASCADE)
    accessed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action      = models.CharField(max_length=20, choices=[
        ('VIEW',     'Viewed'),
        ('DOWNLOAD', 'Downloaded'),
        ('PRINT',    'Printed'),
    ])
    ip_address  = models.GenericIPAddressField(null=True, blank=True)
    timestamp   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.accessed_by} - {self.action} - {self.timestamp:%Y-%m-%d %H:%M}"


# =============================================================
# CONDUCT & MARKING
# =============================================================

class ExamSeatingPlan(models.Model):
    schedule    = models.ForeignKey(ExamSchedule, on_delete=models.CASCADE, related_name='seating_plans')
    student     = models.ForeignKey(Student, on_delete=models.CASCADE)
    seat_number = models.CharField(max_length=20)
    room        = models.CharField(max_length=50, blank=True)

    class Meta:
        unique_together = ('schedule', 'student')

    def __str__(self):
        return f"{self.student.name} - Seat {self.seat_number}"


class InvigilatorDuty(models.Model):
    schedule = models.ForeignKey(ExamSchedule, on_delete=models.CASCADE, related_name='invigilator_duties')
    teacher  = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    room     = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.teacher.name} - {self.schedule}"


class ExamAttendance(models.Model):
    schedule  = models.ForeignKey(ExamSchedule, on_delete=models.CASCADE)
    student   = models.ForeignKey(Student, on_delete=models.CASCADE)
    status    = models.CharField(max_length=10, choices=[
        ('PRESENT', 'Present'),
        ('ABSENT',  'Absent'),
        ('LATE',    'Late'),
    ], default='ABSENT')
    marked_by = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True)
    marked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('schedule', 'student')

    def __str__(self):
        return f"{self.student} - {self.status}"


class AnswerSheet(models.Model):
    schedule     = models.ForeignKey(ExamSchedule, on_delete=models.CASCADE)
    student      = models.ForeignKey(Student, on_delete=models.CASCADE)
    paper        = models.ForeignKey(GeneratedPaper, on_delete=models.SET_NULL, null=True)
    scanned_file = models.FileField(upload_to='answer_sheets/', null=True, blank=True)
    is_submitted = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('schedule', 'student')

    def __str__(self):
        return f"{self.student.name} - {self.schedule.subject.name}"


class QuestionScore(models.Model):
    answer_sheet    = models.ForeignKey(AnswerSheet, on_delete=models.CASCADE, related_name='scores')
    question        = models.ForeignKey(Question, on_delete=models.CASCADE)
    ai_score        = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    ai_feedback     = models.TextField(blank=True)
    teacher_score   = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    teacher_remarks = models.TextField(blank=True)
    verified_by     = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='verified_scores'
    )

    @property
    def final_score(self):
        return self.teacher_score if self.teacher_score is not None else self.ai_score

    def __str__(self):
        return f"{self.answer_sheet.student.name} Q{self.question.id}: {self.final_score}"


class CentralizedResult(models.Model):
    GRADE_CHOICES = [
        ('A+', 'A+'), ('A', 'A'), ('B', 'B'),
        ('C',  'C'),  ('D', 'D'), ('F', 'F'),
    ]

    answer_sheet     = models.OneToOneField(AnswerSheet, on_delete=models.CASCADE, related_name='result')
    total_marks      = models.PositiveIntegerField()
    obtained_marks   = models.DecimalField(max_digits=6, decimal_places=2)
    percentage       = models.DecimalField(max_digits=5, decimal_places=2)
    grade            = models.CharField(max_length=3, choices=GRADE_CHOICES)
    is_pass          = models.BooleanField(default=False)
    class_position   = models.PositiveIntegerField(null=True, blank=True)
    section_position = models.PositiveIntegerField(null=True, blank=True)
    remarks          = models.TextField(blank=True)
    compiled_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.answer_sheet.student.name} - {self.percentage}% ({self.grade})"
    

is_final = models.BooleanField(default=False)

final_approved_by = models.ForeignKey(
    User,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='final_papers'
)

final_approved_at = models.DateTimeField(
    null=True,
    blank=True
)    