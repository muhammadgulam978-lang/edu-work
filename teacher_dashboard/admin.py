from django.contrib import admin
from .models import Teacher


# ---------------------
# Bulk actions for LessonDay
# ---------------------
@admin.action(description='Mark selected lessons as completed')
def mark_as_completed(modeladmin, request, queryset):
    queryset.update(status='completed')

@admin.action(description='Mark selected lessons as missed')
def mark_as_missed(modeladmin, request, queryset):
    queryset.update(status='missed')

@admin.action(description='Mark selected lessons as rescheduled')
def mark_as_rescheduled(modeladmin, request, queryset):
    queryset.update(status='rescheduled')



# teacher_dashboard/admin.py
from django.contrib import admin
from .models import Teacher

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'show_subjects')

    def show_subjects(self, obj):
        return ", ".join([subject.name for subject in obj.subjects.all()])
    show_subjects.short_description = "Assigned Subjects"

