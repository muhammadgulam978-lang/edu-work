"""RFC 6238 TOTP with encrypted secrets, replay prevention and retry throttling.

Algorithm and test vectors: https://www.rfc-editor.org/rfc/rfc6238
"""
import base64
import hashlib
import hmac
import secrets
import struct
import time
from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from .crypto import decrypt_text, encrypt_text
from .models import MfaDevice, AuditEvent


def totp(secret, counter, digits=6):
    key = base64.b32decode(secret)
    digest = hmac.new(key, struct.pack('>Q', counter), hashlib.sha1).digest()
    offset = digest[-1] & 15
    number = struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7fffffff
    return str(number % (10 ** digits)).zfill(digits)


@transaction.atomic
def begin_enrollment(user):
    # Confirmed devices cannot be reset using only a password/session.
    device = MfaDevice.objects.select_for_update().filter(user=user).first()
    if device and device.confirmed:
        raise PermissionDenied('This account already has a confirmed authenticator.')
    if device:
        return decrypt_text(device.encrypted_secret)
    secret = base64.b32encode(secrets.token_bytes(20)).decode('ascii')
    MfaDevice.objects.create(user=user, encrypted_secret=encrypt_text(secret))
    return secret


@transaction.atomic
def verify_code(user, code, now=None):
    now = now or timezone.now()
    device = MfaDevice.objects.select_for_update().filter(user=user).first()
    if not device or not user.is_active or (device.locked_until and device.locked_until > now):
        return False
    code = str(code).strip()
    counter = int(now.timestamp()) // 30
    matched = None
    if len(code) == 6 and code.isascii() and code.isdigit():
        secret = decrypt_text(device.encrypted_secret)
        for candidate in range(max(0, counter - 1), counter + 2):
            if candidate > device.last_counter and hmac.compare_digest(totp(secret, candidate), code):
                matched = candidate
                break
    if matched is None:
        device.failed_attempts += 1
        if device.failed_attempts >= 5:
            device.locked_until = now + timedelta(minutes=5)
            device.failed_attempts = 0
        device.save(update_fields=['failed_attempts', 'locked_until'])
        AuditEvent.objects.create(actor=user, action='mfa.verify', resource='access_control.mfadevice',
                                  object_id=str(device.pk), outcome='denied')
        return False
    device.last_counter, device.confirmed = matched, True
    device.failed_attempts, device.locked_until = 0, None
    device.save(update_fields=['last_counter', 'confirmed', 'failed_attempts', 'locked_until'])
    AuditEvent.objects.create(actor=user, action='mfa.verify', resource='access_control.mfadevice',
                              object_id=str(device.pk), outcome='verified')
    return True


def session_verified(request):
    until = request.session.get('mfa_verified_until', 0)
    return bool(request.user.is_authenticated and isinstance(until, (int, float)) and until > time.time() and
                MfaDevice.objects.filter(user=request.user, confirmed=True).exists())
