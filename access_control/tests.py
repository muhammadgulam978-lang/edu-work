from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.utils import timezone

from .identity import effective_role
from .models import Institution, Campus, RoleDefinition, RoleGrant, RoleAssignment, RecordScope, AuditEvent
from .policy import permitted_assignment, scoped_queryset
from .workflows import create_request, transition, execute


class AccessPolicyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('maker', password='secret')
        self.reviewer = User.objects.create_user('reviewer', password='secret')
        self.owner = User.objects.create_user('owner', password='secret')
        self.school = Institution.objects.create(name='School A', code='a')
        self.other = Institution.objects.create(name='School B', code='b')
        self.campus = Campus.objects.create(institution=self.school, name='A', code='a')
        self.role = RoleDefinition.objects.create(institution=self.school, name='Finance')
        self.assignment = RoleAssignment.objects.create(user=self.user, role=self.role, campus=self.campus,
                                                        scope={'class': [1]}, approved_by=self.owner)
        self.record = RecordScope.objects.create(institution=self.school, campus=self.campus,
                                                  resource='finance.refund', object_id=1, dimensions={'class': [1]})
        for action in ('view', 'create', 'submit', 'approve', 'publish'):
            RoleGrant.objects.create(role=self.role, resource=self.record.resource, action=action)

    def test_action_and_scope_must_be_on_same_assignment(self):
        self.assertIsNotNone(permitted_assignment(self.user, 'approve', self.record))
        wide = RoleDefinition.objects.create(institution=self.school, name='Observer')
        RoleGrant.objects.create(role=wide, resource=self.record.resource, action='view')
        RoleAssignment.objects.create(user=self.user, role=wide, approved_by=self.owner)
        self.record.dimensions = {'class': [2]}
        self.record.save()
        self.assertIsNone(permitted_assignment(self.user, 'approve', self.record))
        self.assertIsNotNone(permitted_assignment(self.user, 'view', self.record))

    def test_cross_institution_and_unmapped_records_are_denied(self):
        self.record.institution, self.record.campus = self.other, None
        self.record.save()
        self.assertIsNone(permitted_assignment(self.user, 'view', self.record))
        self.assertFalse(scoped_queryset(self.user, 'view', User.objects.all(), self.school.pk).exists())

    def test_superuser_does_not_bypass_domain_scope(self):
        self.user.is_superuser = True
        self.user.save()
        self.assignment.active = False
        self.assignment.save()
        self.assertIsNone(permitted_assignment(self.user, 'approve', self.record))

    def test_expiry_mfa_and_explicit_deny(self):
        self.role.requires_mfa = True
        self.role.save()
        self.assertIsNone(permitted_assignment(self.user, 'view', self.record))
        self.assertIsNotNone(permitted_assignment(self.user, 'view', self.record, mfa_verified=True))
        self.assignment.starts_at = timezone.now() - timedelta(days=2)
        self.assignment.ends_at = timezone.now() - timedelta(days=1)
        self.assignment.save()
        self.assertIsNone(permitted_assignment(self.user, 'view', self.record, mfa_verified=True))

    def test_invalid_scope_and_self_access_approval_rejected(self):
        with self.assertRaises(ValidationError):
            RoleAssignment.objects.create(user=self.user, role=self.role, approved_by=self.user)
        with self.assertRaises(ValidationError):
            RoleAssignment.objects.create(user=self.user, role=self.role, scope={'class': ['*']})

    def test_approval_order_self_approval_and_exactly_once_execution(self):
        RoleAssignment.objects.create(user=self.reviewer, role=self.role, approved_by=self.owner)
        item = create_request(self.user, self.record, 'refund', self.reviewer, {'amount': '20.00'}, 'Overpayment')
        with self.assertRaises(ValidationError):
            transition(self.reviewer, item.pk, 'approve', 1, 'Reviewed')
        item = transition(self.user, item.pk, 'submit', 1)
        with self.assertRaises(PermissionDenied):
            transition(self.user, item.pk, 'approve', item.version, 'Own approval')
        with self.assertRaises(ValidationError):
            transition(self.reviewer, item.pk, 'approve', 1, 'Stale')
        item = transition(self.reviewer, item.pk, 'approve', item.version, 'Verified amount')
        calls = []
        execute(self.reviewer, item.pk, lambda item: calls.append(item.pk))
        execute(self.reviewer, item.pk, lambda item: calls.append(item.pk))
        self.assertEqual(calls, [item.pk])
        self.assertEqual(AuditEvent.objects.filter(action='workflow.execute').count(), 1)

    def test_changed_approved_payload_cannot_execute(self):
        RoleAssignment.objects.create(user=self.reviewer, role=self.role, approved_by=self.owner)
        item = create_request(self.user, self.record, 'refund', self.reviewer, {'amount': 20}, 'Reason')
        item = transition(self.user, item.pk, 'submit', 1)
        item = transition(self.reviewer, item.pk, 'approve', item.version, 'Verified')
        item.payload = {'amount': 2000}
        item.save()
        with self.assertRaises(ValidationError):
            execute(self.reviewer, item.pk, lambda item: None)


