import base64
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet
from django.contrib.auth.models import User
from django.test import TestCase

from .mfa import begin_enrollment, totp, verify_code
from .models import MfaDevice


class AuthenticatorTests(TestCase):
    def setUp(self):
        self.settings_override = self.settings(EDUPILOT_FIELD_ENCRYPTION_KEY=Fernet.generate_key().decode())
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.user = User.objects.create_user('authenticator-user', password='secret')
        self.now = datetime(2026, 9, 8, 12, tzinfo=timezone.utc)

    def test_rfc6238_sha1_vectors(self):
        secret = base64.b32encode(b'12345678901234567890').decode()
        for timestamp, expected in [(59, '94287082'), (1111111109, '07081804'),
                                    (1111111111, '14050471'), (1234567890, '89005924'),
                                    (2000000000, '69279037'), (20000000000, '65353130')]:
            self.assertEqual(totp(secret, timestamp // 30, digits=8), expected)

    def test_enrollment_encrypts_secret_and_rejects_replay(self):
        secret = begin_enrollment(self.user)
        self.assertNotIn(secret, MfaDevice.objects.get(user=self.user).encrypted_secret)
        code = totp(secret, int(self.now.timestamp()) // 30)
        self.assertTrue(verify_code(self.user, code, now=self.now))
        self.assertFalse(verify_code(self.user, code, now=self.now))
        self.assertTrue(MfaDevice.objects.get(user=self.user).confirmed)

    def test_failed_codes_lock_and_recover_after_timeout(self):
        secret = begin_enrollment(self.user)
        for _ in range(5):
            self.assertFalse(verify_code(self.user, 'invalid', now=self.now))
        self.assertFalse(verify_code(self.user, totp(secret, int(self.now.timestamp()) // 30), now=self.now))
        later = self.now + timedelta(minutes=6)
        self.assertTrue(verify_code(self.user, totp(secret, int(later.timestamp()) // 30), now=later))
