import tempfile
from datetime import date

from django.test import TestCase, override_settings

from student_profile.models import Student as PortalStudent
from teacher_dashboard.models import Teacher as PortalTeacher

from .canonical_sync import ensure_legacy_student, ensure_legacy_teacher
from .models import (
    CanonicalMappingAudit,
    FeeHead,
    FeePlan,
    FeePlanDetail,
    FeeVoucher,
    NotificationQueue,
    SalaryStructure,
    SalaryVoucher,
    Student,
    StudentFeeAssignment,
    StudentLedger,
    Teacher,
    get_dashboard_stats,
)
from .services import FeeGenerationService, SalaryAutomationService


class CanonicalSyncTests(TestCase):
    def create_student(self, student_id='ST-001', name='Canonical Student'):
        return PortalStudent.objects.create(
            student_id=student_id,
            name=name,
            father_name='Father',
            mother_name='Mother',
            roll_no=student_id,
            gender='Male',
            date_of_birth=date(2012, 1, 1),
            email=f'{student_id.lower()}@example.com',
        )

    def create_teacher(self, email='teacher@example.com', name='Canonical Teacher'):
        return PortalTeacher.objects.create(
            name=name,
            email=email,
            gender='Male',
            faculty_group='Junior Section',
            status='active',
        )

    def test_portal_records_create_one_legacy_mapping(self):
        student = self.create_student()
        teacher = self.create_teacher()

        legacy_student = ensure_legacy_student(student)
        legacy_teacher = ensure_legacy_teacher(teacher)

        self.assertEqual(Student.objects.filter(canonical_student=student).count(), 1)
        self.assertEqual(Teacher.objects.filter(canonical_teacher=teacher).count(), 1)
        self.assertEqual(legacy_student.full_name, student.name)
        self.assertEqual(legacy_teacher.name, teacher.name)
        self.assertEqual(
            CanonicalMappingAudit.objects.filter(status='MATCHED').count(),
            2,
        )

    def test_existing_legacy_student_is_reused_by_identifier(self):
        legacy = Student.objects.create(
            full_name='Existing Student',
            admission_number='ST-002',
            student_id='ST-002',
            current_class='Grade 1',
        )

        student = self.create_student('ST-002', 'Existing Student')

        legacy.refresh_from_db()
        self.assertEqual(legacy.canonical_student, student)
        self.assertEqual(Student.objects.filter(canonical_student=student).count(), 1)

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_fee_generation_writes_canonical_relations(self):
        student = self.create_student('ST-003')
        legacy = ensure_legacy_student(student)
        plan = FeePlan.objects.create(name='Monthly', class_name='Grade 1', session='2026')
        head = FeeHead.objects.create(name='Tuition', frequency='monthly')
        FeePlanDetail.objects.create(fee_plan=plan, fee_head=head, amount=1000)
        assignment = StudentFeeAssignment.objects.create(student=legacy, fee_plan=plan)

        generated = FeeGenerationService.generate_monthly_fees('July', 2026)

        assignment.refresh_from_db()
        voucher = FeeVoucher.objects.get(canonical_student=student)
        self.assertEqual(generated, 1)
        self.assertEqual(assignment.canonical_student, student)
        self.assertEqual(voucher.student, legacy)
        self.assertTrue(StudentLedger.objects.filter(canonical_student=student).exists())
        self.assertTrue(NotificationQueue.objects.filter(canonical_student=student).exists())

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_salary_generation_writes_canonical_teacher(self):
        teacher = self.create_teacher('salary@example.com')
        legacy = ensure_legacy_teacher(teacher)
        legacy.basic_salary = 50000
        legacy.save(update_fields=['basic_salary'])
        structure = SalaryStructure.objects.create(teacher=legacy, deductions=5000)

        SalaryAutomationService.generate_salaries('July', 2026)

        structure.refresh_from_db()
        voucher = SalaryVoucher.objects.get(canonical_teacher=teacher)
        self.assertEqual(structure.canonical_teacher, teacher)
        self.assertEqual(voucher.teacher, legacy)
        self.assertEqual(voucher.net_salary, 45000)

    def test_dashboard_stats_use_canonical_counts(self):
        self.create_student('ST-004')
        self.create_teacher('stats@example.com')
        Student.objects.create(
            full_name='Legacy Only',
            admission_number='LEGACY-ONLY',
            current_class='Old',
        )
        Teacher.objects.create(name='Legacy Only', teacher_id='LEGACY-ONLY')

        stats = get_dashboard_stats()

        self.assertEqual(stats['total_students'], 1)
        self.assertEqual(stats['total_teachers'], 1)
