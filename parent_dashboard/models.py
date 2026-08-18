# from django.db import models
# from django.contrib.auth.models import User
# from phonenumber_field.modelfields import PhoneNumberField

# class Parent(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
#     full_name = models.CharField(max_length=100)
#     phone = models.CharField(max_length=15, null=True, blank=True)
#     email = models.EmailField(null=True, blank=True)
#     address = models.TextField(null=True, blank=True)
#     occupation = models.CharField(max_length=100, null=True, blank=True)
#     students = models.ManyToManyField('student_profile.Student', related_name='student_profile')

#     def __str__(self):
#         return self.full_name

#     def delete(self, *args, **kwargs):  
#         if self.user:
#             self.user.delete()
#         super().delete(*args, **kwargs)




from django.db import models
from django.contrib.auth.models import User


class Parent(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    occupation = models.CharField(max_length=100, blank=True, null=True)

    students = models.ManyToManyField(
        'student_profile.Student',
        related_name='parents'
    )

    def __str__(self):
        return self.full_name

    def delete(self, *args, **kwargs):
        if self.user:
            self.user.delete()
        super().delete(*args, **kwargs)


class StudentGuardian(models.Model):
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE, related_name='guardian_links')
    student = models.ForeignKey(
        'student_profile.Student', on_delete=models.CASCADE, related_name='guardian_links'
    )
    relationship = models.CharField(max_length=40)
    is_primary = models.BooleanField(default=False)
    portal_access = models.BooleanField(default=True)
    notifications_enabled = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['parent', 'student'], name='unique_parent_student_guardian'
            ),
            models.UniqueConstraint(
                fields=['student'], condition=models.Q(is_primary=True),
                name='one_primary_guardian_per_student',
            ),
        ]

    def __str__(self):
        return f"{self.parent.full_name} - {self.student.name} ({self.relationship})"
