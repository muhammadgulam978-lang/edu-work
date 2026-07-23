from pathlib import Path

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse


class AIAdminDesignContractTests(SimpleTestCase):
    ai_templates = (
        "admin_ai/templates/admin_ai/copilot.html",
        "admin_ai/templates/admin_ai/advanced_analytics.html",
        "admin_ai/templates/admin_ai/reports.html",
        "admin_ai/templates/admin_ai/report_detail.html",
        "admin_ai/templates/admin_ai/student_intelligence.html",
        "admin_ai/templates/admin_ai/student_intelligence_detail.html",
        "admin_ai/templates/admin_ai/includes/auto_report_modal.html",
    )

    def read_project_file(self, relative_path):
        return (Path(settings.BASE_DIR) / relative_path).read_text(encoding="utf-8")

    def test_admin_bases_load_the_shared_design_after_existing_layers(self):
        for relative_path in (
            "admin_panel/templates/admin_panel/base.html",
            "admin_panel/templates/admin_panel/bases.html",
        ):
            with self.subTest(template=relative_path):
                template = self.read_project_file(relative_path)
                self.assertIn("ai-admin-design.css", template)
                self.assertGreater(
                    template.index("ai-admin-design.css"),
                    template.index("edupilot-surfaces.css"),
                )

    def test_ai_templates_no_longer_embed_conflicting_style_systems(self):
        for relative_path in self.ai_templates:
            with self.subTest(template=relative_path):
                template = self.read_project_file(relative_path)
                self.assertNotIn("<style", template)
                self.assertNotIn("border-radius:999", template)
                self.assertNotIn("linear-gradient(90deg,#DDF7F2", template)

    def test_shared_design_exposes_required_screen_families(self):
        css = self.read_project_file(
            "admin_panel/static/admin_panel/css/ai-admin-design.css"
        )
        for selector in (
            ".admin-ai-page",
            ".ai-advanced",
            ".ai-report",
            ".ai-student",
            ".student-360-page",
            ".ai-report-popup",
            ".ai-table-actions",
            ".ai-overview-page",
            ".live-dashboard",
        ):
            with self.subTest(selector=selector):
                self.assertIn(selector, css)


class AIAdminDesignRenderTests(TestCase):
    def setUp(self):
        self.admin = User(
            username="ai-design-admin",
            email="ai-design@example.com",
            password=make_password("test-pass"),
            is_staff=True,
            is_superuser=True,
            is_active=True,
        )
        User.objects.bulk_create([self.admin])
        self.admin.refresh_from_db()
        self.client = Client(HTTP_HOST="127.0.0.1")
        self.client.force_login(self.admin)

    def test_every_sidebar_ai_destination_renders_with_shared_design(self):
        destinations = (
            "ai_analytics_dashboard",
            "admin_ai_copilot",
            "ai_analytics_advanced",
            "ai_analytics_reports",
            "admin_ai_student_intelligence",
        )
        for name in destinations:
            with self.subTest(route=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "ai-admin-design.css")

        overview = self.client.get(reverse("ai_analytics_dashboard"))
        self.assertContains(overview, 'id="ai-risk-index"')
        self.assertContains(overview, 'id="system-health"')
