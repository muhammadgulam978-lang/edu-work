from django.test import TestCase
from openpyxl import Workbook

from edupilot_core.models import EmailOutbox, FeePlan, StudentFeeAssignment
from parent_dashboard.models import Parent, StudentGuardian
from student_profile.models import Student

from .bulk_student_import import import_students_from_worksheet
from .models import AcademicYear, Admission, Class


class BulkStudentImportTests(TestCase):
    def setUp(self):
        self.year = AcademicYear.objects.create(year='2026-27', is_active=True)
        self.school_class = Class.objects.create(class_name='Grade 5')
        self.fee_plan = FeePlan.objects.create(
            name='Grade 5 Plan', class_name='Grade 5', session='2026-27'
        )

    def worksheet(self, headers, rows):
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(headers)
        for row in rows:
            sheet.append(row)
        return sheet

    def test_optional_columns_generate_safe_defaults_and_fee_assignment(self):
        sheet = self.worksheet(
            ['S.No', 'Class', 'Fee_Plan'],
            [[1, 'Grade 5', 'Grade 5 Plan']],
        )

        result = import_students_from_worksheet(sheet, self.year)

        self.assertEqual(result.imported, 1, result.errors)
        self.assertEqual(result.enrolled, 1)
        self.assertEqual(result.fee_ready, 1)
        student = Student.objects.get()
        self.assertEqual(student.name, 'N/A')
        self.assertTrue(student.student_id.startswith('STU-'))
        self.assertFalse(student.user.has_usable_password())
        self.assertEqual(Admission.objects.get().admission_status, 'approved')
        self.assertEqual(
            StudentFeeAssignment.objects.get(canonical_student=student).fee_plan,
            self.fee_plan,
        )

    def test_duplicate_row_is_skipped_without_rolling_back_valid_rows(self):
        sheet = self.worksheet(
            ['Student_Id', 'Student Name', 'Email', 'Login_Id'],
            [
                ['STU-100', 'First Student', 'first@example.com', 'first.student'],
                ['STU-100', 'Duplicate Student', 'second@example.com', 'second.student'],
                ['STU-101', 'Third Student', 'third@example.com', 'third.student'],
            ],
        )

        result = import_students_from_worksheet(sheet, self.year)

        self.assertEqual(result.imported, 2)
        self.assertEqual(result.skipped, 1)
        self.assertEqual(Student.objects.count(), 2)
        self.assertIn("Student ID 'STU-100' already exists", result.errors[0])

    def test_parent_account_is_created_linked_and_credentials_are_queued(self):
        sheet = self.worksheet(
            [
                'Student_Id', 'Student Name', 'Email', 'Class',
                'Parent_Name', 'Parent_Email', 'Parent_Relationship',
            ],
            [[
                'STU-200', 'Sara Ahmed', 'sara.ahmed@example.com', 'Grade 5',
                'Ahmed Raza', 'ahmed.raza@example.com', 'Father',
            ]],
        )

        result = import_students_from_worksheet(sheet, self.year)

        self.assertEqual(result.imported, 1, result.errors)
        student = Student.objects.get(student_id='STU-200')
        parent = Parent.objects.get(email='ahmed.raza@example.com')
        self.assertEqual(result.parents_linked, 1)
        self.assertEqual(result.parent_accounts_created, 1)
        self.assertEqual(result.credential_emails_queued, 2)
        self.assertTrue(parent.students.filter(pk=student.pk).exists())
        self.assertTrue(parent.user.has_usable_password())
        self.assertTrue(student.user.has_usable_password())
        self.assertTrue(StudentGuardian.objects.filter(
            parent=parent, student=student, is_primary=True
        ).exists())
        self.assertEqual(EmailOutbox.objects.filter(status='PENDING').count(), 2)

    def test_existing_parent_is_reused_without_password_change(self):
        from django.contrib.auth.models import User

        user = User.objects.create_user(
            username='existing.parent', email='parent@example.com', password='KeepMe@12345'
        )
        parent = Parent.objects.create(
            user=user, full_name='Existing Parent', email='parent@example.com'
        )
        sheet = self.worksheet(
            ['Student_Id', 'Student Name', 'Parent_Email', 'Parent_Password'],
            [['STU-201', 'Second Child', 'parent@example.com', 'DoNotUse@12345']],
        )

        result = import_students_from_worksheet(sheet, self.year)

        user.refresh_from_db()
        self.assertEqual(Parent.objects.count(), 1)
        self.assertEqual(result.parent_accounts_created, 0)
        self.assertTrue(user.check_password('KeepMe@12345'))
        self.assertTrue(parent.students.filter(student_id='STU-201').exists())
