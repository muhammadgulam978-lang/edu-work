from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .models import Announcement, AnnouncementRead
from .services import AnnouncementService


@login_required
def announcement_feed(
    request,
    *,
    template_name,
    redirect_name,
    portal_label,
    required_relation=None,
    require_staff=False,
):
    if require_staff and not request.user.is_staff:
        raise PermissionDenied
    if required_relation and not hasattr(request.user, required_relation):
        raise PermissionDenied
    visible = AnnouncementService.visible_for_user(request.user)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'mark_read':
            announcement = get_object_or_404(visible, pk=request.POST.get('announcement_id'))
            AnnouncementService.mark_read(announcement, request.user)
        elif action == 'mark_all_read':
            for announcement in visible.only('id'):
                AnnouncementService.mark_read(announcement, request.user)
            messages.success(request, 'All announcements marked as read.')
        return redirect(redirect_name)

    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    state = request.GET.get('state', 'all')
    announcements = visible
    if query:
        announcements = announcements.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )
    if category:
        announcements = announcements.filter(category=category)

    read_ids = set(
        AnnouncementRead.objects.filter(
            user=request.user,
            announcement__in=announcements,
        ).values_list('announcement_id', flat=True)
    )
    items = list(announcements[:100])
    for announcement in items:
        announcement.is_read_by_user = announcement.pk in read_ids
    if state == 'unread':
        items = [item for item in items if not item.is_read_by_user]
    elif state == 'read':
        items = [item for item in items if item.is_read_by_user]

    return render(request, template_name, {
        'announcements': items,
        'announcement_count': len(items),
        'unread_count': sum(not item.is_read_by_user for item in items),
        'categories': Announcement.CATEGORY_CHOICES,
        'selected_category': category,
        'active_state': state,
        'query': query,
        'portal_label': portal_label,
    })


def automation_announcements(request):
    return announcement_feed(
        request,
        template_name='automation/announcements_feed.html',
        redirect_name='automation-announcements',
        portal_label='Automation',
        require_staff=True,
    )
