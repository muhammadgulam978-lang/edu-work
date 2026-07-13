

from django.contrib import admin

from django.urls import path
from django.shortcuts import redirect
from django.contrib import messages
from datetime import datetime
from .services import FeeGenerationService, SalaryPDFGeneratorService, SalaryAutomationService
from .models import (
    Scholarship, TransportRoute, Student, Transaction, Teacher, Staff, 
    StudentPerformance, FeeHead, FeePlan, FeePlanDetail, StudentFeeAssignment,
    StudentLedger, StudentBalance, FeeVoucher, FeeVoucherItem,
    FeeGenerationSettings, NotificationQueue, FeeGenerationLog,
    AutomationJob, AutomationJobDetail, SalaryStructure, SalaryVoucher,
    SalaryAutomationSettings, SalaryAutomationJob, SalaryAutomationJobDetail
)


# --- TEACHER ADMIN ---
@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('name', 'teacher_id', 'designation', 'department', 'is_active')
    search_fields = ('name', 'teacher_id', 'cnic')
    list_filter = ('is_active', 'department', 'employment_type')
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('name', 'teacher_id', 'cnic', 'email', 'phone', 'address')
        }),
        ('Employment Information', {
            'fields': ('department', 'designation', 'joining_date', 'employment_type', 'is_active')
        }),
        ('Salary Components', {
            'fields': ('basic_salary', 'house_allowance', 'medical_allowance', 
                       'transport_allowance', 'utility_allowance', 'special_allowance', 'overtime')
        }),
    )

# --- SALARY ADMINS ---
@admin.register(SalaryStructure)
class SalaryStructureAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'deductions')
    search_fields = ('teacher__name', 'teacher__teacher_id')
    autocomplete_fields = ('teacher',)

@admin.register(SalaryVoucher)
class SalaryVoucherAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'month', 'year', 'net_salary', 'status', 'generated_at')
    list_filter = ('status', 'month', 'year')
    search_fields = ('teacher__name', 'teacher__teacher_id')
    list_editable = ('status',)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        try:
            SalaryPDFGeneratorService.generate_salary_pdf(obj)
        except Exception as e:
            messages.error(request, f"Error generating PDF: {e}")

# --- SALARY AUTOMATION ADMINS ---
@admin.register(SalaryAutomationSettings)
class SalaryAutomationSettingsAdmin(admin.ModelAdmin):
    list_display = ('auto_enabled', 'generation_day', 'generation_time', 'send_notifications')
    list_editable = ('generation_day', 'generation_time', 'send_notifications')

def retry_failed_salary(modeladmin, request, queryset):
    SalaryAutomationService.generate_salaries()
    messages.success(request, "Salary retry process initiated.")

retry_failed_salary.short_description = "Retry failed salary generations"

@admin.register(SalaryAutomationJob)
class SalaryAutomationJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'started_at', 'success_count', 'failed_count')
    list_filter = ('status',)
    actions = [retry_failed_salary]

@admin.register(SalaryAutomationJobDetail)
class SalaryAutomationJobDetailAdmin(admin.ModelAdmin):
    list_display = ('job', 'teacher', 'status', 'error_message')
    list_filter = ('status',)
    search_fields = ('teacher__name',)

# --- REST OF THE ADMINS ---
@admin.register(FeeGenerationSettings)
class FeeGenerationSettingsAdmin(admin.ModelAdmin):
    list_display = ('auto_enabled', 'generation_day', 'generation_time', 'send_notifications')
    list_display_links = ('auto_enabled',)
    list_editable = ('generation_day', 'generation_time', 'send_notifications')

@admin.register(NotificationQueue)
class NotificationQueueAdmin(admin.ModelAdmin):
    list_display = ('student', 'notification_type', 'status', 'created_at')
    list_filter = ('status', 'notification_type', 'created_at')
    search_fields = ('student__full_name',)

@admin.register(FeeGenerationLog)
class FeeGenerationLogAdmin(admin.ModelAdmin):
    list_display = ('month', 'year', 'status', 'students_processed', 'success_count', 'failed_count', 'started_at')
    list_filter = ('status', 'month', 'year')

@admin.register(AutomationJob)
class AutomationJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'job_type', 'status', 'processed_count', 'success_count', 'failed_count', 'started_at')
    list_filter = ('status', 'job_type')

