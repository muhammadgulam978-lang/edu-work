import os
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.core.mail import EmailMessage
from django.db import close_old_connections
from django.utils import timezone

from .models import EmailOutbox


_EMAIL_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix='edupilot-email')


def _real_email(value):
    value = (value or '').strip()
    return value if value and not value.lower().endswith('.local') else ''


def queue_account_email(*, user, password, role, display_name, kick=False):
    recipient = _real_email(user.email)
    if not recipient or not password:
        return False
    role_key = role.upper()
    login_urls = {
        'STUDENT': settings.STUDENT_PORTAL_LOGIN_URL,
        'PARENT': settings.PARENT_PORTAL_LOGIN_URL,
        'TEACHER': settings.TEACHER_PORTAL_LOGIN_URL,
    }
    _, created = EmailOutbox.objects.get_or_create(
        dedupe_key=f'account-welcome:{user.pk}',
        defaults={
            'recipient': recipient,
            'subject': f'Your EduPilot {role.title()} Portal account is ready',
            'body': (
                f'Dear {display_name},\n\nYour EduPilot {role.title()} Portal account '
                f'has been created successfully.\n\nLogin ID: {user.username}\n'
                f'Password: {password}\nPortal: {login_urls[role_key]}\n\n'
                'Please sign in and change your password after your first login.\n\nEduPilot'
            ),
            'sensitive': True,
        },
    )
    if created and kick:
        kick_email_dispatch()
    return created


def queue_voucher_email(voucher, student, user, role, kick=True):
    recipient = _real_email(user.email)
    if not recipient:
        return False
    attachment = os.path.join(
        settings.MEDIA_ROOT, 'vouchers', f'voucher_{voucher.voucher_no}.pdf'
    )
    _, created = EmailOutbox.objects.get_or_create(
        dedupe_key=f'voucher:{voucher.pk}:recipient:{user.pk}',
        defaults={
            'recipient': recipient,
            'subject': f'Fee voucher generated for {student.name}',
            'body': (
                f'Dear {user.get_full_name() or user.username},\n\n'
                f'The {voucher.month} {voucher.year} fee voucher for {student.name} '
                f'has been generated.\nVoucher: {voucher.voucher_no}\n'
                f'Amount: PKR {voucher.net_amount:,.2f}\nDue date: {voucher.due_date}\n\n'
                f'The PDF is attached. You can also open it in the {role.title()} Portal.\n\nEduPilot'
            ),
            'attachment_path': attachment,
        },
    )
    if created and kick:
        kick_email_dispatch()
    return created


def dispatch_pending_emails(batch_size=100):
    if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        return 0
    close_old_connections()
    sent = 0
    attempted = 0
    try:
        ids = list(EmailOutbox.objects.filter(status='PENDING').values_list('pk', flat=True)[:batch_size])
        for item in EmailOutbox.objects.filter(pk__in=ids).order_by('created_at'):
            if item.dedupe_key.startswith('voucher:') and not _voucher_delivery_authorized(item):
                item.status = 'FAILED'
                item.last_error = 'Current recipient access does not authorize this voucher.'
                item.save(update_fields=['status', 'last_error'])
                continue
            if item.attachment_path and not os.path.exists(item.attachment_path):
                item.last_error = 'Attachment is not available yet.'
                item.save(update_fields=['last_error'])
                continue
            item.status = 'SENDING'
            item.attempts += 1
            item.save(update_fields=['status', 'attempts'])
            attempted += 1
            try:
                message = EmailMessage(
                    subject=item.subject,
                    body=item.body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[item.recipient],
                )
                if item.attachment_path:
                    message.attach_file(item.attachment_path)
                message.send(fail_silently=False)
                item.status = 'SENT'
                item.sent_at = timezone.now()
                item.last_error = ''
                update_fields = ['status', 'sent_at', 'last_error']
                if item.sensitive:
                    item.body = '[Sensitive credentials removed after successful delivery]'
                    update_fields.append('body')
                item.save(update_fields=update_fields)
                sent += 1
            except Exception as exc:
                item.status = 'PENDING' if item.attempts < 5 else 'FAILED'
                item.last_error = str(exc)[:2000]
                item.save(update_fields=['status', 'last_error'])
    finally:
        close_old_connections()
    # Continue immediately only when this batch contained sendable work. Missing
    # PDFs wait for the scheduler's next pass instead of causing a tight loop.
    if attempted and len(ids) == batch_size and EmailOutbox.objects.filter(status='PENDING').exists():
        _EMAIL_EXECUTOR.submit(dispatch_pending_emails, batch_size)
    return sent


def kick_email_dispatch():
    _EMAIL_EXECUTOR.submit(dispatch_pending_emails)


def _voucher_delivery_authorized(item):
    from .models import VoucherDelivery
    from .voucher_delivery import eligible_vouchers_for
    try:
        prefix, voucher_id, recipient_label, user_id = item.dedupe_key.split(':')
        if prefix != 'voucher' or recipient_label != 'recipient':
            return False
        delivery = VoucherDelivery.objects.select_related('recipient').filter(
            voucher_id=int(voucher_id), recipient_id=int(user_id), recipient__is_active=True,
        ).first()
    except (ValueError, TypeError):
        return False
    if not delivery or delivery.recipient.email.casefold() != item.recipient.casefold():
        return False
    return eligible_vouchers_for(delivery.recipient, delivery.recipient_role).filter(pk=delivery.voucher_id).exists()
