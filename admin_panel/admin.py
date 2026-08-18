from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html

User = get_user_model()

def get_user_role(user):
    if user.groups.filter(name='Teacher').exists():
        return 'Teacher'
    elif user.groups.filter(name='Parent').exists():
        return 'Parent'
    elif user.groups.filter(name='Student').exists():
        return 'Student'
    elif user.groups.filter(name='Admin').exists():
        return 'Admin'
    return 'Unknown'

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'get_role')

    def get_role(self, obj):
        return format_html('<span>{}</span>', get_user_role(obj))
    get_role.short_description = 'Role'

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# ------------------------------- #
#   Other Models Registration     #
# ------------------------------- #
from .models import (
    Admission, Class, AcademicYear, Section, Subject,
    CreatePeriod, SubjectPeriod, AssignedPeriod,
    CurriculumSource, GuideBook, Book,
    Chapter, Topic, SubTopic,
    LessonPlanRequest, LessonDay, Worksheet
)

admin.site.register(Admission)
admin.site.register(Class)
admin.site.register(AcademicYear)
admin.site.register(Section)
admin.site.register(Subject)
admin.site.register(CreatePeriod)
admin.site.register(SubjectPeriod)
admin.site.register(AssignedPeriod)

@admin.register(CurriculumSource)
class CurriculumSourceAdmin(admin.ModelAdmin):
    list_display = ('name','website_url')

@admin.register(GuideBook)
class GuideBookAdmin(admin.ModelAdmin):
    list_display = ('name','subject','school_class')

# ------------------------------- #
#   Correct Inline Hierarchy      #
# ------------------------------- #

class SubTopicInline(admin.TabularInline):
    model = SubTopic
    extra = 0

class TopicInline(admin.TabularInline):
    model = Topic
    extra = 0
    inlines = [SubTopicInline]

class ChapterInline(admin.StackedInline):
    model = Chapter
    extra = 0
    show_change_link = True
    inlines = [TopicInline]

# ------------------------------- #
#   Book Admin (clean)            #
# ------------------------------- #
@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title','class_for','subject','uploaded_by','parsed')
    inlines = [ChapterInline]

# ------------------------------- #
#   Lesson Plan Admin             #
# ------------------------------- #

@admin.register(LessonPlanRequest)
class LessonPlanRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "teacher",
        "chapter",
        "total_periods",
        "planning_style",
        "status",
        "created_at",
    )

    list_filter = ("planning_style", "status", "created_at")
    search_fields = ("chapter__title", "teacher__username")


@admin.register(LessonDay)
class LessonDayAdmin(admin.ModelAdmin):
    list_display = ['id', 'plan', 'day_number']
    list_filter = ['plan']   

    list_filter = ("day_number",)

@admin.register(Worksheet)
class WorksheetAdmin(admin.ModelAdmin):
    list_display = ('lesson_plan','created_at')
