from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from student_profile.models import Student

from .models import AcademicYear, Class, Section


class StudentDirectoryTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='directory-admin',
            email='directory-admin@example.com',
            password='Admin@2026!',
        )
        self.student_user = User.objects.create_user(
            username='dir.student',
            email='dir.student@example.com',
            password='Original@2026!',
        )
        self.year = AcademicYear.objects.create(year='2026-27', is_active=True)
        self.class_obj = Class.objects.create(class_name='Directory Grade 5')
        self.section = Section.objects.create(
            academic_year=self.year,
            class_fk=self.class_obj,
            section_name='A',
            capacity=40,
        )
        self.student = Student.objects.create(
            user=self.student_user,
            academic_year=self.year,
            class_fk=self.class_obj,
            section=self.section,
            student_id='DIR-STU-001',
            name='Ali Directory Khan',
            father_name='Farhan Directory Khan',
            mother_name='Sadia Directory Khan',
            roll_no='D5-A-01',
            phone='+923001112233',
            gender='Male',
            date_of_birth=date(2015, 4, 12),
            email='dir.student@example.com',
            nationality='Pakistani',
            address='Main Campus Road',
            admission_date=date(2026, 1, 15),
        )
        self.client.force_login(self.admin)

    def test_directory_lists_and_searches_canonical_students(self):
        response = self.client.get(reverse('student_directory'), {'q': 'Farhan Directory'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.student.name)
        self.assertContains(response, self.student.student_id)

    def test_complete_profile_shows_placement_and_secure_login_details(self):
        response = self.client.get(reverse('student_directory_detail', args=[self.student.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.student.name)
        self.assertContains(response, self.class_obj.class_name)
        self.assertContains(response, self.section.section_name)
        self.assertContains(response, self.student_user.username)
        self.assertContains(response, 'Passwords are securely hashed and cannot be displayed')

    def test_edit_updates_canonical_student_and_linked_account(self):
        response = self.client.post(
            reverse('student_directory_update', args=[self.student.pk]),
            {
                'student_id': self.student.student_id,
                'name': 'Ali Updated Khan',
                'father_name': self.student.father_name,
                'mother_name': self.student.mother_name,
                'academic_year': self.year.pk,
                'class_fk': self.class_obj.pk,
                'section': self.section.pk,
                'roll_no': 'D5-A-02',
                'gender': 'Male',
                'date_of_birth': '2015-04-12',
                'email': 'ali.updated@example.com',
                'phone': self.student.phone,
                'nationality': self.student.nationality,
                'address': self.student.address,
                'blood_group': '',
                'medical_notes': '',
                'emergency_contact_name': '',
                'emergency_contact_phone': '',
                'admission_date': '2026-01-15',
                'previous_school': '',
                'username': 'ali.updated.student',
                'account_active': 'on',
            },
        )

        self.assertRedirects(response, reverse('student_directory_detail', args=[self.student.pk]))
        self.student.refresh_from_db()
        self.student_user.refresh_from_db()
        self.assertEqual(self.student.name, 'Ali Updated Khan')
        self.assertEqual(self.student.roll_no, 'D5-A-02')
        self.assertEqual(self.student_user.username, 'ali.updated.student')
        self.assertEqual(self.student_user.email, 'ali.updated@example.com')

    def test_password_reset_hashes_password_on_same_account(self):
        response = self.client.post(
            reverse('student_directory_reset_password', args=[self.student.pk]),
            {
                'username': self.student_user.username,
                'password': 'NewStudent@2026!',
                'password_confirm': 'NewStudent@2026!',
            },
        )

        self.assertRedirects(response, reverse('student_directory_detail', args=[self.student.pk]))
        self.student_user.refresh_from_db()
        self.student.refresh_from_db()
        self.assertEqual(self.student.user_id, self.student_user.pk)
        self.assertTrue(self.student_user.check_password('NewStudent@2026!'))
        self.assertNotEqual(self.student_user.password, 'NewStudent@2026!')

    def test_delete_requires_exact_student_id_confirmation(self):
        url = reverse('student_directory_delete', args=[self.student.pk])

        rejected = self.client.post(url, {'confirmation': 'wrong-id'})
        self.assertEqual(rejected.status_code, 200)
        self.assertTrue(Student.objects.filter(pk=self.student.pk).exists())

        accepted = self.client.post(url, {'confirmation': self.student.student_id})
        self.assertRedirects(accepted, reverse('student_directory'))
        self.assertFalse(Student.objects.filter(pk=self.student.pk).exists())
