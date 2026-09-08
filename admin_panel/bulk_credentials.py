import base64
import hashlib
import hmac
import secrets
from datetime import timedelta

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import BulkStudentCredential


def _fernet():
    digest = hashlib.sha256(
        f"edupilot-bulk-credential:{settings.SECRET_KEY}".encode('utf-8')
    ).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def password_fingerprint(password):
    return hmac.new(
        settings.SECRET_KEY.encode('utf-8'), password.encode('utf-8'), hashlib.sha256
    ).hexdigest()


def generate_unique_student_password():
    """Generate a password not previously issued by the bulk workflow."""
    for _attempt in range(25):
        password = f"Edu@{secrets.token_urlsafe(12)}"
        if not BulkStudentCredential.objects.filter(
            password_fingerprint=password_fingerprint(password)
        ).exists():
            return password
    raise RuntimeError('A unique student password could not be generated. Please retry.')


def store_bulk_student_credential(student, password, created_by=None):
    encrypted = _fernet().encrypt(password.encode('utf-8')).decode('ascii')
    expires_at = timezone.now() + timedelta(
        days=getattr(settings, 'BULK_STUDENT_PASSWORD_DISPLAY_DAYS', 30)
    )
    try:
        with transaction.atomic():
            return BulkStudentCredential.objects.update_or_create(
                student=student,
                defaults={
                    'encrypted_password': encrypted,
                    'password_fingerprint': password_fingerprint(password),
                    'created_by': created_by,
                    'expires_at': expires_at,
                },
            )[0]
    except IntegrityError as exc:
        raise ValueError('This password was already issued to another student.') from exc


def get_bulk_student_password(student):
    credential = BulkStudentCredential.objects.filter(
        student=student, expires_at__gt=timezone.now()
    ).first()
    if not credential:
        return ''
    try:
        password = _fernet().decrypt(
            credential.encrypted_password.encode('ascii')
        ).decode('utf-8')
    except (InvalidToken, ValueError, TypeError):
        return ''
    credential.last_viewed_at = timezone.now()
    credential.save(update_fields=['last_viewed_at'])
    return password
