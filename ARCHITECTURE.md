# EduPilot Architecture

Generated: 2026-07-27

## System Shape

EduPilot is a Django monolith with role-specific portals sharing one PostgreSQL database, Django authentication, global templates, and shared UI assets. Domain logic is split between the admin, automation/accounts, teacher/student portals, exam services, and two AI subsystems.

```text
Browser
  -> sms/urls.py
      -> login (authentication and role selection)
      -> admin_panel (administration, academics, HR, operations)
      -> teacher_dashboard (teacher portal and LMS)
      -> student_profile (student portal)
      -> parent_dashboard (parent portal)
      -> exam_system (exam workflows)
      -> edupilot_core (accounts and automation)
      -> admin_ai / ai_tutor (AI workflows)
  -> PostgreSQL
```

## Portal Boundaries

- Admin: `admin_panel` templates/routes plus `admin_ai`, `exam_system`, and `/automation/` links.
- Teacher: `teacher_dashboard` with LMS context, assessment, attendance, lesson plan, exam, and appraisal workflows.
- Student: `student_profile` with academic records and `ai_tutor` access.
- Parent: `parent_dashboard`, reading child-linked academic and fee information.
- Automation: `edupilot_core`, exposing fee, voucher, notification, salary, payslip, log, settings, and generic CRUD screens.

## Shared Presentation

- Sidebar shell and role menus: `templates/shared/sidebar/`.
- Portal header: `templates/shared/header/portal_header.html`.
- Admin UI foundations: `admin_panel/static/admin_panel/css/`.
- Shared button system: `edupilot-buttons.css`.
- Shared graph system: `edupilot-charts.css` and `edupilot-charts.js`.
- Neutral surfaces: `edupilot-surfaces.css`.
- AI/Admin design: `ai-admin-design.css`.
- Never edit `staticfiles/`; it is collected output.

## Core Data Ownership

- Portal students: `student_profile.models.Student`; teacher, exam, AI, and dashboard code commonly imports this model.
- Portal teachers and attendance: `teacher_dashboard.models.Teacher` and `teacher_dashboard.models.Attendance`.
- Administration, academics, HR, appraisal, procurement, and fleet: `admin_panel.models`.
- Active automation/accounts routes: fee, voucher, ledger, salary, notification, and automation records in `edupilot_core.models`.
- Automation compatibility records map to canonical `student_profile.Student` and `teacher_dashboard.Teacher`; legacy foreign keys remain available for historical fallback.
- Exams and question/paper/result data: `exam_system.models`.
- AI conversations/reports/audit data: `admin_ai.models` and `ai_tutor.models`.

## Model and Template Compatibility Boundaries

The repository contains legacy/mirrored model and template families. Never choose a model only by class name; follow the imports used by the target route.

- `Student` exists in `student_profile.models`, `admin_panel.models`, and `edupilot_core.models`.
- `Teacher` exists in `teacher_dashboard.models`, `admin_panel.models`, and `edupilot_core.models`.
- Fee, voucher, salary, notification, and automation model families exist in both `admin_panel.models` and `edupilot_core.models`; `/automation/` uses `edupilot_core`.
- `admin_panel.models` contains two `KpiTemplate` class definitions, matching the current duplicate-model runtime warning.
- `edupilot_core/templates/teacher_dashboard/` and `edupilot_core/templates/student_profile/` contain compatibility copies; check template resolution before editing a portal screen.
- Empty top-level directories such as `assignments/`, `quizzes/`, and `lecture_notes/` are not installed Django apps; their active models/views live in portal apps.
- Dashboard and AI aggregation intentionally import canonical portal models with aliases such as `PortalStudent` and `PortalTeacher`.

## Important Workflows

### Authentication and Role Routing

1. `sms/urls.py` exposes role login endpoints.
2. `login.views` authenticates and redirects by role.
3. Portal decorators/context processors enforce or expose role permissions.

### Real-Time Communication

1. `/communication/` resolves role-aware contacts and conversations through `communication.permissions` and `communication.views`.
2. `CommunicationService` guarantees one direct thread per normalized user pair and persists messages, receipts, mentions, reactions, attachments, and notifications.
3. `/ws/communication/<conversation_id>/` uses Django Channels for live messages, typing, presence, inbox changes, and receipt updates; HTTP polling remains the fallback.
4. Redis backs production channel delivery when `REDIS_URL` is configured; local development uses the in-memory channel layer.

### Fee Generation and Notification

