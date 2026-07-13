from .models import (
    FeeHead, FeePlan, FeePlanDetail, TransportRoute, Scholarship,
    Student, StudentFeeAssignment, StudentLedger, StudentBalance, StudentPerformance,
    FeeVoucher, FeeVoucherItem, FeeGenerationSettings, FeeGenerationLog,
    Teacher, SalaryStructure, SalaryVoucher, SalaryAutomationSettings,
    SalaryAutomationJob, SalaryAutomationJobDetail,
    Staff, Transaction, AutomationJob, AutomationJobDetail, NotificationQueue
)

# Har entry: url slug -> { model, label, list_fields, fields }
# list_fields = list page ke table columns
# fields = '__all__' ya specific field list jo form mein dikhengi

CRUD_REGISTRY = {
    'feehead': {
        'model': FeeHead,
        'label': 'Fee Heads',
        'list_fields': ['name', 'frequency', 'status'],
        'fields': '__all__',
    },
    'feeplan': {
        'model': FeePlan,
        'label': 'Fee Plans',
        'list_fields': ['name', 'class_name', 'session'],
        'fields': '__all__',
    },
    'feeplandetail': {
        'model': FeePlanDetail,
        'label': 'Fee Plan Details',
        'list_fields': ['fee_plan', 'fee_head', 'amount'],
        'fields': '__all__',
    },
    'transportroute': {
        'model': TransportRoute,
        'label': 'Transport Routes',
        'list_fields': ['route_name', 'amount'],
        'fields': '__all__',
    },
    'scholarship': {
        'model': Scholarship,
        'label': 'Scholarships',
        'list_fields': ['name', 'discount_type', 'value'],
        'fields': '__all__',
    },
    'student': {
        'model': Student,
        'label': 'Students',
        'list_fields': ['full_name', 'admission_number', 'current_class', 'is_active'],
        'fields': '__all__',
    },
    'studentfeeassignment': {
        'model': StudentFeeAssignment,
        'label': 'Student Fee Assignments',
        'list_fields': ['student', 'fee_plan', 'transport_route', 'scholarship'],
        'fields': '__all__',
    },
    'studentledger': {
        'model': StudentLedger,
        'label': 'Student Ledgers',
        'list_fields': ['student', 'date', 'description', 'debit', 'credit', 'balance'],
        'fields': '__all__',
    },
    'studentbalance': {
        'model': StudentBalance,
        'label': 'Student Balances',
        'list_fields': ['student', 'outstanding_amount'],
        'fields': '__all__',
    },
    'studentperformance': {
        'model': StudentPerformance,
        'label': 'Student Performance',
        'list_fields': ['student', 'attendance_percentage', 'average_test_score', 'risk_level'],
        'fields': '__all__',
    },
    'feevoucher': {
        'model': FeeVoucher,
        'label': 'Fee Vouchers',
        'list_fields': ['voucher_no', 'student', 'month', 'year', 'net_amount', 'status'],
        'fields': '__all__',
    },
    'feevoucheritem': {
        'model': FeeVoucherItem,
        'label': 'Fee Voucher Items',
        'list_fields': ['voucher', 'fee_head', 'amount'],
        'fields': '__all__',
    },
    'feegenerationsettings': {
        'model': FeeGenerationSettings,
        'label': 'Fee Generation Settings',
        'list_fields': ['auto_enabled', 'generation_day', 'generation_time', 'send_notifications'],
        'fields': '__all__',
    },
    'feegenerationlog': {
        'model': FeeGenerationLog,
        'label': 'Fee Generation Logs',
        'list_fields': ['month', 'year', 'status', 'students_processed', 'success_count', 'failed_count'],
        'fields': '__all__',
    },
    'teacher': {
        'model': Teacher,
        'label': 'Teachers',
        'list_fields': ['name', 'teacher_id', 'designation', 'department', 'is_active'],
        'fields': '__all__',
    },
    'salarystructure': {
        'model': SalaryStructure,
        'label': 'Salary Structures',
        'list_fields': ['teacher', 'deductions'],
        'fields': '__all__',
    },
    'salaryvoucher': {
        'model': SalaryVoucher,
        'label': 'Salary Vouchers',
        'list_fields': ['teacher', 'month', 'year', 'net_salary', 'status'],
        'fields': '__all__',
    },
    'salaryautomationsettings': {
        'model': SalaryAutomationSettings,
        'label': 'Salary Automation Settings',
        'list_fields': ['auto_enabled', 'generation_day', 'generation_time', 'send_notifications'],
        'fields': '__all__',
    },
    'salaryautomationjob': {
        'model': SalaryAutomationJob,
        'label': 'Salary Automation Jobs',
        'list_fields': ['id', 'status', 'started_at', 'success_count', 'failed_count'],
        'fields': '__all__',
    },
    'salaryautomationjobdetail': {
        'model': SalaryAutomationJobDetail,
        'label': 'Salary Job Details',
        'list_fields': ['job', 'teacher', 'status', 'error_message'],
        'fields': '__all__',
    },
    'staff': {
        'model': Staff,
        'label': 'Staff',
        'list_fields': ['name', 'role', 'is_active'],
        'fields': '__all__',
    },
    'transaction': {
        'model': Transaction,
        'label': 'Transactions',
        'list_fields': ['title', 'amount', 'type', 'date'],
        'fields': '__all__',
    },
    'automationjob': {
        'model': AutomationJob,
        'label': 'Automation Jobs',
        'list_fields': ['id', 'job_type', 'status', 'processed_count', 'success_count', 'failed_count'],
        'fields': '__all__',
    },
    'automationjobdetail': {
        'model': AutomationJobDetail,
        'label': 'Automation Job Details',
        'list_fields': ['job', 'student', 'status', 'error_message'],
        'fields': '__all__',
    },
    'notificationqueue': {
        'model': NotificationQueue,
        'label': 'Notification Queue (Data)',
        'list_fields': ['student', 'teacher', 'notification_type', 'status', 'created_at'],
        'fields': '__all__',
    },
}