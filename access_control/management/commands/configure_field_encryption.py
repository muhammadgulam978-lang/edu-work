import os
from pathlib import Path

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from dotenv import dotenv_values


class Command(BaseCommand):
    help = 'Initialize a local encryption key in .env without displaying or replacing an existing key.'

    def handle(self, *args, **options):
        path = Path(settings.BASE_DIR) / '.env'
        values = dotenv_values(path) if path.exists() else {}
        name = 'EDUPILOT_FIELD_ENCRYPTION_KEY'
        existing = os.environ.get(name) or values.get(name)
        if existing:
            try:
                Fernet(existing.encode())
            except (ValueError, TypeError):
                raise CommandError('The configured key is invalid. Restore the correct key; it was not replaced.')
            self.stdout.write('An encryption key is already configured; it was not changed.')
            return
        if name in values:
            raise CommandError('Remove the empty encryption setting from .env before initializing it.')
        with path.open('a', encoding='utf-8') as handle:
            handle.write('\n' + name + '=' + Fernet.generate_key().decode() + '\n')
        self.stdout.write('Encryption key saved in .env. Back it up securely and restart Django to load it.')
