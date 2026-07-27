from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from admin_panel.models import PurchaseRequest, TransportRoute, TransportTrip, Vehicle


class UnifiedLiveChartTests(TestCase):
    def setUp(self):
        self.admin = User(
            username="chart-admin",
            password=make_password("test-pass"),
            is_staff=True,
            is_superuser=True,
            is_active=True,
        )
        User.objects.bulk_create([self.admin])
        self.admin.refresh_from_db()
        self.client = Client(HTTP_HOST="127.0.0.1")
        self.client.force_login(self.admin)

    def test_operations_procurement_endpoint_returns_live_period_series(self):
        today = timezone.localdate()
        PurchaseRequest.objects.create(
            title="Live chart request",
            estimated_cost=Decimal("2500"),
            status="approved",
        )
        response = self.client.get(
            reverse("operation_summary_data", args=["procurement"]),
            {"period": "today"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["meta"]["start_date"], today.isoformat())
        self.assertEqual(payload["chart"]["spend"], [2500.0])
        self.assertEqual(payload["metrics"][0]["value"], 1)

    def test_operations_fleet_endpoint_uses_real_trip_performance(self):
        today = timezone.localdate()
        route = TransportRoute.objects.create(route_name="Chart Route", amount=Decimal("1000"))
        vehicle = Vehicle.objects.create(vehicle_no="CHART-BUS", capacity=30, status="active")
        TransportTrip.objects.create(
            route=route,
            vehicle=vehicle,
            service_date=today,
            scheduled_departure="07:30",
            actual_departure="07:35",
            students_transported=25,
            status="delayed",
        )
        response = self.client.get(
            reverse("operation_summary_data", args=["fleet"]),
            {"period": "today"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["routes"][0]["name"], "Chart Route")
        self.assertEqual(payload["routes"][0]["status"], "Delayed")
        self.assertEqual(payload["metrics"][2]["value"], 25)

    def test_live_endpoints_reject_invalid_custom_ranges(self):
        invalid = {"period": "custom", "start_date": "2026-07-20", "end_date": "2026-07-01"}
        self.assertEqual(self.client.get(reverse("dashboard_summary_data"), invalid).status_code, 400)
        self.assertEqual(
            self.client.get(reverse("operation_summary_data", args=["procurement"]), invalid).status_code,
            400,
        )
        self.assertEqual(self.client.get(reverse("automation-graph-data"), invalid).status_code, 400)

        too_long = {
            "period": "custom",
            "start_date": (timezone.localdate() - timedelta(days=367)).isoformat(),
            "end_date": timezone.localdate().isoformat(),
        }
        self.assertEqual(self.client.get(reverse("dashboard_summary_data"), too_long).status_code, 400)

    def test_graph_pages_load_shared_assets_and_preserve_surfaces(self):
        dashboard = self.client.get(reverse("admin_panel_dashboard"))
        self.assertContains(dashboard, "edupilot-charts.js")
        self.assertContains(dashboard, 'id="academicsChart"')

        ai = self.client.get(reverse("ai_analytics_dashboard"))
        self.assertContains(ai, "edupilot-charts.js")
        self.assertContains(ai, 'id="aiFixtureMixChart"')

        procurement = self.client.get(reverse("operation_procurement_dashboard"))
        self.assertContains(procurement, "operations-dashboard.js")
        self.assertContains(procurement, 'id="operationsChart"')

        fleet = self.client.get(reverse("operation_transportation_dashboard"))
        self.assertContains(fleet, "data-ops-routes", html=False)

    def test_graph_json_endpoints_require_authentication(self):
        anonymous = Client(HTTP_HOST="127.0.0.1")
        for url in (
            reverse("dashboard_summary_data"),
            reverse("operation_summary_data", args=["procurement"]),
            reverse("analytics_data"),
            reverse("automation-graph-data"),
        ):
            self.assertIn(anonymous.get(url).status_code, (302, 403))
