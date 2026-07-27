from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class UnifiedNeutralSurfaceTests(SimpleTestCase):
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

    def read_project_file(self, relative_path):
        return (Path(settings.BASE_DIR) / relative_path).read_text(encoding="utf-8")

    def test_every_authenticated_portal_loads_the_neutral_surface_last(self):
        for relative_path in self.portal_bases:
            with self.subTest(template=relative_path):
                template = self.read_project_file(relative_path)
                self.assertIn("edu-neutral-surfaces", template)
                self.assertIn("edupilot-surfaces.css", template)
                self.assertGreater(
                    template.index("edupilot-surfaces.css"),
                    template.index("edupilot-buttons.css"),
                )

    def test_surface_layer_targets_marked_controls_without_sidebar_rules(self):
        css = self.read_project_file(
            "admin_panel/static/admin_panel/css/edupilot-surfaces.css"
        )

        for selector in (
            ".edu-portal-search button",
            ".edu-portal-icon-button",
            ".edu-portal-profile",
            ".ai-prompt-row button",
            ".ai-filter-actions button",
            ".ai-snapshot-card",
            ".admin-ai-fab",
        ):
            with self.subTest(selector=selector):
                self.assertIn(selector, css)

        self.assertNotRegex(
            css,
            r"\.edu-neutral-surfaces\s+\.edu-reference-sidebar\s*\{",
        )
        self.assertNotIn(".deznav", css)

    def test_functional_header_and_ai_hooks_are_preserved(self):
        header = self.read_project_file("templates/shared/header/portal_header.html")
        ai_overview = self.read_project_file(
            "admin_panel/templates/admin_panel/ai_analytics.html"
        )
        ai_fab = self.read_project_file(
            "admin_panel/templates/admin_panel/includes/admin_ai_fab.html"
        )

        for hook in (
            "data-admin-search-form",
            "data-admin-notification-toggle",
            'data-edu-menu-toggle="profile"',
        ):
            self.assertIn(hook, header)

        self.assertIn("data-copilot-form", ai_overview)
        self.assertIn("data-command", ai_overview)
        self.assertIn("data-filter-reset", ai_overview)
        self.assertIn("data-admin-ai-fab", ai_fab)
        self.assertIn("pointermove", ai_fab)

    def test_public_login_templates_do_not_receive_the_portal_theme(self):
        for relative_path in (
            "login/templates/registration/login.html",
            "login/templates/registration/role_login.html",
            "edupilot_core/templates/login.html",
        ):
            path = Path(settings.BASE_DIR) / relative_path
            if not path.exists():
                continue
            with self.subTest(template=relative_path):
                template = path.read_text(encoding="utf-8")
                self.assertNotIn("edupilot-surfaces.css", template)
                self.assertNotIn("edu-neutral-surfaces", template)
