
# from django.apps import AppConfig

# class EdupilotCoreConfig(AppConfig):
#     default_auto_field = 'django.db.models.BigAutoField'
#     name = 'edupilot_core'

#     def ready(self):
#         import os
#         if os.environ.get('RUN_MAIN') == 'true':
#             from . import updater
#             updater.start()

from django.apps import AppConfig

class EdupilotCoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'edupilot_core'

    def ready(self):
        import os
        from . import canonical_sync  # noqa: F401
        from . import voucher_delivery  # noqa: F401

        if os.environ.get('RUN_MAIN') == 'true':
            try:
                from . import updater
                updater.start()
                print("✅ SCHEDULER STARTED SUCCESSFULLY!")
            except Exception as e:
                print(f"❌ Scheduler Error: {e}")
