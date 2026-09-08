from django.apps import AppConfig


class ExamSystemConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'exam_system'

    def ready(self):
        from . import signals  # noqa: F401
