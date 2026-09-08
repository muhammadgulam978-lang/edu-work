from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from .models import (Institution, Campus, RoleDefinition, RoleGrant, RoleAssignment,
                     RecordScope, AuditEvent, ApprovalRequest, PaymentReceipt)


class GrantInline(admin.TabularInline):
    model = RoleGrant
    extra = 0


@admin.register(RoleDefinition)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'institution', 'active', 'requires_mfa']
    list_filter = ['institution', 'active']
    inlines = [GrantInline]


@admin.register(RoleAssignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'campus', 'is_primary', 'active', 'starts_at', 'ends_at', 'approved_by']
    readonly_fields = ['approved_by']
    actions = ['approve_assignments']

    def save_model(self, request, obj, form, change):
        # Editing a scope invalidates approval instead of carrying it forward.
        obj.approved_by = None
        super().save_model(request, obj, form, change)

    @admin.action(description='Approve selected access assignments')
    def approve_assignments(self, request, queryset):
        for assignment in queryset:
            if assignment.user_id == request.user.pk:
                self.message_user(request, 'You cannot approve your own access.', messages.ERROR)
                continue
            assignment.approved_by = request.user
            assignment.save()
            AuditEvent.objects.create(actor=request.user, institution=assignment.role.institution,
                                      assignment=assignment, action='role.approve', resource='access_control.roleassignment',
                                      object_id=str(assignment.pk), outcome='approved')


class EvidenceAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(Institution)
admin.site.register(Campus)
admin.site.register(RecordScope)
admin.site.register(AuditEvent, EvidenceAdmin)
admin.site.register(PaymentReceipt, EvidenceAdmin)
admin.site.register(ApprovalRequest, EvidenceAdmin)