class IdentityTests(TestCase):
    def test_unassigned_user_cannot_read_exam_analytics(self):
        user = User.objects.create_user('no-exam-access')
        self.client.force_login(user)
        self.assertEqual(self.client.get('/exam/analytics/data/').status_code, 403)
    def test_staff_or_arbitrary_group_does_not_grant_admin_portal(self):
        from .identity import has_portal
        user = User.objects.create_user('staff-only', is_staff=True)
        user.groups.add(Group.objects.create(name='Finance Officer'))
        self.assertFalse(has_portal(user, 'admin'))

    def test_username_never_grants_a_role(self):
        user = User.objects.create_user('teacher-admin-student', password='secret')
        self.assertFalse(user.groups.exists())
        self.assertIsNone(effective_role(user))

    def test_superuser_label_is_consistent(self):
        user = User.objects.create_superuser('root', 'root@example.com', 'secret')
        self.assertEqual(effective_role(user), 'Super Admin')
        self.assertEqual(list(user.groups.values_list('name', flat=True)), ['Admin'])

    def test_multiple_roles_require_an_explicit_primary_role(self):
        user = User.objects.create_user('multi')
        user.groups.add(Group.objects.create(name='Teacher'), Group.objects.create(name='Parent'))
        with self.assertRaises(PermissionDenied):
            effective_role(user)

    def test_permission_change_invalidates_existing_session(self):
        user = User.objects.create_user('admin-user', password='secret')
        group = Group.objects.create(name='Admin')
        user.groups.add(group)
        self.client.force_login(user)
        self.client.get('/login/')
        user.groups.clear()
        self.assertEqual(self.client.get('/login/').status_code, 403)
        self.assertNotIn('_auth_user_id', self.client.session)


class GuardianTests(TestCase):
    def setUp(self):
        from parent_dashboard.models import Parent, StudentGuardian
        from student_profile.models import Student
        self.user = User.objects.create_user('guardian', password='secret')
        self.user.groups.add(Group.objects.create(name='Parent'))
        self.parent = Parent.objects.create(user=self.user, full_name='Guardian')
        self.student = Student.objects.create(student_id='A1', name='Child', date_of_birth=date(2015, 1, 1),
                                               email='child@example.com')
        self.parent.students.add(self.student)
        self.link = StudentGuardian.objects.create(parent=self.parent, student=self.student, relationship='Parent')

    def test_old_relation_does_not_bypass_verification_or_revocation(self):
        from parent_dashboard.access import accessible_students
        self.assertFalse(accessible_students(self.parent).exists())
        self.link.verified_at = timezone.now()
        self.link.save()
        self.assertEqual(list(accessible_students(self.parent)), [self.student])
        self.link.portal_access = False
        self.link.save()
        self.assertFalse(accessible_students(self.parent).exists())

    def test_expired_guardian_and_no_child_result_page(self):
        from parent_dashboard.access import accessible_students
        self.link.verified_at = timezone.now()
        self.link.expires_at = timezone.now() - timedelta(seconds=1)
        self.link.save()
        self.assertFalse(accessible_students(self.parent).exists())
        self.client.force_login(self.user)
        from django.urls import reverse
        response = self.client.get(reverse('parent_result'))
        self.assertEqual(response.status_code, 200)


