"""Scoped authorization records. Domain ownership is explicit, never inferred from IDs."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Institution(models.Model):
    name = models.CharField(max_length=200)
    code = models.SlugField(unique=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Campus(models.Model):
    institution = models.ForeignKey(Institution, on_delete=models.PROTECT)
    name = models.CharField(max_length=200)
    code = models.SlugField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['institution', 'code'], name='access_campus_code')]

    def __str__(self):
        return self.name


class RoleDefinition(models.Model):
    institution = models.ForeignKey(Institution, on_delete=models.PROTECT)
    name = models.CharField(max_length=100)
    active = models.BooleanField(default=True)
    requires_mfa = models.BooleanField(default=False)
    system = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['institution', 'name'], name='access_role_name')]

    def __str__(self):
        return self.name


class RoleGrant(models.Model):
    ACTIONS = [(a, a.title()) for a in ('view', 'create', 'edit', 'submit', 'review',
                                      'approve', 'publish', 'export', 'delete', 'configure')]
    role = models.ForeignKey(RoleDefinition, on_delete=models.CASCADE, related_name='grants')
    resource = models.CharField(max_length=100)
    action = models.CharField(max_length=12, choices=ACTIONS)
    allowed = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['role', 'resource', 'action'], name='access_grant_unique')]


class RoleAssignment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    role = models.ForeignKey(RoleDefinition, on_delete=models.PROTECT)
    campus = models.ForeignKey(Campus, on_delete=models.PROTECT, null=True, blank=True)
    # Explicit dimension values; no wildcard or user-supplied query expressions.
    scope = models.JSONField(default=dict, blank=True)
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(default=True)
    is_primary = models.BooleanField(default=False)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                    related_name='approved_access_assignments', null=True, blank=True)

    def clean(self):
        if self.campus_id and self.campus.institution_id != self.role.institution_id:
            raise ValidationError('Campus and role must belong to the same institution.')
        if self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError('Access expiry must be after its start.')
        if self.approved_by_id == self.user_id:
            raise ValidationError('Users cannot approve their own access.')
        from .policy import validate_scope
        validate_scope(self.scope)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class RecordScope(models.Model):
    """Ownership registry for existing models without destructive schema rewrites."""
    institution = models.ForeignKey(Institution, on_delete=models.PROTECT)
    campus = models.ForeignKey(Campus, on_delete=models.PROTECT, null=True, blank=True)
    resource = models.CharField(max_length=100)
    object_id = models.PositiveBigIntegerField()
    dimensions = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['resource', 'object_id'], name='access_record_owner')]
        indexes = [models.Index(fields=['institution', 'resource'])]

    def clean(self):
        if self.campus_id and self.campus.institution_id != self.institution_id:
            raise ValidationError('Campus belongs to another institution.')
        from .policy import validate_scope
        validate_scope(self.dimensions)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class AuditQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError('Audit events cannot be edited.')

    def delete(self):
        raise ValidationError('Audit events cannot be deleted.')


class AuditEvent(models.Model):
    objects = AuditQuerySet.as_manager()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True)
    institution = models.ForeignKey(Institution, on_delete=models.PROTECT, null=True)
    assignment = models.ForeignKey(RoleAssignment, on_delete=models.PROTECT, null=True)
    action = models.CharField(max_length=100)
    resource = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100, blank=True)
    outcome = models.CharField(max_length=20)
    reason = models.TextField(blank=True)
    evidence = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError('Audit events cannot be edited.')
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('Audit events cannot be deleted.')


class ApprovalRequest(models.Model):
    STATES = [(x, x.title()) for x in ('draft', 'submitted', 'approved', 'rejected', 'executed')]
    ownership = models.ForeignKey(RecordScope, on_delete=models.PROTECT)
    operation = models.CharField(max_length=50)
    maker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='made_approvals')
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='assigned_approvals')
    status = models.CharField(max_length=12, choices=STATES, default='draft')
    payload = models.JSONField(default=dict)
    payload_hash = models.CharField(max_length=64)
    reason = models.TextField(blank=True)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now)
    decided_at = models.DateTimeField(null=True, blank=True)
    executed_at = models.DateTimeField(null=True, blank=True)

    def clean(self):
        if self.maker_id == self.reviewer_id:
            raise ValidationError('Maker and reviewer must be different people.')


class PaymentReceipt(models.Model):
    voucher = models.ForeignKey('edupilot_core.FeeVoucher', on_delete=models.PROTECT, related_name='verified_receipts')
    reference = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(amount__gt=0), name='access_positive_receipt')]


class MfaDevice(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    encrypted_secret = models.TextField()
    confirmed = models.BooleanField(default=False)
    last_counter = models.BigIntegerField(default=-1)
    failed_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
