from django.contrib import admin
from django.core.exceptions import ValidationError

from .models import PaperApproval


@admin.register(PaperApproval)
class PaperApprovalAdmin(admin.ModelAdmin):
    list_display = ['paper_id', 'stage', 'assigned_to', 'status']
    fields = ['paper', 'stage', 'assigned_to', 'status', 'reviewed_by', 'remarks', 'timestamp']
    readonly_fields = ['paper', 'stage', 'status', 'reviewed_by', 'remarks', 'timestamp']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        if obj.paper.status == 'LOCKED':
            raise ValidationError('Locked paper assignments cannot change.')
        if obj.stage != 'TEACHER' and obj.assigned_to_id == obj.paper.generated_by_id:
            raise ValidationError('The setter cannot be an independent reviewer.')
        if 'assigned_to' in form.changed_data:
            from .access import invalidate_reviews
            invalidate_reviews(obj.paper)
            obj.status, obj.reviewed_by, obj.remarks = 'PENDING', None, ''
        super().save_model(request, obj, form, change)
