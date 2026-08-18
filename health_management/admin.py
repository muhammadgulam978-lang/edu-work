from django.contrib import admin

from .models import (
    AllergyRecord,
    ChronicCondition,
    EmergencyCase,
    HealthCheckupCycle,
    HealthCheckupRecord,
    HealthNotification,
    HealthProfile,
    MedicalVisit,
    Medicine,
    MedicineAdministration,
    MedicineBatch,
    SickBayAdmission,
)

admin.site.register(HealthProfile)
admin.site.register(AllergyRecord)
admin.site.register(ChronicCondition)
admin.site.register(HealthCheckupCycle)
admin.site.register(HealthCheckupRecord)
admin.site.register(MedicalVisit)
admin.site.register(EmergencyCase)
admin.site.register(SickBayAdmission)
admin.site.register(Medicine)
admin.site.register(MedicineBatch)
admin.site.register(MedicineAdministration)
admin.site.register(HealthNotification)
