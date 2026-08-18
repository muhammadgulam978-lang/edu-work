from datetime import date

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from edupilot_core.models import FeeHead, FeePlan, FeePlanDetail, FeeVoucher
from parent_dashboard.models import Parent, StudentGuardian
from student_profile.models import Student

from .admission_services import approve_and_enroll, submit_for_review
from .models import (
    AcademicYear, AdmissionDocument, AdmissionGuardian, Class, Section,
    StudentAdmissionWorkflow,
)


class StudentAdmissionWorkflowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            'admission-admin', 'admin@example.com', 'Admin@2026!', is_staff=True
        )
        self.year = AcademicYear.objects.create(year='2026-27', is_active=True)
        self.class_obj = Class.objects.create(class_name='Admission Test Grade')
        self.section = Section.objects.create(
            academic_year=self.year, class_fk=self.class_obj, section_name='A', capacity=30
        )
        self.plan = FeePlan.objects.create(
            name='Admission Test Plan', class_name=self.class_obj.class_name, session=self.year.year
        )
        self.head = FeeHead.objects.create(name='Tuition Test', frequency='monthly')
        FeePlanDetail.objects.create(fee_plan=self.plan, fee_head=self.head, amount=10000)

    def workflow(self):
        workflow = StudentAdmissionWorkflow.objects.create(
            created_by=self.admin, updated_by=self.admin,
            student_username='admission.test.student',
            student_password_hash=make_password('Student@2026!'),
            payload={
                'name': 'Areeba Hassan', 'date_of_birth': '2017-04-14',
                'gender': 'female', 'email': 'areeba.admission@example.com',
                'phone': '+923001234567', 'nationality': 'Pakistani',
                'address': 'House 12, Main Road', 'campus': 'Main Campus',
                'branch': 'Primary', 'ref_no': 'ADM-TEST-001',
                'admission_date': '2026-08-03', 'academic_year_id': str(self.year.pk),
                'class_id': str(self.class_obj.pk), 'section_id': str(self.section.pk),
                'roll_no': 'A-025', 'fee_plan_id': str(self.plan.pk),
                'voucher_month': 'August', 'voucher_issue_date': '2026-08-03',
                'voucher_due_date': '2026-08-18', 'transport_enabled': False,
            },
        )
        AdmissionGuardian.objects.create(
            workflow=workflow, full_name='Hassan Ahmed', relationship='Father',
            email='hassan.parent@example.com', phone='+923001234568', is_primary=True,
            portal_access=True, notifications_enabled=True, username='hassan.parent.test',
            password_hash=make_password('Parent@2026!'),
        )
        for kind in ('B_FORM', 'GUARDIAN_CNIC'):
            AdmissionDocument.objects.create(
                workflow=workflow, document_type=kind, is_required=True,
                uploaded_by=self.admin,
                file=SimpleUploadedFile(f'{kind.lower()}.pdf', b'%PDF-1.4 test'),
            )
        return workflow

    def test_submit_for_review_does_not_create_accounts_or_voucher(self):
        workflow = self.workflow()
        submit_for_review(workflow, self.admin)
        self.assertEqual(workflow.status, 'PENDING')
        self.assertFalse(Student.objects.filter(email='areeba.admission@example.com').exists())
        self.assertFalse(User.objects.filter(username='admission.test.student').exists())
        self.assertEqual(FeeVoucher.objects.count(), 0)

    def test_inline_fee_plan_creation_creates_details_and_returns_selection(self):
        self.admin.is_superuser = True
        self.admin.save(update_fields=['is_superuser'])
        self.client.force_login(self.admin)
        response = self.client.post(reverse('admission_create_fee_plan'), {
            'class_id': self.class_obj.pk,
            'academic_year_id': self.year.pk,
            'name': 'Inline Admission Plan',
            f'head_{self.head.pk}': '12500.00',
        })
        self.assertEqual(response.status_code, 200)
        plan = FeePlan.objects.get(name='Inline Admission Plan')
        self.assertEqual(plan.class_name, self.class_obj.class_name)
        self.assertEqual(plan.session, self.year.year)
        self.assertEqual(FeePlanDetail.objects.get(fee_plan=plan).amount, 12500)
        self.assertEqual(response.json()['plan']['id'], plan.pk)

    def test_approve_is_idempotent_and_creates_complete_enrollment(self):
        workflow = self.workflow()
        with self.captureOnCommitCallbacks(execute=True):
            student = approve_and_enroll(workflow, self.admin)
        workflow.refresh_from_db()
        self.assertEqual(workflow.status, 'APPROVED')
        self.assertTrue(student.user.check_password('Student@2026!'))
        self.assertEqual(student.parents.count(), 1)
        self.assertTrue(student.parents.get().user.check_password('Parent@2026!'))
        self.assertEqual(StudentGuardian.objects.filter(student=student, is_primary=True).count(), 1)
        self.assertEqual(FeeVoucher.objects.filter(canonical_student=student).count(), 1)
        same_student = approve_and_enroll(workflow, self.admin)
        self.assertEqual(same_student.pk, student.pk)
        self.assertEqual(FeeVoucher.objects.filter(canonical_student=student).count(), 1)

    def test_existing_parent_password_is_preserved(self):
        parent_user = User.objects.create_user('existing.parent.test', password='Original@2026!')
        parent = Parent.objects.create(user=parent_user, full_name='Existing Parent')
        workflow = self.workflow()
        guardian = workflow.guardians.get(is_primary=True)
        guardian.existing_parent = parent
        guardian.username = ''
        guardian.password_hash = ''
        guardian.save()
        original_hash = parent_user.password
        approve_and_enroll(workflow, self.admin)
        parent_user.refresh_from_db()
        self.assertEqual(parent_user.password, original_hash)

    def test_enrollment_profile_renders_student_class_and_login(self):
        workflow = self.workflow()
        student = approve_and_enroll(workflow, self.admin)
        self.client.force_login(self.admin)
        session = self.client.session
        session[f'admission_credentials_{workflow.pk}'] = {
            'student': {'username': student.user.username, 'password': 'Student@2026!'},
            'guardians': [],
        }
        session.save()
        response = self.client.get(f'/admin_panel/students/admissions/{workflow.pk}/enrollment/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, student.name)
        self.assertContains(response, self.class_obj.class_name)
        self.assertContains(response, 'Student@2026!')
