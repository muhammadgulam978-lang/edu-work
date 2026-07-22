from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class UnifiedButtonThemeTests(SimpleTestCase):
    portal_bases = (
        "admin_panel/templates/admin_panel/base.html",
        "admin_panel/templates/admin_panel/bases.html",
        "teacher_dashboard/templates/teacher_dashboard/base.html",
        "teacher_dashboard/templates/teacher_dashboard/bases.html",
        "teacher_dashboard/templates/teacher_dashboard/lms_base.html",
        "teacher_dashboard/templates/teacher_dashboard/lms_action_base.html",
        "student_profile/templates/student_profile/base.html",
        "student_profile/templates/student_profile/bases.html",
        "parent_dashboard/templates/parent_dashboard/base.html",
        "edupilot_core/templates/automation/base_automation.html",
        "edupilot_core/templates/teacher_dashboard/base.html",
        "edupilot_core/templates/teacher_dashboard/bases.html",
        "edupilot_core/templates/teacher_dashboard/lms_base.html",
        "edupilot_core/templates/teacher_dashboard/lms_action_base.html",
        "edupilot_core/templates/student_profile/base.html",
        "edupilot_core/templates/student_profile/bases.html",
    )

    auth_templates = (
        "login/templates/registration/login.html",
        "login/templates/registration/role_login.html",
        "edupilot_core/templates/login.html",
    )

    def read_project_file(self, relative_path):
        return (Path(settings.BASE_DIR) / relative_path).read_text(encoding="utf-8")

    def test_shared_stylesheet_exposes_the_public_button_interface(self):
        css = self.read_project_file(
            "admin_panel/static/admin_panel/css/edupilot-buttons.css"
        )

        for selector in (
            ".edu-button-theme",
            ".edu-btn-primary",
            ".edu-btn-secondary",
            ".edu-btn-success",
            ".edu-btn-warning",
            ".edu-btn-danger",
            ".edu-icon-btn",
        ):
            with self.subTest(selector=selector):
                self.assertIn(selector, css)

        self.assertIn(".btn-close", css)
        self.assertIn(".pagination *", css)
        self.assertIn("prefers-reduced-motion", css)

    def test_every_authenticated_portal_base_enables_the_theme(self):
        for relative_path in self.portal_bases:
            with self.subTest(template=relative_path):
                template = self.read_project_file(relative_path)
                self.assertIn("edupilot-buttons.css", template)
                self.assertIn("edu-button-theme", template)

    def test_authentication_entry_templates_are_not_themed(self):
        for relative_path in self.auth_templates:
            path = Path(settings.BASE_DIR) / relative_path
            if not path.exists():
                continue
            with self.subTest(template=relative_path):
                template = path.read_text(encoding="utf-8")
                self.assertNotIn("edupilot-buttons.css", template)
                self.assertNotIn("edu-button-theme", template)
