from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from admin_panel.models import AcademicYear


class LiveExamAnalyticsTests(TestCase):
    def setUp(self):
        self.user = User(
            username="exam-chart-user",
            password=make_password("test-pass"),
            is_active=True,
        )
        User.objects.bulk_create([self.user])
        self.user.refresh_from_db()
        self.client = Client(HTTP_HOST="127.0.0.1")
        self.client.force_login(self.user)

    def test_empty_exam_analytics_is_live_and_structured(self):
        AcademicYear.objects.create(year="2026-2027", is_active=True)
        response = self.client.get(reverse("analytics_data"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["kpis"][0]["value"], 0)
        self.assertEqual(payload["subject_performance"]["labels"], [])
        self.assertEqual(payload["grade_distribution"]["values"], [])

    def test_exam_analytics_page_keeps_table_and_adds_shared_graphs(self):
        AcademicYear.objects.create(year="2026-2027", is_active=True)
        response = self.client.get(reverse("analytics_dashboard"))
        self.assertContains(response, 'id="examSubjectChart"')
        self.assertContains(response, 'id="examGradeChart"')
        self.assertContains(response, "Subject-wise Performance")
        self.assertContains(response, "edupilot-charts.js")
