from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Student


class UnassignedStudentPortalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="unassigned.student",
            password="StudentPass123!",
            email="unassigned.student@example.com",
        )
        self.student = Student.objects.create(
            user=self.user,
            student_id="UNASSIGNED-001",
            name="Unassigned Student",
            father_name="Parent One",
            mother_name="Parent Two",
            class_fk=None,
            section=None,
            roll_no="PENDING",
            gender="Male",
            date_of_birth=date(2012, 1, 1),
            email="unassigned.student@example.com",
        )

    def test_dashboard_is_available_without_class_or_section(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("student_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome to your student portal")
        self.assertContains(response, "Not assigned yet")
        self.assertContains(response, "Courses will appear after your class is assigned.")

    def test_role_login_allows_student_without_class_or_section(self):
        response = self.client.post(
            reverse("login_student"),
            {
                "username": "unassigned.student",
                "password": "StudentPass123!",
            },
        )

        self.assertRedirects(response, reverse("student_dashboard"))

    def test_academic_portal_pages_remain_available_without_placement(self):
        self.client.force_login(self.user)

        route_names = (
            "student_attendance",
            "student_result",
            "student_assignments",
            "student_quizzes",
            "student_diary",
            "student_timetable",
            "ai_tutor_dashboard",
        )
        for route_name in route_names:
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
