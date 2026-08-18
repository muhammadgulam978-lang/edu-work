from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from admin_ai.models import AdminAIConversation, AdminAIMessage
from edupilot_core.models import AutomationJob, FeeVoucher, NotificationQueue, Student as FinanceStudent
from student_profile.models import Student
from teacher_dashboard.models import Attendance, Teacher

from .models import AcademicYear, Class, Section
from .views import build_ai_analytics_data


class LiveAIOverviewTests(TestCase):
    def setUp(self):
        self.admin = User(
            username="ai-overview-admin",
            email="ai-overview@example.com",
            password=make_password("test-pass"),
            is_staff=True,
            is_superuser=True,
            is_active=True,
        )
        User.objects.bulk_create([self.admin])
        self.admin.refresh_from_db()
        self.client = Client(HTTP_HOST="127.0.0.1")
        self.client.force_login(self.admin)

    def _create_live_records(self):
        academic_year = AcademicYear.objects.create(year="2026-2027", is_active=True)
        school_class = Class.objects.create(class_name="AI Test Class")
        section = Section.objects.create(
            academic_year=academic_year,
            class_fk=school_class,
            section_name="A",
            capacity=30,
        )
        present_student = Student.objects.create(
            academic_year=academic_year,
            student_id="AI-LIVE-001",
            name="Present Student",
            father_name="Father",
            mother_name="Mother",
            class_fk=school_class,
            section=section,
            roll_no="1",
            date_of_birth=date(2012, 1, 1),
            email="ai-present@example.com",
        )
        absent_student = Student.objects.create(
            academic_year=academic_year,
            student_id="AI-LIVE-002",
            name="Absent Student",
            father_name="Father",
            mother_name="Mother",
            class_fk=school_class,
            section=section,
            roll_no="2",
            date_of_birth=date(2012, 2, 1),
            email="ai-absent@example.com",
        )
        Teacher.objects.create(
            name="AI Live Teacher",
            email="ai-teacher@example.com",
            gender="Male",
            faculty_group="Junior Section",
            status="active",
        )
        today = timezone.localdate()
        Attendance.objects.create(student=present_student, date=today, status="present", class_fk=school_class, section=section)
        Attendance.objects.create(student=absent_student, date=today, status="absent", class_fk=school_class, section=section)

        finance_student = FinanceStudent.objects.create(
            full_name="AI Finance Student",
            admission_number="AI-FIN-001",
            current_class="AI Test Class",
        )
        FeeVoucher.objects.bulk_create([FeeVoucher(
            voucher_no="AI-V-001",
            student=finance_student,
            month="July",
            year=2026,
            issue_date=today,
            due_date=today,
            gross_amount=Decimal("1000"),
            net_amount=Decimal("1000"),
            status="UNPAID",
        )])
        NotificationQueue.objects.create(
            student=finance_student,
            notification_type="EMAIL",
            content="Test failure",
            status="FAILED",
        )
        AutomationJob.objects.create(job_type="fee", status="FAILED")
        return school_class, section

    def test_live_payload_contains_every_reference_and_legacy_group(self):
        school_class, section = self._create_live_records()
        today = timezone.localdate().isoformat()
        payload = build_ai_analytics_data({
            "period": "custom",
            "start_date": timezone.localdate(),
            "end_date": timezone.localdate(),
            "class_id": school_class.pk,
            "section_id": section.pk,
        })

        self.assertEqual(len(payload["kpis"]), 4)
        self.assertEqual(len(payload["snapshot"]), 6)
        self.assertEqual(len(payload["modules"]), 6)
        self.assertEqual(len(payload["trends"]), 6)
        self.assertEqual(len(payload["charts"]), 6)
        self.assertEqual(len(payload["risk"]["breakdown"]), 5)
        self.assertEqual(len(payload["system_health"]["items"]), 3)
        self.assertEqual(payload["meta"]["start_date"], today)
        self.assertEqual(payload["meta"]["class_id"], school_class.pk)

        kpis = {item["key"]: item for item in payload["kpis"]}
        self.assertEqual(kpis["students"]["value"], 2)
        self.assertEqual(kpis["attendance"]["value"], "50.0%")
        self.assertEqual(kpis["fees"]["value"], "0.0%")
        self.assertEqual(payload["risk"]["score"], 14)
        self.assertEqual(payload["system_health"]["issue_count"], 2)
        self.assertEqual(payload["system_health"]["status"], "Needs Attention")
        self.assertEqual(payload["charts"]["attendance"]["present"], [1])
        self.assertEqual(payload["charts"]["attendance"]["absent"], [1])

    def test_endpoint_validates_ranges_and_preserves_structured_contract(self):
        response = self.client.get(reverse("ai_analytics_data"), {
            "period": "custom", "start_date": "2026-07-01", "end_date": "2026-07-20",
        })
        self.assertEqual(response.status_code, 200)
        for key in ("meta", "kpis", "snapshot", "risk", "system_health", "modules", "alerts", "trends", "charts", "quick_actions"):
            self.assertIn(key, response.json())

        missing = self.client.get(reverse("ai_analytics_data"), {"period": "custom"})
        reversed_range = self.client.get(reverse("ai_analytics_data"), {
            "period": "custom", "start_date": "2026-07-20", "end_date": "2026-07-01",
        })
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(reversed_range.status_code, 400)

        anonymous = Client(HTTP_HOST="127.0.0.1").get(reverse("ai_analytics_data"))
        self.assertEqual(anonymous.status_code, 302)

    def test_standard_periods_and_empty_database_return_honest_states(self):
        for period in ("today", "week", "this_month"):
            with self.subTest(period=period):
                response = self.client.get(reverse("ai_analytics_data"), {"period": period})
                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertEqual(payload["meta"]["period"], period)
                self.assertLessEqual(payload["meta"]["start_date"], payload["meta"]["end_date"])

        payload = self.client.get(reverse("ai_analytics_data"), {"period": "today"}).json()
        kpis = {item["key"]: item for item in payload["kpis"]}
        self.assertEqual(kpis["students"]["value"], 0)
        self.assertEqual(kpis["attendance"]["value"], "0%")
        self.assertEqual(payload["risk"]["score"], 0)
        self.assertEqual(payload["system_health"]["status"], "Healthy")
        self.assertEqual(payload["alerts"][0]["title"], "All clear")

    def test_overview_renders_all_six_graphs_and_anchor_sections(self):
        response = self.client.get(reverse("ai_analytics_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="ai-risk-index"')
        self.assertContains(response, 'id="system-health"')
        for canvas_id in (
            "aiAttendanceChart", "aiFeeChart", "aiAdmissionsChart",
            "aiAttendanceDonutChart", "aiWorkloadChart", "aiFixtureMixChart",
        ):
            self.assertContains(response, f'id="{canvas_id}"')
        self.assertContains(response, reverse("admin_ai_copilot_message"))

    def test_copilot_reuses_conversation_and_rejects_empty_questions(self):
        conversation = AdminAIConversation.objects.create(created_by=self.admin)
        empty = self.client.post(reverse("admin_ai_copilot_message"), {
            "conversation_id": conversation.pk,
            "message": "   ",
        })
        self.assertEqual(empty.status_code, 400)
        self.assertEqual(AdminAIMessage.objects.count(), 0)
        anonymous = Client(HTTP_HOST="127.0.0.1").post(reverse("admin_ai_copilot_message"), {"message": "Hello"})
        self.assertEqual(anonymous.status_code, 302)

        agent_result = {
            "answer": "Two students are available in live ERP records.",
            "intent": "student_count",
            "plan": {"intent": "student_count", "steps": []},
            "tools": [],
            "evidence": [{"label": "Students", "value": 2}],
            "actions": [{"label": "Open Student Search", "url": "/admin_panel/student-intelligence/", "kind": "link"}],
            "mode": "tool_agent_fallback",
            "model": "",
            "llm_error": "",
        }
        with patch("admin_ai.views.run_admin_agent", return_value=agent_result):
            response = self.client.post(reverse("admin_ai_copilot_message"), {
                "conversation_id": conversation.pk,
                "message": "How many students are there?",
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["reply"], agent_result["answer"])
        self.assertEqual(response.json()["actions"], agent_result["actions"])
        self.assertEqual(AdminAIMessage.objects.filter(conversation=conversation).count(), 2)
