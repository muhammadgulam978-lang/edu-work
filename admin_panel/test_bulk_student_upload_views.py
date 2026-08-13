from datetime import date
from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from openpyxl import Workbook

from student_profile.models import Student

from .models import AcademicYear, Admission


class BulkStudentUploadViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('bulk.admin', 'bulk@example.com', 'Test@12345')
        self.client.force_login(self.admin)
        self.year = AcademicYear.objects.create(year='2026-27', is_active=True)

    def upload_file(self, student_id='STU-VIEW-1'):
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(['Student_Id', 'Student Name', 'Email', 'Parent_Name', 'Parent_Email'])
        sheet.append([
            student_id, 'View Test Student', f'{student_id.lower()}@example.com',
            'View Test Parent', f'parent.{student_id.lower()}@example.com',
        ])
        stream = BytesIO()
        workbook.save(stream)
        return SimpleUploadedFile(
            'students.xlsx', stream.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

    def test_screen_template_download_and_live_activity_render(self):
        screen = self.client.get(reverse('bulk_upload_students'))
        self.assertEqual(screen.status_code, 200)
        self.assertContains(screen, 'Bulk Student & Parent Import')
        self.assertContains(screen, 'data-progress-overlay')
        self.assertContains(screen, 'Estimated remaining')
        self.assertContains(screen, 'name="csrfmiddlewaretoken"')
        self.assertIn('csrftoken', self.client.cookies)
        self.assertContains(
            screen,
            f'action="{reverse("bulk_upload_students")}"',
            count=1,
        )

        template = self.client.get(reverse('bulk_upload_students_template'))
        self.assertEqual(template.status_code, 200)
        self.assertIn('spreadsheetml', template['Content-Type'])

        activity = self.client.get(reverse('bulk_upload_students_activity'))
        self.assertEqual(activity.status_code, 200)
        self.assertEqual(activity.json()['student_count'], 0)

    def test_anonymous_bulk_routes_redirect_to_admin_login(self):
        anonymous = Client()

        for route_name in (
            'bulk_upload_students',
            'bulk_upload_students_template',
            'bulk_upload_students_activity',
            'bulk_upload_students_progress',
        ):
            response = anonymous.get(reverse(route_name))
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.url.startswith(reverse('login_admin')))

    def test_ajax_preview_accepts_django_csrf_header(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.admin)
        screen = csrf_client.get(reverse('bulk_upload_students'))
        self.assertEqual(screen.status_code, 200)
        csrf_token = csrf_client.cookies['csrftoken'].value

        response = csrf_client.post(
            reverse('bulk_upload_students'),
            {
                'action': 'preview',
                'csrfmiddlewaretoken': csrf_token,
                'excel_file': self.upload_file('STU-CSRF-1'),
            },
            HTTP_X_CSRFTOKEN=csrf_token,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Validation Preview')

    def test_preview_then_confirm_creates_live_student_and_parent(self):
        preview = self.client.post(
            reverse('bulk_upload_students'),
            {'action': 'preview', 'excel_file': self.upload_file()},
        )
        self.assertEqual(preview.status_code, 200)
        self.assertContains(preview, 'Validation Preview')
        token = self.client.session['bulk_student_pending']['token']

        confirmed = self.client.post(
            reverse('bulk_upload_students'),
            {'action': 'confirm', 'upload_token': token},
            follow=True,
        )
        self.assertEqual(confirmed.status_code, 200)
        self.assertContains(confirmed, 'Complete Import Report')
        self.assertContains(confirmed, 'Portal logins ready')
        self.assertContains(confirmed, 'Emails sent')
        self.assertTrue(Student.objects.filter(student_id='STU-VIEW-1').exists())

        activity = self.client.get(reverse('bulk_upload_students_activity')).json()
        self.assertEqual(activity['result']['login_ready'], 2)
        self.assertEqual(activity['result']['total_rows'], 1)

    def test_chunked_progress_reports_committed_rows_and_finishes(self):
        preview = self.client.post(
            reverse('bulk_upload_students'),
            {'action': 'preview', 'excel_file': self.upload_file('STU-PROGRESS-1')},
        )
        self.assertEqual(preview.status_code, 200)
        token = self.client.session['bulk_student_pending']['token']

        start = self.client.post(reverse('bulk_upload_students_progress'), {
            'operation': 'start', 'upload_token': token,
        })
        self.assertEqual(start.status_code, 200)
        self.assertEqual(start.json()['processed_rows'], 0)

        process = self.client.post(reverse('bulk_upload_students_progress'), {
            'operation': 'process', 'upload_token': token,
            'cursor': start.json()['cursor'],
        })
        payload = process.json()
        self.assertEqual(process.status_code, 200)
        self.assertTrue(payload['done'])
        self.assertEqual(payload['percent'], 100)
        self.assertEqual(payload['processed_rows'], 1)
        self.assertTrue(Student.objects.filter(student_id='STU-PROGRESS-1').exists())

    def test_progress_start_resumes_existing_import_state(self):
        session = self.client.session
        session['bulk_student_pending'] = {
            'token': 'resume-token',
            'path': 'bulk_upload_previews/user_1/resume.xlsx',
            'total_rows': 10,
            'valid_rows': 10,
            'invalid_rows': 0,
        }
        session['bulk_student_progress'] = {
            'token': 'resume-token',
            'next_row': 7,
            'total_rows': 10,
            'processed_rows': 5,
            'started_at': 1,
            'result': {},
        }
        session.save()

        response = self.client.post(
            reverse('bulk_upload_students_progress'),
            {'operation': 'start', 'upload_token': 'resume-token'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['cursor'], 7)
        self.assertEqual(response.json()['processed_rows'], 5)

    def test_admission_student_name_links_to_insight_profile(self):
        student = Student.objects.create(
            student_id='STU-LINK-1', name='Linked Student', father_name='Father',
            mother_name='Mother', roll_no='1', date_of_birth=date.today(),
            email='linked.student@example.com', academic_year=self.year,
        )
        Admission.objects.create(
            student_id=student.student_id, campus='Main', branch='Main', ref_no='REF-LINK',
            name=student.name, dob=date.today(), email=student.email, contact='N/A',
            address='N/A', admission_date=date.today(), father_name='Father',
            mother_name='Mother', father_contact='N/A', father_occupation='N/A',
            father_cnic='N/A', academic_year=self.year, nationality='Pakistani',
            admission_status='approved',
        )

        response = self.client.get(reverse('admission_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, reverse('admin_ai_student_intelligence_detail', args=[student.student_id])
        )
