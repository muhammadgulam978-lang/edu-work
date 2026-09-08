from django.contrib import admin
from .models import Parent
from .models import StudentGuardian
from django.utils import timezone

admin.site.register(Parent)


@admin.register(StudentGuardian)
class GuardianAdmin(admin.ModelAdmin):
    list_display = ['parent', 'student', 'relationship', 'portal_access', 'verified_at', 'expires_at']
    readonly_fields = ['verified_at', 'verified_by']
    actions = ['verify_relationships', 'revoke_relationships']

    def save_model(self, request, obj, form, change):
        if change and {'parent', 'student', 'relationship', 'consent_reference'} & set(form.changed_data):
            obj.verified_at = None
            obj.verified_by = None
        super().save_model(request, obj, form, change)

    @admin.action(description='Verify selected relationships using recorded consent evidence')
    def verify_relationships(self, request, queryset):
        from access_control.models import AuditEvent
        for link in queryset:
            if not link.consent_reference.strip() or link.parent.user_id == request.user.pk:
                self.message_user(request, 'Independent verification and a consent reference are required.', level='ERROR')
                continue
            link.verified_at, link.verified_by = timezone.now(), request.user
            link.save(update_fields=['verified_at', 'verified_by'])
            link.parent.students.add(link.student)
            AuditEvent.objects.create(actor=request.user, action='guardian.verify',
                                      resource='parent_dashboard.studentguardian', object_id=str(link.pk), outcome='verified')

    @admin.action(description='Revoke portal access for selected relationships')
    def revoke_relationships(self, request, queryset):
        from access_control.models import AuditEvent
        for link in queryset:
            link.portal_access = False
            link.save(update_fields=['portal_access'])
            AuditEvent.objects.create(actor=request.user, action='guardian.revoke',
                                      resource='parent_dashboard.studentguardian', object_id=str(link.pk), outcome='revoked')
# Register your models here.
