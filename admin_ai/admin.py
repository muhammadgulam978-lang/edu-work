from django.contrib import admin

from .models import (
    AdminAIConversation,
    AdminAIMessage,
    AdminAIReport,
    AdminAIReportShareLog,
    AdminAIStudentProfileSnapshot,
    AdminAIToolAuditLog,
)


admin.site.register(AdminAIConversation)
admin.site.register(AdminAIMessage)
admin.site.register(AdminAIToolAuditLog)
admin.site.register(AdminAIReport)
admin.site.register(AdminAIReportShareLog)
admin.site.register(AdminAIStudentProfileSnapshot)

