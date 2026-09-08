from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def field_cipher():
    key = getattr(settings, 'EDUPILOT_FIELD_ENCRYPTION_KEY', '')
    if not key:
        raise ImproperlyConfigured('Configure EDUPILOT_FIELD_ENCRYPTION_KEY before storing sensitive information.')
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_text(value):
    return field_cipher().encrypt(value.encode('utf-8')).decode('ascii')


def decrypt_text(value):
    return field_cipher().decrypt(value.encode('ascii')).decode('utf-8')
