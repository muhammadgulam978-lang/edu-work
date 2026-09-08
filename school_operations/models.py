from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class CampusRecord(models.Model):
    campus = models.ForeignKey('access_control.Campus', on_delete=models.PROTECT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    archived = models.BooleanField(default=False)

    class Meta:
        abstract = True


class LibraryBook(CampusRecord):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=200, blank=True)
    isbn = models.CharField(max_length=32, blank=True)
    copies = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.title


class LibraryLoan(CampusRecord):
    book = models.ForeignKey(LibraryBook, on_delete=models.PROTECT, related_name='loans')
    student = models.ForeignKey('student_profile.Student', on_delete=models.PROTECT)
    due_on = models.DateField()
    returned_at = models.DateTimeField(null=True, blank=True)
    return_condition = models.CharField(max_length=200, blank=True)
    fine = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['book', 'student'], condition=models.Q(returned_at__isnull=True),
                                               name='one_open_loan_per_book_student')]

    def __str__(self):
        return f'{self.book.title} — {self.student.name}'


class LabAsset(CampusRecord):
    name = models.CharField(max_length=200)
    laboratory = models.CharField(max_length=100)
    inventory_code = models.CharField(max_length=50)
    quantity = models.PositiveIntegerField(default=1)
    safety_notes = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['campus', 'inventory_code'], name='campus_lab_inventory_code')]

    def __str__(self):
        return f'{self.name} ({self.laboratory})'


class LabBooking(CampusRecord):
    asset = models.ForeignKey(LabAsset, on_delete=models.PROTECT, related_name='bookings')
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    purpose = models.CharField(max_length=255)
    status = models.CharField(max_length=12, default='pending', choices=[
        ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('cancelled', 'Cancelled')])
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
                                   related_name='decided_lab_bookings')

    def clean(self):
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError('The booking must end after it starts.')
        if self.asset_id and self.campus_id and self.asset.campus_id != self.campus_id:
            raise ValidationError('Equipment must belong to the selected campus.')

    def __str__(self):
        return f'{self.asset.name} — {self.starts_at:%Y-%m-%d %H:%M}'


class HealthCase(CampusRecord):
    student = models.ForeignKey('student_profile.Student', on_delete=models.PROTECT)
    category = models.CharField(max_length=20, choices=[
        ('clinic', 'Clinic'), ('counselling', 'Counselling'), ('safeguarding', 'Safeguarding')])
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                    related_name='assigned_health_cases')
    consent_reference = models.CharField(max_length=255)
    encrypted_notes = models.TextField()
    follow_up_on = models.DateField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        # Keep clinical details out of labels and general administrator widgets.
        return f'Case {self.pk}'
