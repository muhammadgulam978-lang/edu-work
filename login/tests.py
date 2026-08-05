from django.test import TestCase
from django.urls import reverse


class PortalSessionHostTests(TestCase):
    def test_selector_builds_separate_local_portal_hosts(self):
        response = self.client.get(reverse("login"), HTTP_HOST="localhost:8000")

        self.assertContains(
            response,
            'href="http://admin.localhost:8000/login/admin/"',
        )
        self.assertContains(
            response,
            'href="http://teacher.localhost:8000/login/teacher/"',
        )
        self.assertContains(
            response,
            'href="http://student.localhost:8000/login/student/"',
        )
        self.assertContains(
            response,
            'href="http://parent.localhost:8000/login/parent/"',
        )

    def test_role_login_redirects_to_its_isolated_local_host(self):
        response = self.client.get(
            reverse("login_student"),
            HTTP_HOST="localhost:8000",
        )

        self.assertRedirects(
            response,
            "http://student.localhost:8000/login/student/",
            fetch_redirect_response=False,
        )

    def test_role_login_renders_on_matching_portal_host(self):
        response = self.client.get(
            reverse("login_teacher"),
            HTTP_HOST="teacher.localhost:8000",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Teacher Login")
