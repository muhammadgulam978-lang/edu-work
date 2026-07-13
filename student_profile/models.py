# student_profile/models.py
# ─── FIXED VERSION ───────────────────────────────────────

from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from django.contrib.auth.models import User
import datetime
import os


def filepath(request, filename):
    old_filename = filename
    timeNow = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    filename = "%s_%s" % (timeNow, old_filename)
    return os.path.join('uploads/', filename)


GENDER_CHOICES = [
    ('Male',   'Male'),
    ('Female', 'Female'),
    ('Other',  'Other'),
]


class Student(models.Model):
    academic_year = models.ForeignKey(
        'admin_panel.AcademicYear', on_delete=models.SET_NULL,
        null=True, blank=True
    )
    user        = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    student_id  = models.CharField(max_length=20, unique=True)
    name        = models.CharField(max_length=100)
    father_name = models.CharField(max_length=100)
    mother_name = models.CharField(max_length=100)
    class_fk    = models.ForeignKey(
        'admin_panel.Class', on_delete=models.SET_NULL,
        null=True, blank=True
    )
    section     = models.ForeignKey(
        'admin_panel.Section', on_delete=models.SET_NULL,
        null=True, blank=True
    )
    roll_no       = models.CharField(max_length=100)
    phone         = PhoneNumberField(blank=True, null=True)
    gender        = models.CharField(max_length=10, choices=GENDER_CHOICES, default='Male')
    date_of_birth = models.DateField()
    email         = models.EmailField(unique=True)
    photo         = models.ImageField(upload_to='student_photos/', blank=True, null=True)

    def __str__(self):
        # ✅ FIX: class_name ki jagah class_fk use karo
        class_name = self.class_fk.class_name if self.class_fk else 'No Class'
        return f"{self.name} - Class {class_name}"

    def delete(self, *args, **kwargs):
        if self.user:
            self.user.delete()
        super().delete(*args, **kwargs)


# ─────────────────────────────────────────────────────────

class AssignmentSubmission(models.Model):
    assignment  = models.ForeignKey('teacher_dashboard.Assignment', on_delete=models.CASCADE)
    student     = models.ForeignKey(Student, on_delete=models.CASCADE)
    file        = models.FileField(upload_to='assignment_submissions/')
    submitted_at = models.DateTimeField(auto_now_add=True)
    marks       = models.IntegerField(null=True, blank=True)
    feedback    = models.TextField(blank=True)

    def __str__(self):
        return f"{self.student.name} - {self.assignment.title}"


class QuizSubmission(models.Model):
    quiz           = models.ForeignKey('teacher_dashboard.Quiz', on_delete=models.CASCADE)
    student        = models.ForeignKey(Student, on_delete=models.CASCADE)
    submitted_file = models.FileField(upload_to='quiz_submissions/')
    submitted_at   = models.DateTimeField(auto_now_add=True)
    marks          = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.student.name} - {self.quiz}"