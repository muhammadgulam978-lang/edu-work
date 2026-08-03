from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .models import PortalNotification, VoucherDelivery
from .services import PDFGeneratorService
from .voucher_delivery import ROLE_ROUTE_NAMES, sync_user_deliveries


BASE_TEMPLATES = {
    'STUDENT': 'student_profile/bases.html',
    'PARENT': 'parent_dashboard/base.html',
    'TEACHER': 'teacher_dashboard/bases.html',
}


def _profile_for(user, role):
    relation = role.lower()
    profile = getattr(user, relation, None)
    if not profile:
        raise Http404('Portal profile not found.')
    return profile


def _delivery(request, delivery_id, role):
    _profile_for(request.user, role)
    return get_object_or_404(
        VoucherDelivery.objects.select_related('voucher', 'related_student'),
        pk=delivery_id,
        recipient=request.user,
        recipient_role=role,
    )


def _pdf_path(voucher):
    path = Path(settings.MEDIA_ROOT) / 'vouchers' / f'voucher_{voucher.voucher_no}.pdf'
    if not path.exists():
        generated = PDFGeneratorService.generate_voucher_pdf(voucher)
        path = Path(generated)
    if not path.exists():
        raise Http404('Voucher PDF is not available.')
    return path


def _mark_viewed(delivery):
    now = timezone.now()
    update_fields = ['last_viewed_at']
    delivery.last_viewed_at = now
    if not delivery.viewed_at:
        delivery.viewed_at = now
        update_fields.append('viewed_at')
    delivery.save(update_fields=update_fields)
    PortalNotification.objects.filter(
        recipient=delivery.recipient, voucher=delivery.voucher, is_read=False
    ).update(is_read=True, read_at=now)


def _delivery_json(delivery, role):
    voucher = delivery.voucher
    names = ROLE_ROUTE_NAMES[role]
    return {
        'id': delivery.pk,
        'student_name': delivery.related_student.name,
        'student_id': delivery.related_student.student_id,
        'title': f'{voucher.month} {voucher.year} Fee Voucher',
        'issue_date': voucher.issue_date.isoformat(),
        'due_date': voucher.due_date.isoformat(),
        'amount': f'{voucher.net_amount:,.2f}',
        'status': voucher.status,
        'delivered_at': delivery.delivered_at.isoformat(),
        'viewed': bool(delivery.viewed_at),
        'downloaded': bool(delivery.downloaded_at),
        'dismissed': bool(delivery.dismissed_at),
        'last_viewed_at': delivery.last_viewed_at.isoformat() if delivery.last_viewed_at else None,
        'view_url': reverse(names['view'], args=[delivery.pk]),
        'download_url': reverse(names['download'], args=[delivery.pk]),
        'dismiss_url': reverse(names['dismiss'], args=[delivery.pk]),
    }


@login_required
def portal_vouchers(request, portal_role):
    _profile_for(request.user, portal_role)
    sync_user_deliveries(request.user, portal_role)
    deliveries = VoucherDelivery.objects.filter(
        recipient=request.user, recipient_role=portal_role
    ).select_related('voucher', 'related_student')
    notifications = PortalNotification.objects.filter(
        recipient=request.user, notification_type='VOUCHER'
    ).select_related('voucher', 'related_student')[:20]
    return render(request, 'voucher_portal/list.html', {
        'base_template': BASE_TEMPLATES[portal_role],
        'portal_role': portal_role,
        'deliveries': deliveries,
        'notifications': notifications,
        'unread_count': PortalNotification.objects.filter(
            recipient=request.user, notification_type='VOUCHER', is_read=False
        ).count(),
        'route_names': ROLE_ROUTE_NAMES[portal_role],
    })


@login_required
@require_GET
def voucher_summary(request, portal_role):
    _profile_for(request.user, portal_role)
    sync_user_deliveries(request.user, portal_role)
    deliveries = VoucherDelivery.objects.filter(
        recipient=request.user, recipient_role=portal_role
    ).select_related('voucher', 'related_student')
    popup = deliveries.filter(dismissed_at__isnull=True).first()
    unread = PortalNotification.objects.filter(
        recipient=request.user, notification_type='VOUCHER', is_read=False
    )
    return JsonResponse({
        'popup': _delivery_json(popup, portal_role) if popup else None,
        'total_vouchers': deliveries.count(),
        'unread_notifications': unread.count(),
        'vouchers_url': reverse(ROLE_ROUTE_NAMES[portal_role]['list']),
    })


@login_required
@require_GET
def voucher_view(request, delivery_id, portal_role):
    delivery = _delivery(request, delivery_id, portal_role)
    _mark_viewed(delivery)
    return FileResponse(
        open(_pdf_path(delivery.voucher), 'rb'),
        content_type='application/pdf',
        filename=f'{delivery.voucher.voucher_no}.pdf',
    )


@login_required
@require_GET
def voucher_download(request, delivery_id, portal_role):
    delivery = _delivery(request, delivery_id, portal_role)
    now = timezone.now()
    delivery.downloaded_at = delivery.downloaded_at or now
    delivery.last_viewed_at = now
    delivery.save(update_fields=['downloaded_at', 'last_viewed_at'])
    PortalNotification.objects.filter(
        recipient=request.user, voucher=delivery.voucher, is_read=False
    ).update(is_read=True, read_at=now)
    return FileResponse(
        open(_pdf_path(delivery.voucher), 'rb'),
        as_attachment=True,
        filename=f'{delivery.voucher.voucher_no}.pdf',
        content_type='application/pdf',
    )


@login_required
@require_POST
def voucher_dismiss(request, delivery_id, portal_role):
    delivery = _delivery(request, delivery_id, portal_role)
    if not delivery.dismissed_at:
        delivery.dismissed_at = timezone.now()
        delivery.save(update_fields=['dismissed_at'])
    return JsonResponse({'ok': True})


@login_required
@require_POST
def notification_read(request, notification_id, portal_role):
    _profile_for(request.user, portal_role)
    notification = get_object_or_404(
        PortalNotification, pk=notification_id, recipient=request.user
    )
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=['is_read', 'read_at'])
    return JsonResponse({'ok': True})
