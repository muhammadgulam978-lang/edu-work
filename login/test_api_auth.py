from datetime import date

from django.contrib.auth.models import Group, User
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from student_profile.models import Student


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class StudentAuthenticationAPITests(APITestCase):
    def setUp(self):
        self.student_group = Group.objects.create(name="Student")
        self.user = User.objects.create_user(
            username="student001",
            email="student@example.com",
            password="StrongPass123!",
        )
        self.user.groups.add(self.student_group)
        self.student = Student.objects.create(
            user=self.user,
            student_id="STD-001",
            name="Ali Ahmed",
            father_name="Ahmed",
            mother_name="Ayesha",
            roll_no="1",
            date_of_birth=date(2012, 1, 1),
            email="student@example.com",
        )
        self.login_url = "/api/v1/auth/student/login/"

    def login(self, identifier="student001", password="StrongPass123!"):
        return self.client.post(
            self.login_url,
            {"identifier": identifier, "password": password},
            format="json",
        )

    def test_login_accepts_login_id_and_returns_safe_profile(self):
        response = self.login()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["role"], "student")
        self.assertEqual(response.data["user"]["student_id"], "STD-001")
        self.assertNotIn("password", response.data["user"])
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_accepts_email_case_insensitively(self):
        response = self.login("STUDENT@EXAMPLE.COM")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_bad_password_and_unknown_user_have_same_error(self):
        bad_password = self.login(password="wrong")
        unknown = self.login(identifier="unknown@example.com")
        self.assertEqual(bad_password.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(bad_password.data, unknown.data)
        self.assertEqual(bad_password.data["error"]["code"], "invalid_credentials")

    def test_non_student_role_is_rejected(self):
        teacher = User.objects.create_user(username="teacher", password="StrongPass123!")
        teacher_group, _ = Group.objects.get_or_create(name="Teacher")
        teacher.groups.set([teacher_group])
        response = self.login(identifier=teacher.username)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["error"]["code"], "role_not_allowed")

    def test_inactive_student_is_rejected(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        response = self.login()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["error"]["code"], "account_inactive")

    def test_missing_student_profile_is_rejected(self):
        self.student.user = None
        self.student.save(update_fields=["user"])
        response = self.login()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["error"]["code"], "student_profile_missing")

    def test_me_refresh_and_logout_flow(self):
        login_response = self.login()
        access = login_response.data["access"]
        refresh = login_response.data["refresh"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        me_response = self.client.get("/api/v1/auth/me/")
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data["user"]["login_id"], "student001")

        self.client.credentials()
        refresh_response = self.client.post(
            "/api/v1/auth/token/refresh/", {"refresh": refresh}, format="json"
        )
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_response.data)
        self.assertIn("refresh", refresh_response.data)

        logout_response = self.client.post(
            "/api/v1/auth/logout/",
            {"refresh": refresh_response.data["refresh"]},
            format="json",
        )
        self.assertEqual(logout_response.status_code, status.HTTP_204_NO_CONTENT)
        reused = self.client.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": refresh_response.data["refresh"]},
            format="json",
        )
        self.assertEqual(reused.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(reused.data["error"]["code"], "token_invalid")
