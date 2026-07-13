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