1. Admin or scheduler enters `edupilot_core.views`.
2. Canonical portal students resolve to automation compatibility records through `edupilot_core.canonical_sync`.
3. Fee generation logic in `edupilot_core.services` creates/updates voucher and ledger records with both canonical and legacy links.
4. Notification queue records are created for relevant recipients.
5. Automation jobs/logs record counts, status, and errors.
6. Dashboard and portal views prefer canonical records and retain legacy fallback.
7. Manual and scheduled fee, salary, and notification jobs start through `edupilot_core.automation_runner`; a persistent `AutomationProgressRun` and per-record `AutomationProgressEvent` provide live polling updates without changing the original job history.
8. A new `FeeVoucher` is distributed by `edupilot_core.voucher_delivery` to the canonical student account, linked parent accounts, and the assigned class teacher account.
9. `VoucherDelivery` and `PortalNotification` persist recipient-specific delivery, read, view, download, popup-dismissal, and last-viewed state.
10. Student, Parent, and Teacher voucher routes use `edupilot_core.voucher_portal`; `/ws/vouchers/` pushes new-voucher events and the portal JavaScript retains polling fallback.
                
### Salary and Payslip

1. Salary automation is triggered through `edupilot_core.views`.
2. Service logic calculates salary records and persists vouchers/payslips.
3. Notifications and automation logs capture delivery and execution state.

### Timetable Absence and Fixture Assignment

1. Absence/timetable data is stored through admin and automation views.
2. Fixture services locate available replacement teachers.
3. Fixture and notification records are created.
4. Teacher/admin dashboards display assignment and exception state.

### Admin Dashboard

1. `admin_panel.views` aggregates canonical models across student, teacher, accounts, exam, HR, procurement, and fleet domains.
2. JSON summary endpoints provide filtered live data.
3. `admin_panel/templates/admin_panel/index.html` renders modules and actions.
4. Shared chart JavaScript refreshes visible data without duplicating chart instances.

### Admin AI Analytics and Copilot

1. `admin_ai.views` receives filters, questions, and report actions.
2. `planner.py`, `tools.py`, `services.py`, `memory.py`, and `agent.py` resolve safe tool plans against live ERP data.
3. `llm.py` provides model integration with deterministic/tool-based fallback behavior.
4. Conversations, messages, reports, and audit records persist in `admin_ai.models`.
5. AI analytics screens reuse admin data endpoints and shared graph/UI layers.

### Student AI Tutor

1. `ai_tutor.views` receives student questions.
2. `safety.py` validates scope and input.
3. `rag.py` retrieves indexed school knowledge.
4. `services.py`, `prompts.py`, and `llm.py` build the answer.
5. Conversation and usage records persist in `ai_tutor.models`.

### Exam and Result Processing

1. `exam_system.views` manages exam definitions, questions, papers, marking, and analytics.
2. `exam_system.services` contains paper/result domain operations.
3. Teacher-facing exam actions may enter through `teacher_dashboard.exam_views`.
4. Student and parent portals consume published result records.

## Dependency Direction

- `admin_ai` imports or depends on `admin_panel`.
- `admin_ai` imports or depends on `student_profile`.
- `admin_ai` imports or depends on `teacher_dashboard`.
- `admin_panel` imports or depends on `parent_dashboard`.
- `admin_panel` imports or depends on `student_profile`.
- `admin_panel` imports or depends on `teacher_dashboard`.
- `ai_tutor` imports or depends on `admin_panel`.
- `ai_tutor` imports or depends on `student_profile`.
- `ai_tutor` imports or depends on `teacher_dashboard`.
- `exam_system` imports or depends on `admin_panel`.
- `exam_system` imports or depends on `student_profile`.
- `exam_system` imports or depends on `teacher_dashboard`.
- `parent_dashboard` imports or depends on `admin_panel`.
- `parent_dashboard` imports or depends on `teacher_dashboard`.
- `student_profile` imports or depends on `admin_panel`.
- `student_profile` imports or depends on `teacher_dashboard`.
- `teacher_dashboard` imports or depends on `admin_panel`.
- `teacher_dashboard` imports or depends on `exam_system`.
- `teacher_dashboard` imports or depends on `student_profile`.

## Change Safety

- UI-only changes belong in templates/static assets; preserve every URL, form field, POST action, CSRF token, and data hook.
- Service or model changes require checking all importing apps in `PROJECT_MAP.json`.
- Cross-app dashboard metrics must continue using canonical model owners listed above.
- Scheduler, notification, payment, and report changes need idempotency and duplicate-record checks.
- Migrations are schema history: add new migrations; do not rewrite old applied migrations.
- The current settings file contains development-oriented configuration. Secrets and database credentials should be environment variables before production deployment.

## Map Refresh Procedure

Regenerate or update the three map files after:

- adding/removing an app;
- adding/removing models or service modules;
- changing root mounts or named routes;
- moving templates/shared UI ownership;
- changing canonical data ownership or a major workflow.

For ordinary localized fixes, update only the affected map section.