class PaperWorkflowTests(TestCase):
    def setUp(self):
        from admin_panel.models import AcademicYear, Class, Subject
        from exam_system.models import ExamPlan, PaperBlueprint, GeneratedPaper, PaperApproval
        self.setter = User.objects.create_user('setter')
        self.reviewers = [User.objects.create_user(f'reviewer{i}') for i in range(3)]
        year = AcademicYear.objects.create(year='2026-2027')
        cls = Class.objects.create(class_name='Test Class')
        subject = Subject.objects.create(academic_year=year, class_fk=cls, name='Math', short_code='M', sort_order=1)
        plan = ExamPlan.objects.create(title='Final', academic_year=year, class_fk=cls,
                                        start_date=date(2026, 9, 1), end_date=date(2026, 9, 7))
        blueprint = PaperBlueprint.objects.create(exam_plan=plan, subject=subject)
        self.paper = GeneratedPaper.objects.create(blueprint=blueprint, generated_by=self.setter)
        from exam_system.models import QuestionBank, Question
        bank = QuestionBank.objects.create(subject=subject, class_fk=cls, academic_year=year)
        question = Question.objects.create(bank=bank, text='Reviewed question', human_approved=True)
        self.paper.questions.add(question)
        from exam_system.access import STAGES
        for stage, user in zip(STAGES, [self.setter] + self.reviewers):
            PaperApproval.objects.create(paper=self.paper, stage=stage, assigned_to=user)

    def test_order_and_controller_visibility(self):
        from exam_system.access import decide_paper, visible_papers
        controller = self.reviewers[-1]
        self.assertFalse(visible_papers(controller).exists())
        with self.assertRaises(ValidationError):
            decide_paper(self.reviewers[0], self.paper.pk, 'COORDINATOR', 'approve')
        from exam_system.access import STAGES
        for stage, user in zip(STAGES, [self.setter] + self.reviewers):
            decide_paper(user, self.paper.pk, stage, 'approve')
        self.paper.refresh_from_db()
        self.assertEqual(self.paper.status, 'LOCKED')
        with self.assertRaises(ValidationError):
            decide_paper(controller, self.paper.pk, 'CONTROLLER', 'approve')

    def test_superuser_cannot_read_unassigned_paper(self):
        from exam_system.access import visible_papers
        admin = User.objects.create_superuser('super', 'super@example.com', 'secret')
        self.assertFalse(visible_papers(admin).exists())

    def test_ai_questions_need_human_review(self):
        from exam_system.models import QuestionBank, Question
        from exam_system.access import decide_paper
        plan = self.paper.blueprint.exam_plan
        bank = QuestionBank.objects.get(subject=self.paper.blueprint.subject, class_fk=plan.class_fk,
                                       academic_year=plan.academic_year)
        question = Question.objects.create(bank=bank, text='AI question', ai_generated=True)
        self.paper.questions.add(question)
        with self.assertRaises(ValidationError):
            decide_paper(self.setter, self.paper.pk, 'TEACHER', 'approve')

    def test_question_changes_invalidate_reviews_and_locked_content_is_immutable(self):
        from exam_system.access import decide_paper, STAGES
        decide_paper(self.setter, self.paper.pk, 'TEACHER', 'approve')
        question = self.paper.questions.first()
        question.text = 'Changed question'
        question.save()
        self.assertEqual(self.paper.approvals.get(stage='TEACHER').status, 'PENDING')
        question.refresh_from_db()
        self.assertFalse(question.human_approved)
        question.human_approved, question.approved_by = True, self.setter
        question.save()
        for stage, user in zip(STAGES, [self.setter] + self.reviewers):
            decide_paper(user, self.paper.pk, stage, 'approve')
        question.text = 'Tampered locked question'
        with self.assertRaises(ValidationError):
            question.save()
        with self.assertRaises(ValidationError):
            self.paper.questions.clear()


