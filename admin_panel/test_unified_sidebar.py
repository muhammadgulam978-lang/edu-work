from types import SimpleNamespace

from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase


class UnifiedSidebarTemplateTests(SimpleTestCase):
    def setUp(self):
        self.request_factory = RequestFactory()

    def render_sidebar(self, portal, menu_template, path="/"):
        request = self.request_factory.get(path)
        request.user = AnonymousUser()
        return render_to_string(
            "shared/sidebar/shell.html",
            {
                "request": request,
                "sidebar_portal": portal,
                "sidebar_menu_template": menu_template,
            },
            request=request,
        )

    def test_all_portal_menus_render_through_one_shell(self):
        variants = (
            ("admin", "admin_panel/sidebar.html", "AI Analytics"),
            ("teacher", "teacher_dashboard/sidebar.html", "Lesson Plans"),
            ("student", "student_profile/sidebar.html", "AI Tutor"),
            ("parent", "parent_dashboard/sidebar.html", "Student Progress"),
            ("automation", "automation/sidebar.html", "Data Management"),
        )

        for portal, menu_template, expected_label in variants:
            with self.subTest(portal=portal):
                html = self.render_sidebar(portal, menu_template)
                self.assertEqual(html.count("data-edu-sidebar\n"), 1)
                self.assertEqual(html.count("edupilot-logo-2026-nav.png"), 1)
                self.assertIn(expected_label, html)

    def test_role_menus_do_not_expose_admin_only_operations(self):
        for portal, menu_template in (
            ("teacher", "teacher_dashboard/sidebar.html"),
            ("student", "student_profile/sidebar.html"),
            ("parent", "parent_dashboard/sidebar.html"),
        ):
            with self.subTest(portal=portal):
                html = self.render_sidebar(portal, menu_template)
                self.assertNotIn("Procurement &amp; Inventory", html)
                self.assertNotIn("Transportation &amp; Fleet", html)

    def test_teacher_context_menu_keeps_existing_lms_destinations(self):
        request = self.request_factory.get("/teacher/lms/1/2/3/")
        request.user = AnonymousUser()
        html = render_to_string(
            "shared/sidebar/shell.html",
            {
                "request": request,
                "sidebar_portal": "teacher",
                "sidebar_menu_template": "teacher_dashboard/sidebar.html",
                "class_obj": SimpleNamespace(id=1),
                "section_obj": SimpleNamespace(id=2),
                "subject_obj": SimpleNamespace(id=3),
            },
            request=request,
        )

        self.assertIn("Current Subject", html)
        self.assertIn("Assignment Submissions", html)
        self.assertIn("Lecture Notes", html)
        self.assertIn("Quiz Submissions", html)
        self.assertIn("Diary", html)
