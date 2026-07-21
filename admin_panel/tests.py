from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from edupilot_core.models import FeeVoucher, Student as FinanceStudent, StudentLedger
from student_profile.models import Student as PortalStudent
from teacher_dashboard.models import Attendance, Teacher as PortalTeacher

from .models import PurchaseRequest, TransportRoute, TransportTrip, Vehicle, VehicleMaintenance
from .views import build_reference_dashboard_data


class LiveReferenceDashboardTests(TestCase):
    def setUp(self):
        # bulk_create avoids the project's console-printing user signal, whose
        # Unicode output is not supported by the Windows test runner encoding.
        self.admin = User(
            username="dashboard-admin", email="admin@example.com",
            password=make_password("test-pass"), is_staff=True,
            is_superuser=True, is_active=True,
        )
        User.objects.bulk_create([self.admin])
        self.admin.refresh_from_db()
        self.client = Client(HTTP_HOST="127.0.0.1")
        self.client.force_login(self.admin)

    def test_dashboard_uses_canonical_portal_and_finance_models(self):
        student = PortalStudent.objects.create(
            student_id="LIVE-001", name="Live Student", father_name="Father",
            mother_name="Mother", roll_no="1", date_of_birth=date(2012, 1, 1),
            email="live-student@example.com",
        )
        PortalTeacher.objects.create(
            name="Live Teacher", email="live-teacher@example.com", gender="Male",
            faculty_group="Junior Section", status="active",
        )
        Attendance.objects.create(student=student, date=timezone.localdate(), status="present")

        finance_student = FinanceStudent.objects.create(
            full_name="Finance Student", admission_number="FIN-001", current_class="1"
        )
        FeeVoucher.objects.bulk_create([FeeVoucher(
            voucher_no="LIVE-V-001", student=finance_student, month="July", year=2026,
            issue_date=timezone.localdate(), due_date=timezone.localdate(),
            gross_amount=Decimal("100"), net_amount=Decimal("100"), status="PARTIAL",
        )])
        StudentLedger.objects.create(
            student=finance_student, description="Payment received", credit=Decimal("50"),
            balance=Decimal("50"), reference_no="LIVE-TXN-001",
        )

        payload = build_reference_dashboard_data(period="today")
        kpis = {item["key"]: item for item in payload["kpis"]}
        self.assertEqual(kpis["students"]["value"], 1)
        self.assertEqual(kpis["teachers"]["value"], 1)
        self.assertEqual(kpis["attendance"]["value"], 100.0)
        self.assertEqual(kpis["fees"]["value"], 50.0)

    def test_dashboard_endpoint_supports_custom_range_and_structured_modules(self):
        response = self.client.get(reverse("dashboard_summary_data"), {
            "period": "custom", "start_date": "2026-07-01", "end_date": "2026-07-20",
        })
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["meta"]["start_date"], "2026-07-01")
        self.assertEqual(payload["meta"]["end_date"], "2026-07-20")
        for key in ("kpis", "academics", "hr", "finance", "procurement", "fleet", "alerts"):
            self.assertIn(key, payload)

    def test_transport_trip_crud_uses_normal_admin_post_flow(self):
        route = TransportRoute.objects.create(route_name="Test Route", amount=Decimal("2000"))
        vehicle = Vehicle.objects.create(vehicle_no="TEST-BUS-1", vehicle_type="bus", capacity=30)
        create_response = self.client.post(reverse("operation_transport_trip_create"), {
            "route": route.pk, "vehicle": vehicle.pk, "service_date": "2026-07-20",
            "scheduled_departure": "07:30", "actual_departure": "07:40",
            "students_transported": 24, "status": "delayed", "notes": "Traffic",
        })
        self.assertEqual(create_response.status_code, 302)
        trip = TransportTrip.objects.get(route=route, vehicle=vehicle)

        edit_response = self.client.post(reverse("operation_transport_trip_edit", args=[trip.pk]), {
            "route": route.pk, "vehicle": vehicle.pk, "service_date": "2026-07-20",
            "scheduled_departure": "07:30", "actual_departure": "07:30",
            "students_transported": 25, "status": "on_time", "notes": "",
        })
        self.assertEqual(edit_response.status_code, 302)
        trip.refresh_from_db()
        self.assertEqual(trip.status, "on_time")
        self.assertEqual(trip.students_transported, 25)

        delete_response = self.client.post(reverse("operation_transport_trip_delete", args=[trip.pk]))
        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(TransportTrip.objects.filter(pk=trip.pk).exists())

    def test_empty_dashboard_returns_real_zero_states(self):
        payload = build_reference_dashboard_data(period="today")
        kpis = {item["key"]: item for item in payload["kpis"]}
        self.assertEqual(kpis["students"]["value"], 0)
        self.assertEqual(kpis["vehicles"]["value"], 0)
        self.assertEqual(payload["fleet"]["routes"], [])

    def test_reference_graphs_use_live_finance_procurement_and_fleet_data(self):
        today = timezone.localdate()
        PurchaseRequest.objects.create(
            title="On-time books", needed_by=today,
            received_on=today, estimated_cost=Decimal("1200"), status="received",
        )
        PurchaseRequest.objects.create(
            title="Late supplies", needed_by=today - timedelta(days=1),
            received_on=today, estimated_cost=Decimal("800"), status="received",
        )
        route = TransportRoute.objects.create(route_name="Live Route", amount=Decimal("1500"))
        vehicle = Vehicle.objects.create(vehicle_no="GRAPH-BUS-1", capacity=40, status="maintenance")
        TransportTrip.objects.create(
            route=route, vehicle=vehicle, service_date=today,
            scheduled_departure=time(7, 30), actual_departure=time(7, 35),
            students_transported=32, status="delayed",
        )
        VehicleMaintenance.objects.create(
            vehicle=vehicle, maintenance_type="Service", service_date=today, status="scheduled",
        )

        payload = build_reference_dashboard_data(period="today")
        self.assertEqual(payload["procurement"]["summary"]["on_time"], 1)
        self.assertEqual(payload["procurement"]["summary"]["delayed"], 1)
        self.assertEqual(payload["procurement"]["chart"]["spend"], [2000.0])
        self.assertEqual(payload["fleet"]["metrics"][2]["value"], 32)
        self.assertEqual(payload["fleet"]["metrics"][3]["value"], 1)
        self.assertEqual(payload["fleet"]["routes"][0]["status"], "Delayed")

    def test_dashboard_renders_all_reference_graph_surfaces(self):
        response = self.client.get(reverse("admin_panel_dashboard"))
        self.assertContains(response, 'id="academicsChart"')
        self.assertContains(response, 'id="hrChart"')
        self.assertContains(response, 'id="financeChart"')
        self.assertContains(response, 'id="procurementChart"')
        self.assertContains(response, "data-fleet-summary", html=False)
