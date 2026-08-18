from django.contrib import admin

from .models import (
    CounsellingAppointment,
    CounsellingCase,
    CounsellingReferral,
    CounsellingSession,
    ExternalReferralContact,
    SafeguardingConcern,
    StudentSupportPlan,
    WellbeingCheckIn,
)

admin.site.register(CounsellingReferral)
admin.site.register(CounsellingCase)
admin.site.register(CounsellingSession)
admin.site.register(StudentSupportPlan)
admin.site.register(CounsellingAppointment)
admin.site.register(WellbeingCheckIn)
admin.site.register(SafeguardingConcern)
admin.site.register(ExternalReferralContact)
