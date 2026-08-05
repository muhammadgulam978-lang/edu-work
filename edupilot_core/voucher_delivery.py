from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import FeeVoucher, PortalNotification, VoucherDelivery


ROLE_ROUTE_NAMES = {
    'STUDENT': {
        'list': 'student_vouchers',
        'view': 'student_voucher_view',
        'download': 'student_voucher_download',
        'dismiss': 'student_voucher_dismiss',
    },
    'PARENT': {
        'list': 'parent_vouchers',
        'view': 'parent_voucher_view',
        'download': 'parent_voucher_download',
        'dismiss': 'parent_voucher_dismiss',
    },
    'TEACHER': {
        'list': 'teacher_vouchers',
        'view': 'teacher_voucher_view',
        'download': 'teacher_voucher_download',
        'dismiss': 'teacher_voucher_dismiss',
    },
}


def canonical_student_for(voucher):
    if voucher.canonical_student_id:
        return voucher.canonical_student
    return getattr(voucher.student, 'canonical_student', None)


def recipients_for_student(student):
    recipients = []
    if student.user_id:
        recipients.append((student.user, 'STUDENT'))

    for parent in student.parents.select_related('user').filter(user__isnull=False):
        recipients.append((parent.user, 'PARENT'))

    if student.class_fk_id and student.section_id:
        from admin_panel.models import ClassTeacher

        teachers = ClassTeacher.objects.filter(
            class_fk_id=student.class_fk_id,
            section_id=student.section_id,
            teacher__user__isnull=False,
        ).select_related('teacher__user')
        if student.academic_year_id:
            teachers = teachers.filter(academic_year_id=student.academic_year_id)
        for assignment in teachers:
            recipients.append((assignment.teacher.user, 'TEACHER'))

    unique = {}
    for user, role in recipients:
        unique[user.pk] = (user, role)
    return list(unique.values())


def _broadcast(user_id, voucher_id):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(
        f'voucher_user_{user_id}',
        {'type': 'voucher.available', 'voucher_id': voucher_id},
    )


def _create_delivery(voucher, student, user, role):
    delivery, created = VoucherDelivery.objects.get_or_create(
        voucher=voucher,
        recipient=user,
        defaults={'related_student': student, 'recipient_role': role},
    )
    if not created and (
        delivery.related_student_id != student.pk or delivery.recipient_role != role
    ):
        delivery.related_student = student
        delivery.recipient_role = role
        delivery.save(update_fields=['related_student', 'recipient_role'])

    PortalNotification.objects.get_or_create(
        recipient=user,
        voucher=voucher,
        notification_type='VOUCHER',
        defaults={
            'title': f'Fee voucher available - {student.name}',
            'message': (
                f'{voucher.month} {voucher.year} fee voucher for {student.name} '
                f'is ready. Amount: PKR {voucher.net_amount:,.2f}.'
            ),
            'related_student': student,
        },
    )
    if created:
        transaction.on_commit(lambda: _broadcast(user.pk, voucher.pk))
    return delivery


def distribute_voucher(voucher_id):
    voucher = FeeVoucher.objects.select_related(
        'student__canonical_student', 'canonical_student__user',
        'canonical_student__class_fk', 'canonical_student__section',
        'canonical_student__academic_year',
    ).get(pk=voucher_id)
    student = canonical_student_for(voucher)
    if not student:
        return 0
    count = 0
    for user, role in recipients_for_student(student):
        _create_delivery(voucher, student, user, role)
        count += 1
    return count


def eligible_vouchers_for(user, role):
    base = FeeVoucher.objects.select_related(
        'student__canonical_student', 'canonical_student',
    )
    if role == 'STUDENT':
        student = getattr(user, 'student', None)
        if not student:
            return base.none()
        return base.filter(
            Q(canonical_student=student) | Q(student__canonical_student=student)
        ).distinct()

    if role == 'PARENT':
        parent = getattr(user, 'parent', None)
        if not parent:
            return base.none()
        students = parent.students.all()
        return base.filter(
            Q(canonical_student__in=students) | Q(student__canonical_student__in=students)
        ).distinct()

    if role == 'TEACHER':
        teacher = getattr(user, 'teacher', None)
        if not teacher:
            return base.none()
        from admin_panel.models import ClassTeacher

        assignments = ClassTeacher.objects.filter(teacher=teacher).values(
            'class_fk_id', 'section_id', 'academic_year_id'
        )
        filters = Q(pk__in=[])
        for assignment in assignments:
            pair = Q(
                canonical_student__class_fk_id=assignment['class_fk_id'],
                canonical_student__section_id=assignment['section_id'],
            ) | Q(
                student__canonical_student__class_fk_id=assignment['class_fk_id'],
                student__canonical_student__section_id=assignment['section_id'],
            )
            if assignment['academic_year_id']:
                pair &= (
                    Q(canonical_student__academic_year_id=assignment['academic_year_id'])
                    | Q(student__canonical_student__academic_year_id=assignment['academic_year_id'])
                )
            filters |= pair
        return base.filter(filters).distinct()
    return base.none()


def sync_user_deliveries(user, role):
    created = 0
    for voucher in eligible_vouchers_for(user, role).iterator(chunk_size=200):
        student = canonical_student_for(voucher)
        if student:
            _, was_created = VoucherDelivery.objects.get_or_create(
                voucher=voucher,
                recipient=user,
                defaults={'related_student': student, 'recipient_role': role},
            )
            PortalNotification.objects.get_or_create(
                recipient=user,
                voucher=voucher,
                notification_type='VOUCHER',
                defaults={
                    'title': f'Fee voucher available - {student.name}',
                    'message': f'{voucher.month} {voucher.year} fee voucher is ready.',
                    'related_student': student,
                },
            )
            created += int(was_created)
    return created


@receiver(post_save, sender=FeeVoucher)
def distribute_new_fee_voucher(sender, instance, created, **kwargs):
    if created:
        transaction.on_commit(lambda: distribute_voucher(instance.pk))