def retry_failed_records(modeladmin, request, queryset):
    now = datetime.now()
    month = now.strftime("%B")
    year = now.year
    count = 0
    for detail in queryset:
        if detail.status == 'FAILED':
            FeeGenerationService.retry_failed_records(detail.job.id, month, year)
            count += 1
    messages.success(request, f"Retry initiated for {count} records.")

retry_failed_records.short_description = "Retry selected failed records"

@admin.register(AutomationJobDetail)
class AutomationJobDetailAdmin(admin.ModelAdmin):
    list_display = ('job', 'student', 'status', 'error_message')
    list_filter = ('status',)
    search_fields = ('student__full_name',)
    actions = [retry_failed_records]

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'admission_number', 'admission_date', 'current_class', 'is_active')
    search_fields = ('full_name', 'admission_number', 'student_id')
    list_filter = ('is_active', 'campus', 'current_class')

@admin.register(StudentPerformance)
class StudentPerformanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'attendance_percentage', 'average_test_score', 'risk_level')
    list_filter = ('risk_level',)
    search_fields = ('student__full_name',)

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('title', 'amount', 'type', 'date')
    list_filter = ('type', 'date')

@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'is_active')
    search_fields = ('name', 'role')
    list_filter = ('is_active', 'role')

@admin.register(FeeHead)
class FeeHeadAdmin(admin.ModelAdmin):
    list_display = ('name', 'frequency', 'status')
    list_filter = ('frequency', 'status')
    search_fields = ('name',)

@admin.register(FeePlan)
class FeePlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'class_name', 'session')
    search_fields = ('name', 'class_name')

@admin.register(FeePlanDetail)
class FeePlanDetailAdmin(admin.ModelAdmin):
    list_display = ('fee_plan', 'fee_head', 'amount')
    list_filter = ('fee_plan', 'fee_head')

@admin.register(TransportRoute)
class TransportRouteAdmin(admin.ModelAdmin):
    list_display = ('route_name', 'amount')

@admin.register(Scholarship)
class ScholarshipAdmin(admin.ModelAdmin):
    list_display = ('name', 'discount_type', 'value')

@admin.register(StudentFeeAssignment)
class StudentFeeAssignmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'fee_plan', 'transport_route', 'scholarship')
    list_filter = ('fee_plan', 'transport_route')
    search_fields = ('student__full_name',)

@admin.register(StudentLedger)
class StudentLedgerAdmin(admin.ModelAdmin):
    list_display = ('student', 'date', 'description', 'debit', 'credit', 'balance')
    list_filter = ('student', 'date')
    search_fields = ('student__full_name',)

@admin.register(StudentBalance)
class StudentBalanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'outstanding_amount')
    search_fields = ('student__full_name',)

class FeeVoucherItemInline(admin.TabularInline):
    model = FeeVoucherItem
    extra = 1

@admin.register(FeeVoucher)
class FeeVoucherAdmin(admin.ModelAdmin):
    list_display = ('voucher_no', 'student', 'month', 'net_amount', 'status')
    list_filter = ('status', 'month')
    search_fields = ('voucher_no', 'student__full_name')
    inlines = [FeeVoucherItemInline]
    change_list_template = "fee_voucher_change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('generate-all-fees/', self.admin_site.admin_view(self.generate_fees_view), name='generate_all_fees'),
        ]
        return my_urls + urls

    def generate_fees_view(self, request):
        now = datetime.now()
        month = now.strftime("%B")
        year = now.year
        job = AutomationJob.objects.create(job_type='MANUAL_GENERATION', status='PENDING')
        FeeGenerationService.generate_monthly_fees(month, year, job_id=job.id)
        messages.success(request, f"Fee generation initiated! Job ID: {job.id}. Monitor progress in Automation Jobs.")
        return redirect('..')

@admin.register(FeeVoucherItem)
class FeeVoucherItemAdmin(admin.ModelAdmin):
    list_display = ('voucher', 'fee_head', 'amount')
    list_filter = ('voucher',)

from edupilot_core.models import Period, AssignedPeriods, Fixture, Absence

admin.site.register(Period)
admin.site.register(AssignedPeriods)
admin.site.register(Fixture)
admin.site.register(Absence)