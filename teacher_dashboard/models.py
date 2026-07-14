from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from django.contrib.auth.models import User
from admin_panel.models import Subject
from multiselectfield import MultiSelectField
from django.utils.timezone import now
import os
import datetime


def filepath(request, filename):
    old_filename = filename
    timeNow = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    filename = "%s_%s" % (timeNow, old_filename)
    return os.path.join('uploads/', filename)

class Teacher(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    FACULTY_CHOICES = [
        ('Pre-Primary', 'Pre-Primary'),
        ('Junior Section', 'Junior Section'),
        ('Senior Section', 'Senior Section'),
        ('Pre-o level', 'Pre-o level'),
        ('O level', 'O level'),
    ]
    QUALIFICATION_CHOICES = [
        ('PhD', 'PhD'),
        ('Masters', 'Masters'),
        ('Bachelor', 'Bachelor'),
        ('Diploma', 'Diploma'),
        ('Matric', 'Matric'),
        ('Intermediate', 'Intermediate'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    employee = models.OneToOneField('admin_panel.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='teacher_profile')
    image = models.ImageField(upload_to=filepath, null=True, blank=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = PhoneNumberField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female')],)
    date_of_birth = models.DateField(null=True, blank=True)
    qualification = models.CharField(max_length=50, choices=QUALIFICATION_CHOICES, default='Matric')
    experience = models.PositiveIntegerField(blank=True, null=True, help_text="Years of teaching experience")
    is_merge = models.BooleanField(default=False)
    Address = models.CharField(max_length=50, blank=True, null=True)
    faculty_group = MultiSelectField(choices=FACULTY_CHOICES, max_length=200)
    department = models.CharField(max_length=100, blank=True, null=True)
    subjects = models.ManyToManyField(Subject, related_name='teachers', blank=True)
    image = models.ImageField(upload_to='teacher_images/', null=True, blank=True)
    joining_date = models.DateField(default=now, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    

    def __str__(self):
        return self.name

    def delete(self, *args, **kwargs):
        if self.user:
            self.user.delete()
        super().delete(*args, **kwargs)


from django.db import models
from student_profile.models import Student
from admin_panel.models import Class, Section, AssignedPeriod
from django.utils import timezone
class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)

    date = models.DateField(default=timezone.now)

    status_choices = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('leave', 'Leave'),
    ]
    status = models.CharField(max_length=10, choices=status_choices)

    class_fk = models.ForeignKey(
        Class,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    section = models.ForeignKey(
        Section,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    period = models.ForeignKey(
        AssignedPeriod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # ✅ NEW FIELD
    marked_by = models.ForeignKey(
        Teacher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marked_attendance"
    )

    class Meta:
        unique_together = ('student', 'date', 'period')

    def __str__(self):
        return f"{self.student.name} - {self.date} - {self.status}"
# models.py
class LectureNote(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    class_fk = models.ForeignKey(Class, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='lecture_notes/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.subject.name})"
    


class Assignment(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    class_fk = models.ForeignKey(Class, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='assignments/')
    due_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.subject.name}"


class Quiz(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    class_fk = models.ForeignKey(Class, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='quizzes/')
    due_date = models.DateField()