class PaymentTests(TestCase):
    def setUp(self):
        from edupilot_core.models import Student, FeeVoucher, StudentBalance
        self.maker = User.objects.create_user('finance')
        self.approver = User.objects.create_user('access-owner')
        institution = Institution.objects.create(name='School', code='school')
        role = RoleDefinition.objects.create(institution=institution, name='Finance')
        RoleGrant.objects.create(role=role, resource='edupilot_core.feevoucher', action='edit')
        RoleAssignment.objects.create(user=self.maker, role=role, approved_by=self.approver)
        student = Student.objects.create(full_name='Payment Student', admission_number='PAY-1', current_class='1')
        # Fixtures deliberately bypass external-delivery signals.
        self.voucher = FeeVoucher(voucher_no='PAY-V1', student=student, month='September', year=2026,
                                   issue_date=date(2026, 9, 1), due_date=date(2026, 9, 30), gross_amount=100, net_amount=100)
        FeeVoucher.objects.bulk_create([self.voucher])
        StudentBalance.objects.update_or_create(student=student, defaults={'outstanding_amount': 100})
        RecordScope.objects.create(institution=institution, resource='edupilot_core.feevoucher', object_id=self.voucher.pk)

    def test_partial_payments_accumulate_and_retries_do_not_double_post(self):
        from .payments import record_payment
        from edupilot_core.models import StudentBalance, StudentLedger
        first = record_payment(self.maker, self.voucher.pk, '40.00', 'BANK-1')
        repeat = record_payment(self.maker, self.voucher.pk, '40.00', 'BANK-1')
        self.assertEqual(first.pk, repeat.pk)
        self.voucher.refresh_from_db()
        self.assertEqual(self.voucher.status, 'PARTIAL')
        record_payment(self.maker, self.voucher.pk, '60.00', 'BANK-2')
        self.voucher.refresh_from_db()
        self.assertEqual(self.voucher.status, 'PAID')
        self.assertEqual(StudentBalance.objects.get(student=self.voucher.student).outstanding_amount, Decimal('0'))
        self.assertEqual(StudentLedger.objects.filter(student=self.voucher.student, credit__gt=0).count(), 2)

    def test_overpayment_replay_mismatch_and_nonfinite_values_do_not_mutate(self):
        from .payments import record_payment
        from .models import PaymentReceipt
        for amount in ('101.00', 'NaN', 'Infinity', '-1', '0.001'):
            with self.assertRaises(ValidationError):
                record_payment(self.maker, self.voucher.pk, amount, 'BAD')
        self.assertFalse(PaymentReceipt.objects.exists())
        record_payment(self.maker, self.voucher.pk, '10', 'ONCE')
        with self.assertRaises(ValidationError):
            record_payment(self.maker, self.voucher.pk, '20', 'ONCE')

    def test_unassigned_user_cannot_post_even_as_superuser(self):
        from .payments import record_payment
        admin = User.objects.create_superuser('finance-root', 'root@example.com', 'secret')
        with self.assertRaises(PermissionDenied):
            record_payment(admin, self.voucher.pk, '10', 'UNAUTHORIZED')


class AcademicAndProcurementTests(TestCase):
    def test_archiving_year_preserves_sections_and_students(self):
        from admin_panel.models import AcademicYear, Class, Section
        year = AcademicYear.objects.create(year='2026-2027', is_active=True, status='active')
        section = Section.objects.create(academic_year=year, class_fk=Class.objects.create(class_name='Archive'),
                                           section_name='A', capacity=20)
        year.delete()
        year.refresh_from_db()
        self.assertEqual(year.status, 'archived')
        self.assertFalse(year.is_active)
        self.assertTrue(Section.objects.filter(pk=section.pk).exists())

    def test_purchase_maker_cannot_approve_and_approved_amount_is_locked(self):
        from admin_panel.models import PurchaseRequest
        from admin_panel.procurement_services import save_purchase_request
        maker = User.objects.create_superuser('buyer', 'buyer@example.com', 'secret')
        checker = User.objects.create_superuser('checker', 'checker@example.com', 'secret')
        obj = save_purchase_request(PurchaseRequest(title='Books', estimated_cost=100), maker)
        obj.status = 'approved'
        with self.assertRaises(PermissionDenied):
            save_purchase_request(obj, maker)
        obj.refresh_from_db()
        obj.status = 'approved'
        save_purchase_request(obj, checker)
        self.assertEqual(obj.approved_by_id, checker.pk)
        obj.estimated_cost = 1000
        with self.assertRaises(ValidationError):
            save_purchase_request(obj, checker)

    def test_new_purchase_cannot_skip_to_received(self):
        from admin_panel.models import PurchaseRequest
        from admin_panel.procurement_services import save_purchase_request
        maker = User.objects.create_user('skip-buyer')
        with self.assertRaises(ValidationError):
            save_purchase_request(PurchaseRequest(title='Bypass', status='received'), maker)
