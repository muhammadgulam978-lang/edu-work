from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TicketCategory(TimeStampedModel):
    code = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    student_enabled = models.BooleanField(default=True)
    parent_enabled = models.BooleanField(default=True)
    teacher_enabled = models.BooleanField(default=True)
    confidential_by_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['department', 'name']
        verbose_name_plural = 'Ticket categories'

    def __str__(self):
        return f'{self.name} · {self.department}'


class SLAPolicy(TimeStampedModel):
    PRIORITIES = [('LOW', 'Low'), ('NORMAL', 'Normal'), ('HIGH', 'High'), ('URGENT', 'Urgent'),
                  ('CRITICAL', 'Critical')]
    category = models.ForeignKey(TicketCategory, null=True, blank=True, on_delete=models.CASCADE,
                                 related_name='sla_policies')
    priority = models.CharField(max_length=10, choices=PRIORITIES)
    first_response_hours = models.PositiveIntegerField(default=24)
    resolution_hours = models.PositiveIntegerField(default=72)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['category', 'priority'], name='helpdesk_unique_sla_policy')]
        ordering = ['priority']

    def __str__(self):
        return f'{self.category or "Default"} · {self.get_priority_display()}'


class Ticket(TimeStampedModel):
    TYPES = [('COMPLAINT', 'Complaint'), ('ENQUIRY', 'Enquiry'), ('REQUEST', 'Service request')]
    ROLES = [('STUDENT', 'Student'), ('PARENT', 'Parent'), ('TEACHER', 'Teacher'), ('STAFF', 'Staff')]
    PRIORITIES = SLAPolicy.PRIORITIES
    PRIVACY = [('NORMAL', 'Normal'), ('CONFIDENTIAL', 'Confidential'), ('SAFEGUARDING', 'Safeguarding')]
    STATUS = [('SUBMITTED', 'Submitted'), ('ASSIGNED', 'Assigned'), ('IN_REVIEW', 'In review'),
              ('WAITING_USER', 'Waiting for user'), ('RESOLVED', 'Resolved'), ('REOPENED', 'Reopened'),
              ('CLOSED', 'Closed'), ('REJECTED', 'Rejected')]

    number = models.CharField(max_length=30, unique=True)
    ticket_type = models.CharField(max_length=12, choices=TYPES)
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='helpdesk_tickets')
    requester_role = models.CharField(max_length=10, choices=ROLES)
    student = models.ForeignKey('student_profile.Student', null=True, blank=True, on_delete=models.PROTECT,
                                related_name='helpdesk_tickets')
    category = models.ForeignKey(TicketCategory, on_delete=models.PROTECT, related_name='tickets')
    subject = models.CharField(max_length=180)
    description = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITIES, default='NORMAL')
    privacy = models.CharField(max_length=15, choices=PRIVACY, default='NORMAL')
    anonymous_to_handlers = models.BooleanField(default=False)
    status = models.CharField(max_length=15, choices=STATUS, default='SUBMITTED')
    assigned_department = models.CharField(max_length=100, blank=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
                                    related_name='helpdesk_tickets_assigned')
    due_at = models.DateTimeField(null=True, blank=True)
    first_responded_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    resolution = models.TextField(blank=True)
    satisfaction_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    satisfaction_comment = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        permissions = [
            ('manage_tickets', 'Can manage helpdesk tickets'),
            ('view_confidential_tickets', 'Can view confidential helpdesk tickets'),
            ('view_safeguarding_tickets', 'Can view safeguarding tickets'),
        ]

    def clean(self):
        if self.requester_role == 'PARENT' and not self.student_id:
            raise ValidationError('A parent ticket must identify the linked child.')
        if self.satisfaction_rating is not None and not 1 <= self.satisfaction_rating <= 5:
            raise ValidationError('Satisfaction rating must be from 1 to 5.')

    @property
    def is_overdue(self):
        return bool(self.due_at and self.due_at < timezone.now() and self.status not in {'RESOLVED', 'CLOSED', 'REJECTED'})

    def __str__(self):
        return f'{self.number} · {self.subject}'


class TicketMessage(TimeStampedModel):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='messages')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    body = models.TextField()
    is_internal = models.BooleanField(default=False)
    attachment = models.FileField(upload_to='helpdesk/attachments/%Y/%m/', null=True, blank=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.ticket.number} message by {self.author}'


class TicketEvent(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.PROTECT, related_name='events')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=40)
    from_status = models.CharField(max_length=15, blank=True)
    to_status = models.CharField(max_length=15, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def delete(self, *args, **kwargs):
        raise ValidationError('Ticket audit events are immutable.')

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError('Ticket audit events are immutable.')
        return super().save(*args, **kwargs)


class TicketNotification(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='helpdesk_notifications')
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='notifications')
    text = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
