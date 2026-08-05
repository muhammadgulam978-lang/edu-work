# EduPilot Project Map

Generated: 2026-07-27

This is the fast lookup index for future work. Start here, then inspect only the files listed for the requested feature. Update the affected section whenever structure, routes, models, or workflows change.

## Recent Feature Map

- Real-time Communication: `communication/models.py`, `communication/services.py`, `communication/views.py`, `communication/consumers.py`, and `communication/routing.py`.
- Communication UI: `/communication/` uses `communication/templates/communication/inbox.html` with its dedicated CSS/JS; Admin, Teacher, Student, and Parent portals share this screen with role-aware contact permissions.
- Direct conversations use a unique normalized `direct_key`; receipts progress `SENT -> DELIVERED -> READ`; WebSocket route is `/ws/communication/<conversation_id>/` with polling fallback.
- Announcements: `edupilot_core/models.py` (`Announcement`, `AnnouncementRead`, `AnnouncementNotification`), `edupilot_core/services.py` (`AnnouncementService`), `admin_panel/views.py` (`announcement_center`), `admin_panel/templates/admin_panel/announcement_center.html`, and `admin_panel/static/admin_panel/{css/announcement-center.css,js/announcement-center.js}`.
- Admin route: `/admin_panel/announcements/` name=`announcement_center`; creation is CSRF-protected and targets live users by audience/class.
- Recipient feeds share `templates/shared/announcements/feed_content.html` and `edupilot_core/announcement_views.py`.
- Feed routes: `/teacher_dashboard/announcements/`, `/student/announcements/`, `/parent/announcements/`, and staff-only `/automation/announcements/`.
- Automation live progress: `edupilot_core/automation_runner.py` starts bounded background fee, salary, and notification runs; `edupilot_core/progress.py` persists run/event state; `edupilot_core/services.py` records per-recipient progress; `/automation/progress/<run_id>/` polls snapshots; reusable UI lives in `edupilot_core/templates/automation/_progress_tracker.html` and `admin_panel/static/admin_panel/{css/automation-progress.css,js/automation-progress.js}`.
- Portal voucher delivery: `edupilot_core/voucher_delivery.py` resolves Student/Parent/Class Teacher recipients; `edupilot_core/voucher_portal.py` provides recipient-scoped history/view/download/dismiss APIs; `VoucherDelivery` and `PortalNotification` live in `edupilot_core/models.py`; realtime route is `/ws/vouchers/` via `edupilot_core/consumers.py`.
- Portal voucher UI: `edupilot_core/templates/voucher_portal/`, `admin_panel/static/admin_panel/{css/portal-vouchers.css,js/portal-vouchers.js}`, plus Student/Parent/Teacher dashboard includes, bases, sidebars, and URL modules.

## Runtime Entry Points

- Management: `manage.py`
- Settings: `sms/settings.py`
- Root routing: `sms/urls.py`
- Database: PostgreSQL
- Shared templates: `templates/`
- Collected static output: `staticfiles/` (generated; do not edit directly)
- Uploaded files: `media/` (runtime data; do not treat as source)

## Root URL Mounts

- `/` and `/login/` -> role selection/login
- `/auth/` -> `login.urls`
- `/admin/` -> Django admin
- `/admin_panel/` -> `admin_panel.urls`
- `/teacher/` and `/teacher_dashboard/` -> `teacher_dashboard.urls`
- `/student/` -> `student_profile.urls`
- `/parent/` -> `parent_dashboard.urls`
- `/exam/` -> `exam_system.urls`
- `/automation/` -> `edupilot_core.urls`

## Application Summary

| App | Responsibility | Models | Routes | Templates |
|---|---|---:|---:|---:|
| `login` | Role selection, authentication entry points, and role-aware redirects. | 0 | 6 | 7 |
| `admin_panel` | Administration, academics, HR, appraisal, timetable, procurement, fleet, dashboards, and shared admin UI. | 89 | 174 | 119 |
| `admin_ai` | Admin AI copilot, analytics, reports, student intelligence, tool execution, planning, and conversation memory. | 6 | 14 | 7 |
| `ai_tutor` | Student AI tutor conversations, retrieval-augmented knowledge, safety, prompts, and tutor UI. | 7 | 9 | 4 |
| `teacher_dashboard` | Teacher portal, LMS, attendance, lesson planning, assessments, result entry, and teacher workflows. | 5 | 32 | 58 |
| `student_profile` | Student portal, profile, attendance, results, assignments, quizzes, diary, timetable, and notifications. | 3 | 12 | 22 |
| `parent_dashboard` | Parent portal and child-facing academic information. | 1 | 9 | 12 |
| `exam_system` | Exam definitions, paper generation, question bank, marks, grading, analytics, and exam workflows. | 15 | 30 | 21 |
| `edupilot_core` | Accounts, fees, salary, payments, notifications, automation, timetable fixtures, and generic data CRUD. | 29 | 21 | 93 |

## `login/`

Role selection, authentication entry points, and role-aware redirects.

### Python Modules

- `login/admin.py` - Django admin registration
- `login/apps.py` - Django application configuration
  - Classes:
    - `LoginConfig` (class, line 4)
- `login/models.py` - data models
- `login/urls.py` - URL routing
- `login/views.py` - request handlers
  - Functions:
    - `_user_has_role()`, `_linked_profile_exists()`, `role_select_view()`, `role_login_view()`, `admin_login()`, `teacher_login()`, `student_login()`, `parent_login()`
    - `login_view()`, `redirect_user_dashboard()`, `change_password()`, `custom_logout()`

### Routes

- `login/` -> `views.login_view` name=`legacy_login`
- `password_reset/` -> `auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html')` name=`password_reset`
- `password_reset/done/` -> `auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html')` name=`password_reset_done`
- `reset/<uidb64>/<token>/` -> `auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html')` name=`password_reset_confirm`
- `reset/done/` -> `auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html')` name=`password_reset_complete`
- `logout/` -> `custom_logout` name=`custom_logout`

### Templates

- `login/templates/registration/login.html`
- `login/templates/registration/password_reset_complete.html`
- `login/templates/registration/password_reset_confirm.html`
- `login/templates/registration/password_reset_done.html`
- `login/templates/registration/password_reset_form.html`
- `login/templates/registration/role_login.html`
- `login/templates/registration/role_select.html`

Static asset counts: `.css`: 2, `.js`: 1.

## `admin_panel/`

Administration, academics, HR, appraisal, timetable, procurement, fleet, dashboards, and shared admin UI.

### Python Modules

- `admin_panel/admin.py` - Django admin registration
  - Classes:
    - `CustomUserAdmin` (admin, line 19)
    - `CurriculumSourceAdmin` (admin, line 50)
    - `GuideBookAdmin` (admin, line 54)
    - `SubTopicInline` (class, line 61)
    - `TopicInline` (class, line 65)
    - `ChapterInline` (class, line 70)
    - `BookAdmin` (admin, line 80)
    - `LessonPlanRequestAdmin` (admin, line 89)
    - `LessonDayAdmin` (admin, line 105)
    - `WorksheetAdmin` (admin, line 112)
  - Functions:
    - `get_user_role()`
- `admin_panel/appraisal_services.py` - python module
  - Functions:
    - `band_from_score()`, `score_rule()`, `_feature_keys_for_template()`, `_vector_from_submission()`, `generate_score()`, `train_random_forest()`, `predict_band()`
- `admin_panel/appraisal_services1.py` - python module
  - Functions:
    - `band_from_score()`, `score_rule()`, `_feature_keys_for_template()`, `_vector_from_submission()`, `generate_score()`, `train_random_forest()`, `predict_band()`
- `admin_panel/appraisal_views_patch.py` - python module
  - Functions:
    - `is_admin()`, `admin_kpi_builder()`, `admin_appraisal_list()`, `admin_appraisal_detail()`
- `admin_panel/apps.py` - Django application configuration
  - Classes:
    - `AdminPanelConfig` (class, line 4)
- `admin_panel/context_processors.py` - shared template context
  - Functions:
    - `user_permissions()`, `teacher_fixture_notifications()`
- `admin_panel/decorators.py` - access-control decorators
  - Functions:
    - `role_required()`
- `admin_panel/forms.py` - forms and validation
  - Classes:
    - `RoleForm` (form, line 18)
    - `AssignRoleForm` (form, line 41)
    - `AdmissionForm` (form, line 79)
    - `ClassForm` (form, line 99)
    - `AcademicYearForm` (form, line 117)
    - `SectionForm` (form, line 126)
    - `SubjectForm` (form, line 139)
    - `TeacherForm` (form, line 153)
    - `CreatePeriodForm` (form, line 220)
    - `AssignedPeriodForm` (form, line 233)
    - `BookUploadForm` (form, line 307)
    - `PermissionForm` (form, line 317)
    - `StaffCategoryForm` (form, line 352)
    - `EmployeeForm` (form, line 378)
    - `JobTypeForm` (form, line 477)
    - `LeaveTypeForm` (form, line 524)
    - `TeacherFromEmployeeForm` (form, line 548)
    - `TeacherSubmissionForm` (form, line 612)
    - `StudentRegistrationForm` (form, line 649)
    - `OperationFormMixin` (class, line 665)
    - `ProcurementCategoryForm` (form, line 681)
    - `VendorForm` (form, line 687)
    - `PurchaseRequestForm` (form, line 693)
    - `InventoryItemForm` (form, line 706)
    - `StockMovementForm` (form, line 715)
    - `TransportRouteOperationForm` (form, line 721)
    - `VehicleForm` (form, line 727)
    - `RouteVehicleAssignmentForm` (form, line 739)
    - `TransportTripForm` (form, line 749)
    - `VehicleMaintenanceForm` (form, line 763)
- `admin_panel/management/commands/auto_assign_teacher_fixtures.py` - python module
  - Classes:
    - `Command` (class, line 10)
- `admin_panel/management/commands/seed_ai_analytics_demo.py` - python module
  - Classes:
    - `Command` (class, line 28)
- `admin_panel/management/commands/setup_permissions.py` - python module
  - Classes:
    - `Command` (class, line 5)
- `admin_panel/ml_toc_parser.py` - python module
  - Functions:
    - `safe_title()`, `extract_features()`, `heuristic_classify()`, `parse_book_toc_ml()`
- `admin_panel/models.py` - data models
  - Classes:
    - `UserRole` (model, line 28); relations: user -> User, role -> Group
    - `RoleActivityLog` (model, line 35); relations: action_by -> User, target_user -> User, target_role -> Group
    - `AcademicYear` (model, line 83)
    - `ClassGroup` (model, line 90)
    - `Stream` (model, line 96)
    - `Class` (model, line 103); relations: group -> ClassGroup
    - `Section` (model, line 120); relations: academic_year -> AcademicYear, class_fk -> Class
    - `Admission` (model, line 141); relations: academic_year -> AcademicYear, section -> Section, class_fk -> Class
    - `Subject` (model, line 215); relations: academic_year -> AcademicYear, class_fk -> Class, stream -> 'Stream'
    - `CreatePeriod` (model, line 260)
    - `SubjectPeriod` (model, line 278); relations: group -> ClassGroup, subject -> Subject
    - `AssignedPeriod` (model, line 294); relations: class_fk -> Class, section -> Section, subject -> Subject, period -> CreatePeriod, teacher -> 'teacher_dashboard.Teacher', timetable_version -> 'TimetableVersion'
    - `TimetableVersion` (model, line 308); relations: academic_year -> AcademicYear
    - `ClassTeacher` (model, line 330); relations: academic_year -> AcademicYear, class_fk -> Class, section -> Section, teacher -> 'teacher_dashboard.Teacher'
    - `ExamResult` (model, line 347); relations: student -> Student, subject -> Subject, class_fk -> Class, section -> Section, teacher -> 'teacher_dashboard.Teacher'
    - `Diary` (model, line 369); relations: teacher -> 'teacher_dashboard.Teacher', class_fk -> 'admin_panel.Class', section -> 'admin_panel.Section', subject -> 'admin_panel.Subject'
    - `ExamFormat` (model, line 386); relations: class_obj -> Class, subject -> Subject
    - `Question` (model, line 398); relations: exam_format -> ExamFormat, teacher -> User, section -> Section
    - `CurriculumSource` (model, line 436)
    - `GuideBook` (model, line 442); relations: subject -> 'Subject', school_class -> 'Class', source -> CurriculumSource
    - `Book` (model, line 451); relations: class_for -> Class, subject -> Subject, uploaded_by -> User
    - `Chapter` (model, line 466); relations: book -> Book, class_for -> Class, subject -> Subject, uploaded_by -> User
    - `Topic` (model, line 483); relations: chapter -> Chapter
    - `SubTopic` (model, line 495); relations: topic -> Topic
    - `ContentBlock` (model, line 507); relations: topic -> Topic, subtopic -> SubTopic
    - `LessonPlanRequest` (model, line 532); relations: chapter -> Chapter, topics -> Topic, teacher -> User
    - `LessonDay` (model, line 553); relations: plan -> 'LessonPlanRequest'
    - `Worksheet` (model, line 574); relations: lesson_plan -> LessonPlanRequest
    - `TeacherFixture` (model, line 585); relations: class_fk -> Class, section -> Section, subject -> Subject, period -> CreatePeriod, assigned_period -> 'AssignedPeriod', timetable_version -> 'TimetableVersion', absent_teacher -> 'teacher_dashboard.Teacher', substitute_teacher -> 'teacher_dashboard.Teacher', original_substitute_teacher -> 'teacher_dashboard.Teacher', overridden_by -> User
    - `Department` (model, line 667)
    - `Designation` (model, line 674); relations: department -> Department
    - `StaffCategory` (model, line 685)
    - `JobType` (model, line 692); relations: allowed_leave_types -> 'LeaveType'
    - `Employee` (model, line 707); relations: user -> User, staff_category -> StaffCategory, job_type -> JobType, department -> Department, designation -> Designation
    - `LeaveType` (model, line 766)
    - `LeaveApplication` (model, line 775); relations: employee -> Employee, leave_type -> LeaveType
    - `TeacherAbsence` (model, line 817); relations: teacher -> 'teacher_dashboard.Teacher', leave_application -> LeaveApplication, created_by -> User
    - `TeacherAbsenceResult` (model, line 849); relations: absence -> TeacherAbsence, assigned_period -> 'AssignedPeriod', fixture -> TeacherFixture
    - `TeacherNotification` (model, line 875); relations: teacher -> 'teacher_dashboard.Teacher', related_fixture -> TeacherFixture
    - `TeacherFixtureNotificationLog` (model, line 897); relations: fixture -> TeacherFixture, recipient_teacher -> 'teacher_dashboard.Teacher'
    - `TeacherAvailability` (model, line 925); relations: teacher -> 'teacher_dashboard.Teacher', period -> CreatePeriod
    - `TeacherTeachingEligibility` (model, line 951); relations: teacher -> 'teacher_dashboard.Teacher', subject -> Subject, class_fk -> Class
    - `SubjectSubstitutionRule` (model, line 968); relations: source_subject -> Subject, eligible_subject -> Subject, class_fk -> Class
    - `TeacherFixtureCandidateLog` (model, line 983); relations: absence -> TeacherAbsence, absence_result -> TeacherAbsenceResult, assigned_period -> AssignedPeriod, teacher -> 'teacher_dashboard.Teacher'
    - `TeacherFixtureHandover` (model, line 1006); relations: fixture -> TeacherFixture, submitted_by -> 'teacher_dashboard.Teacher'
    - `AppraisalCycle` (model, line 1027)
    - `GradePolicy` (model, line 1037)
    - `KpiTemplate` (model, line 1052); relations: cycle -> AppraisalCycle, grade_policy -> GradePolicy
    - `KpiTemplate` (model, line 1065); relations: cycle -> 'AppraisalCycle', grade_policy -> 'GradePolicy'
    - `KpiRule` (model, line 1074); relations: template -> KpiTemplate
    - `TeacherAppraisalSubmission` (model, line 1172); relations: teacher -> 'teacher_dashboard.Teacher', cycle -> AppraisalCycle, kpi_template -> KpiTemplate
    - `TeacherActivity` (model, line 1222); relations: submission -> 'admin_panel.TeacherAppraisalSubmission', manual_rule -> 'admin_panel.KpiRule'
    - `AppraisalScore` (model, line 1267); relations: submission -> TeacherAppraisalSubmission
    - `MLModelArtifact` (model, line 1279)
    - `AcademicCalendarEvent` (model, line 1297)
    - `FeeHead` (model, line 1346)
    - `FeePlan` (model, line 1355)
    - `FeePlanDetail` (model, line 1363); relations: fee_plan -> FeePlan, fee_head -> FeeHead
    - `TransportRoute` (model, line 1368)
    - `ProcurementCategory` (model, line 1375)
    - `Vendor` (model, line 1388)
    - `PurchaseRequest` (model, line 1408); relations: category -> ProcurementCategory, vendor -> Vendor, requested_by -> User
    - `InventoryItem` (model, line 1442); relations: category -> ProcurementCategory, vendor -> Vendor
    - `StockMovement` (model, line 1465); relations: item -> InventoryItem, created_by -> User
    - `Vehicle` (model, line 1485)
    - `RouteVehicleAssignment` (model, line 1514); relations: route -> TransportRoute, vehicle -> Vehicle
    - `TransportTrip` (model, line 1529); relations: route -> TransportRoute, vehicle -> Vehicle
    - `VehicleMaintenance` (model, line 1554); relations: vehicle -> Vehicle
    - `Scholarship` (model, line 1575)
    - `Student` (model, line 1584)
    - `StudentFeeAssignment` (model, line 1596); relations: student -> Student, fee_plan -> FeePlan, transport_route -> TransportRoute, scholarship -> Scholarship
    - `StudentLedger` (model, line 1602); relations: student -> Student
    - `StudentBalance` (model, line 1611); relations: student -> Student
    - `FeeVoucher` (model, line 1617); relations: student -> Student
    - `FeeVoucherItem` (model, line 1637); relations: voucher -> FeeVoucher, fee_head -> FeeHead
    - `FeeGenerationSettings` (model, line 1643)
    - `FeeGenerationLog` (model, line 1649)
    - `AutomationJob` (model, line 1659)
    - `AutomationJobDetail` (model, line 1669); relations: job -> AutomationJob, student -> Student
    - `NotificationQueue` (model, line 1675); relations: student -> Student
    - `Teacher` (model, line 1684)
    - `SalaryStructure` (model, line 1707); relations: teacher -> Teacher
    - `SalaryVoucher` (model, line 1711); relations: teacher -> Teacher
    - `SalaryAutomationSettings` (model, line 1720)
    - `SalaryAutomationJob` (model, line 1726)
    - `SalaryAutomationJobDetail` (model, line 1734); relations: job -> SalaryAutomationJob, teacher -> Teacher
    - `Staff` (model, line 1741)
    - `StudentPerformance` (model, line 1746); relations: student -> Student
    - `Transaction` (model, line 1752)
  - Functions:
    - `get_dashboard_stats()`, `create_ledger_entry()`
- `admin_panel/services.py` - domain services
  - Classes:
    - `PDFGeneratorService` (class, line 26)
    - `SalaryPDFGeneratorService` (class, line 48)
    - `NotificationService` (class, line 68)
    - `NotificationDispatcherService` (class, line 79)
    - `FixtureAutomationService` (class, line 92)
    - `FeeGenerationService` (class, line 796)
    - `SalaryAutomationService` (class, line 1047)
  - Functions:
    - `money()`
- `admin_panel/signals.py` - model signals
  - Functions:
    - `assign_section()`, `assign_default_group()`, `assign_permissions_based_on_role()`, `assign_group_on_creation()`
- `admin_panel/templatetags/custom_filters.py` - python module
  - Functions:
    - `dict_get()`, `period_label()`, `dict_sum()`
- `admin_panel/urls.py` - URL routing
- `admin_panel/utils.py` - python module
  - Functions:
    - `group_required()`, `role_required()`
- `admin_panel/views.py` - request handlers
  - Classes:
    - `AdminDashboardAPI` (view, line 6294)
  - Functions:
    - `setup_default_roles()`, `_detect_user_profile_type()`, `_group_permissions_by_model()`, `_split_full_name()`, `_record_role_activity()`, `_role_management_context()`, `user_role_management()`, `create_role()`
    - `list_roles()`, `assign_role_to_user()`, `admin_view_assignments()`, `admin_view_quizzes()`, `admin_view_diaries()`, `admin_view_lecture_notes()`, `assign_role()`, `teacher_dashboard()`
    - `student_profile()`, `parent_dashboard()`, `_safe_reverse()`, `_safe_value()`, `_format_automation_activity()`, `build_automation_overview_data()`, `build_admin_dashboard_stats()`, `_dashboard_card()`
    - `_dashboard_status()`, `build_attention_required_cards()`, `build_module_summary_cards()`, `build_recent_activity_items()`, `build_quick_action_cards()`, `build_dashboard_summary_data()`, `_reference_date_range()`, `_graph_range_error()`
    - `_reference_delta()`, `_reference_money()`, `_reference_buckets()`, `_reference_bucket_key()`, `build_reference_dashboard_data()`, `build_admin_dashboard_context()`, `build_ai_analytics_data()`, `ai_analytics_dashboard()`
    - `ai_analytics_data()`, `admin_dashboard()`, `access_denied()`, `custom_login()`, `custom_logout()`, `create_admin_user()`, `admin_panel_dashboard()`, `automation_overview_data()`
    - `dashboard_summary_data()`, `_admin_role_label()`, `_admin_search_result()`, `_build_admin_header_notifications()`, `_build_admin_search_results()`, `admin_header_data()`, `admin_search_suggestions()`, `admin_search()`
    - `admin_profile()`, `user_list()`, `register_admission()`, `admission_list()`, `update_admission_status()`, `is_section_full()`, `reject_reason()`, `generate_unique_student_id()`
    - `approve_admission_credentials()`, `change_admission_status()`, `query()`, `class_list()`, `class_students()`, `class_create()`, `class_update()`, `class_delete()`
    - `academic_year_list()`, `add_academic_year()`, `update_academic_year()`, `delete_academic_year()`, `add_section()`, `section_list()`, `edit_section()`, `delete_section()`
    - `subject_list()`, `add_subject()`, `edit_subject()`, `delete_subject()`, `teacher_list()`, `teacher_profile()`, `teacher_create()`, `teacher_update()`
    - `teacher_delete()`, `create_period_view()`, `period_list_view()`, `update_period_view()`, `delete_period_view()`, `timetable_automation()`, `timetable_view()`, `assign_period_view()`
    - `get_teachers_for_subject()`, `filter_subject_periods()`, `get_time_slots_for_subject_day()`, `get_days_for_subject()`, `ajax_subject_periods()`, `ajax_time_slots()`, `get_subjects_for_section()`, `get_sections_for_class()`
    - `get_periods_for_day()`, `add_class_group()`, `class_group_list()`, `delete_assignment()`, `get_assigned_classes()`, `edit_class_group()`, `delete_class_group()`, `class_teacher_list()`
    - `class_teacher_create()`, `class_teacher_update()`, `class_teacher_delete()`, `ajax_load_sections()`, `ajax_load_teachers_by_class()`, `_get_portfolio_timetable_data()`, `get_sections()`, `extract_period_number()`
    - `portfolio_timetable()`, `timetable_pdf()`, `generate_student_id_card()`, `student_id_card_list()`, `upload_student_photo()`, `stream_list()`, `add_stream()`, `edit_stream()`
    - `delete_stream()`, `my_view()`, `format_list()`, `edit_format()`, `delete_format()`, `create_format()`, `format_questions()`, `all_questions()`
    - `generate_paper_confirm()`, `_pick_most_common_questions()`, `_pick_random_questions()`, `generate_question_paper_pdf()`, `generate_question_paper()`, `upload_book()`, `book_detail()`, `book_list()`
    - `get_teacher_data()`, `manage_fixture()`, `get_free_teachers()`, `department_list()`, `department_create()`, `designation_list()`, `designation_create()`, `employee_list()`
    - `employee_create()`, `employee_edit()`, `calculate_leave_days()`, `leave_create()`, `leave_list()`, `leave_action()`, `staff_category_list()`, `staff_category_create()`
    - `job_type_list()`, `job_type_create()`, `leave_type_list()`, `leave_type_create()`, `is_admin()`, `admin_kpi_builder()`, `admin_appraisal_list()`, `admin_appraisal_detail()`
    - `_type_to_color()`, `academic_calendar_page()`, `academic_calendar_events()`, `academic_calendar_create()`, `academic_calendar_update()`, `academic_calendar_delete()`, `academic_calendar_export_pdf()`, `_parse_date()`
    - `_parse_experience()`, `_str()`, `bulk_upload_students()`, `bulk_upload_teachers()`, `bulk_delete_students()`, `bulk_delete_teachers()`, `login_view()`, `logout_view()`
    - `admin_dashboard_view()`, `student_registration_view()`, `generate_fees_view()`, `student_dashboard()`, `teacher_dashboard()`, `parent_dashboard()`, `automation_logs()`, `_operation_configs()`
    - `_operation_list()`, `_operation_save()`, `_operation_delete()`, `operation_procurement_dashboard()`, `operation_transportation_dashboard()`, `operation_summary_data()`, `_operation_view_set()`

### Routes

- `<dynamic>` -> `include('admin_ai.urls')`
- `<dynamic>` -> `views.admin_panel_dashboard` name=`admin_panel_dashboard`
- `user_list/` -> `views.user_list` name=`user_list`
- `register/` -> `views.register_admission` name=`registration`
- `admission_list/` -> `views.admission_list` name=`admission_list`
- `admission/<int:pk>/update_status/` -> `views.update_admission_status` name=`update_admission_status`
- `rejection_reason/<int:admission_id>/` -> `views.reject_reason` name=`reject_reason`
- `admission/<int:admission_id>/approve-credentials/` -> `views.approve_admission_credentials` name=`approve_admission_credentials`
- `change_admission_status/<int:admission_id>/` -> `views.change_admission_status` name=`change_admission_status`
- `query/` -> `views.query` name=`query`
- `classes/` -> `views.class_list` name=`class_list`
- `classes/add/` -> `views.class_create` name=`class_create`
- `classes/<int:pk>/students/` -> `views.class_students` name=`class_students`
- `classes/<int:pk>/edit/` -> `views.class_update` name=`class_update`
- `classes/<int:pk>/delete/` -> `views.class_delete` name=`class_delete`
- `classes/` -> `views.class_list` name=`class_list`
- `academic-years/` -> `views.academic_year_list` name=`academic_year_list`
- `academic-years/add/` -> `views.add_academic_year` name=`add_academic_year`
- `academic-years/update/<int:pk>/` -> `views.update_academic_year` name=`update_academic_year`
- `academic-years/delete/<int:pk>/` -> `views.delete_academic_year` name=`delete_academic_year`
- `sections/` -> `views.section_list` name=`section_list`
- `sections/add/` -> `views.add_section` name=`add_section`
- `sections/edit/<int:pk>/` -> `views.edit_section` name=`edit_section`
- `sections/delete/<int:pk>/` -> `views.delete_section` name=`delete_section`
- `subjects/` -> `views.subject_list` name=`subject_list`
- `subjects/add/` -> `views.add_subject` name=`add_subject`
- `subjects/edit/<int:pk>/` -> `views.edit_subject` name=`edit_subject`
- `subjects/delete/<int:pk>/` -> `views.delete_subject` name=`delete_subject`
- `teachers/` -> `views.teacher_list` name=`teacher_list`
- `teachers/add/` -> `views.teacher_create` name=`teacher_add`
- `teachers/<int:pk>/profile/` -> `views.teacher_profile` name=`teacher_profile`
- `teachers/edit/<int:pk>/` -> `views.teacher_update` name=`teacher_edit`
- `teachers/delete/<int:pk>/` -> `views.teacher_delete` name=`teacher_delete`
- `periods/` -> `views.period_list_view` name=`period_list`
- `periods/create/` -> `views.create_period_view` name=`create_period`
- `periods/update/<int:pk>/` -> `views.update_period_view` name=`update_period`
- `periods/delete/<int:pk>/` -> `views.delete_period_view` name=`delete_period`
- `timetable-automation/` -> `views.timetable_automation` name=`timetable_automation`
- `header-data/` -> `views.admin_header_data` name=`admin_header_data`
- `search/` -> `views.admin_search` name=`admin_search`
- `search-suggestions/` -> `views.admin_search_suggestions` name=`admin_search_suggestions`
- `profile/` -> `views.admin_profile` name=`admin_profile`
- `ai-analytics/` -> `views.ai_analytics_dashboard` name=`ai_analytics_dashboard`
- `ai-analytics-data/` -> `views.ai_analytics_data` name=`ai_analytics_data`
- `automation-overview-data/` -> `views.automation_overview_data` name=`automation_overview_data`
- `dashboard-summary-data/` -> `views.dashboard_summary_data` name=`dashboard_summary_data`
- `timetable/` -> `views.timetable_view` name=`timetable_view`
- `assign_period/` -> `views.assign_period_view` name=`assign_period`
- `ajax/subject_periods/` -> `views.ajax_subject_periods` name=`ajax_subject_periods`
- `ajax/time_slots/` -> `views.ajax_time_slots` name=`ajax_time_slots`
- `ajax/get_days_for_subject/` -> `views.get_days_for_subject` name=`get_days_for_subject`
- `ajax/get_subjects_for_class/` -> `views.get_subjects_for_section` name=`get_subjects_for_class`
- `ajax/get_subjects_for_section/` -> `views.get_subjects_for_section` name=`get_subjects_for_section`
- `ajax/get_assigned_classes/` -> `views.get_assigned_classes` name=`get_assigned_classes`
- `ajax/get_sections_for_class/` -> `views.get_sections_for_class` name=`get_sections_for_class`
- `ajax/delete_assignment/<int:assignment_id>/` -> `views.delete_assignment` name=`delete_assignment`
- `groups/add/` -> `views.add_class_group` name=`add_class_group`
- `groups/` -> `views.class_group_list` name=`class_group_list`
- `edit-group/<int:group_id>/` -> `views.edit_class_group` name=`edit_class_group`
- `delete-group/<int:group_id>/` -> `views.delete_class_group` name=`delete_class_group`
- `class_teachers/` -> `views.class_teacher_list` name=`class_teacher_list`
- `class_teachers/create/` -> `views.class_teacher_create` name=`class_teacher_create`
- `class_teachers/<int:pk>/edit/` -> `views.class_teacher_update` name=`class_teacher_update`
- `class_teachers/<int:pk>/delete/` -> `views.class_teacher_delete` name=`class_teacher_delete`
- `ajax/load-sections/` -> `views.ajax_load_sections` name=`ajax_load_sections`
- `ajax/load-teachers-by-class/` -> `views.ajax_load_teachers_by_class` name=`ajax_load_teachers_by_class`
- `portfolio-timetable/` -> `views.portfolio_timetable` name=`portfolio_timetable`
- `get-sections/` -> `views.get_sections` name=`get_sections`
- `generate-timetable-pdf/` -> `views.timetable_pdf` name=`timetable_pdf`
- `portfolio_timetable/` -> `views.portfolio_timetable` name=`portfolio_timetable`
- `id_cards/` -> `views.student_id_card_list` name=`student_id_card_list`
- `id_card/<int:student_id>/` -> `views.generate_student_id_card` name=`generate_id_card`
- `upload-photo/<int:student_id>/` -> `views.upload_student_photo` name=`upload_student_photo`
- `dashboard/` -> `views.admin_dashboard` name=`admin_dashboard`
- `hello/` -> `views.my_view` name=`hello`
- `streams/` -> `views.stream_list` name=`stream_list`
- `streams/add/` -> `views.add_stream` name=`add_stream`
- `streams/edit/<int:pk>/` -> `views.edit_stream` name=`edit_stream`
- `streams/delete/<int:pk>/` -> `views.delete_stream` name=`delete_stream`
- `formats/` -> `views.format_list` name=`format_list`
- `formats/<int:format_id>/edit/` -> `views.edit_format` name=`edit_format`
- `formats/<int:format_id>/delete/` -> `views.delete_format` name=`delete_format`
- `formats/create/` -> `views.create_format` name=`create_format`
- `formats/<int:format_id>/questions/` -> `views.format_questions` name=`format_questions`
- `formats/<int:format_id>/generate/` -> `views.generate_paper_confirm` name=`generate_paper_confirm`
- `formats/<int:format_id>/generate-pdf/` -> `views.generate_question_paper_pdf` name=`generate_question_paper_pdf`
- `questions/` -> `views.all_questions` name=`all_questions`
- `generate-paper/<int:format_id>/` -> `views.generate_question_paper` name=`generate_question_paper`
- `user-role-management/` -> `views.user_role_management` name=`user_role_management`
- `create-role/` -> `views.create_role` name=`create_role`
- `roles/` -> `views.list_roles` name=`list_roles`
- `assign-role/` -> `views.assign_role` name=`assign_role`
- `books/upload/` -> `views.upload_book` name=`upload_book`
- `books/parse/<int:book_id>/` -> `views.parse_book_toc_ml` name=`parse_book_toc_ml`
- `books/<int:pk>/` -> `views.book_detail` name=`book_detail`
- `books/` -> `views.book_list` name=`book_list`
- `manage_fixture/` -> `views.manage_fixture` name=`manage_fixture`
- `get_free_teachers/` -> `views.get_free_teachers` name=`get_free_teachers`
- `departments/` -> `views.department_list` name=`department_list`
- `departments/create/` -> `views.department_create` name=`department_create`
- `designations/` -> `views.designation_list` name=`designation_list`
- `designations/create/` -> `views.designation_create` name=`designation_create`
- `employees/` -> `views.employee_list` name=`employee_list`
- `employees/create/` -> `views.employee_create` name=`employee_create`
- `employees/<int:pk>/edit/` -> `views.employee_edit` name=`employee_edit`
- `staff-categories/` -> `views.staff_category_list` name=`staff_category_list`
- `staff-categories/create/` -> `views.staff_category_create` name=`staff_category_create`
- `job-types/` -> `views.job_type_list` name=`job_type_list`
- `job-types/create/` -> `views.job_type_create` name=`job_type_create`
- `leaves/` -> `views.leave_list` name=`leave_list`
- `leaves/apply/` -> `views.leave_create` name=`leave_create`
- `leaves/<int:pk>/<str:action>/` -> `views.leave_action` name=`leave_action`
- `leave-types/` -> `views.leave_type_list` name=`leave_type_list`
- `leave-types/create/` -> `views.leave_type_create` name=`leave_type_create`
- `appraisal/admin/kpis/` -> `views.admin_kpi_builder` name=`admin_kpi_builder`
- `appraisal/admin/submissions/` -> `views.admin_appraisal_list` name=`admin_appraisal_list`
- `appraisal/admin/submissions/<int:pk>/` -> `views.admin_appraisal_detail` name=`admin_appraisal_detail`
- `academic-calendar/` -> `views.academic_calendar_page` name=`academic_calendar_page`
- `academic-calendar/events/` -> `views.academic_calendar_events` name=`academic_calendar_events`
- `academic-calendar/create/` -> `views.academic_calendar_create` name=`academic_calendar_create`
- `academic-calendar/<int:event_id>/update/` -> `views.academic_calendar_update` name=`academic_calendar_update`
- `academic-calendar/<int:event_id>/delete/` -> `views.academic_calendar_delete` name=`academic_calendar_delete`
- `academic-calendar/export-pdf/` -> `views.academic_calendar_export_pdf` name=`academic_calendar_export_pdf`
- `assignments/` -> `views.admin_view_assignments` name=`admin_view_assignments`
- `quizzes/` -> `views.admin_view_quizzes` name=`admin_view_quizzes`
- `diaries/` -> `views.admin_view_diaries` name=`admin_view_diaries`
- `lecture-notes/` -> `views.admin_view_lecture_notes` name=`admin_view_lecture_notes`
- `bulk-upload-students/` -> `views.bulk_upload_students` name=`bulk_upload_students`
- `bulk-upload-teachers/` -> `views.bulk_upload_teachers` name=`bulk_upload_teachers`
- `students/bulk-delete/` -> `bulk_delete_students` name=`bulk_delete_students`
- `teachers/bulk-delete/` -> `bulk_delete_teachers` name=`bulk_delete_teachers`
- `operations/procurement/` -> `views.operation_procurement_dashboard` name=`operation_procurement_dashboard`
- `operations/<str:module>/summary-data/` -> `views.operation_summary_data` name=`operation_summary_data`
- `operations/procurement/categories/` -> `views.operation_procurement_category_list` name=`operation_procurement_category_list`
- `operations/procurement/categories/add/` -> `views.operation_procurement_category_create` name=`operation_procurement_category_create`
- `operations/procurement/categories/<int:pk>/edit/` -> `views.operation_procurement_category_edit` name=`operation_procurement_category_edit`
- `operations/procurement/categories/<int:pk>/delete/` -> `views.operation_procurement_category_delete` name=`operation_procurement_category_delete`
- `operations/procurement/vendors/` -> `views.operation_vendor_list` name=`operation_vendor_list`
- `operations/procurement/vendors/add/` -> `views.operation_vendor_create` name=`operation_vendor_create`
- `operations/procurement/vendors/<int:pk>/edit/` -> `views.operation_vendor_edit` name=`operation_vendor_edit`
- `operations/procurement/vendors/<int:pk>/delete/` -> `views.operation_vendor_delete` name=`operation_vendor_delete`
- `operations/procurement/purchase-requests/` -> `views.operation_purchase_request_list` name=`operation_purchase_request_list`
- `operations/procurement/purchase-requests/add/` -> `views.operation_purchase_request_create` name=`operation_purchase_request_create`
- `operations/procurement/purchase-requests/<int:pk>/edit/` -> `views.operation_purchase_request_edit` name=`operation_purchase_request_edit`
- `operations/procurement/purchase-requests/<int:pk>/delete/` -> `views.operation_purchase_request_delete` name=`operation_purchase_request_delete`
- `operations/procurement/inventory-items/` -> `views.operation_inventory_item_list` name=`operation_inventory_item_list`
- `operations/procurement/inventory-items/add/` -> `views.operation_inventory_item_create` name=`operation_inventory_item_create`
- `operations/procurement/inventory-items/<int:pk>/edit/` -> `views.operation_inventory_item_edit` name=`operation_inventory_item_edit`
- `operations/procurement/inventory-items/<int:pk>/delete/` -> `views.operation_inventory_item_delete` name=`operation_inventory_item_delete`
- `operations/procurement/stock-movements/` -> `views.operation_stock_movement_list` name=`operation_stock_movement_list`
- `operations/procurement/stock-movements/add/` -> `views.operation_stock_movement_create` name=`operation_stock_movement_create`
- `operations/procurement/stock-movements/<int:pk>/edit/` -> `views.operation_stock_movement_edit` name=`operation_stock_movement_edit`
- `operations/procurement/stock-movements/<int:pk>/delete/` -> `views.operation_stock_movement_delete` name=`operation_stock_movement_delete`
- `operations/transportation/` -> `views.operation_transportation_dashboard` name=`operation_transportation_dashboard`
- `operations/transportation/vehicles/` -> `views.operation_vehicle_list` name=`operation_vehicle_list`
- `operations/transportation/vehicles/add/` -> `views.operation_vehicle_create` name=`operation_vehicle_create`
- `operations/transportation/vehicles/<int:pk>/edit/` -> `views.operation_vehicle_edit` name=`operation_vehicle_edit`
- `operations/transportation/vehicles/<int:pk>/delete/` -> `views.operation_vehicle_delete` name=`operation_vehicle_delete`
- `operations/transportation/routes/` -> `views.operation_transport_route_list` name=`operation_transport_route_list`
- `operations/transportation/routes/add/` -> `views.operation_transport_route_create` name=`operation_transport_route_create`
- `operations/transportation/routes/<int:pk>/edit/` -> `views.operation_transport_route_edit` name=`operation_transport_route_edit`
- `operations/transportation/routes/<int:pk>/delete/` -> `views.operation_transport_route_delete` name=`operation_transport_route_delete`
- `operations/transportation/route-assignments/` -> `views.operation_route_assignment_list` name=`operation_route_assignment_list`
- `operations/transportation/route-assignments/add/` -> `views.operation_route_assignment_create` name=`operation_route_assignment_create`
- `operations/transportation/route-assignments/<int:pk>/edit/` -> `views.operation_route_assignment_edit` name=`operation_route_assignment_edit`
- `operations/transportation/route-assignments/<int:pk>/delete/` -> `views.operation_route_assignment_delete` name=`operation_route_assignment_delete`
- `operations/transportation/trips/` -> `views.operation_transport_trip_list` name=`operation_transport_trip_list`
- `operations/transportation/trips/add/` -> `views.operation_transport_trip_create` name=`operation_transport_trip_create`
- `operations/transportation/trips/<int:pk>/edit/` -> `views.operation_transport_trip_edit` name=`operation_transport_trip_edit`
- `operations/transportation/trips/<int:pk>/delete/` -> `views.operation_transport_trip_delete` name=`operation_transport_trip_delete`
- `operations/transportation/maintenance-records/` -> `views.operation_vehicle_maintenance_list` name=`operation_vehicle_maintenance_list`
- `operations/transportation/maintenance-records/add/` -> `views.operation_vehicle_maintenance_create` name=`operation_vehicle_maintenance_create`
- `operations/transportation/maintenance-records/<int:pk>/edit/` -> `views.operation_vehicle_maintenance_edit` name=`operation_vehicle_maintenance_edit`
- `operations/transportation/maintenance-records/<int:pk>/delete/` -> `views.operation_vehicle_maintenance_delete` name=`operation_vehicle_maintenance_delete`

### Templates

- `admin_panel/templates/admin_panel/academic_calendar.html`
- `admin_panel/templates/admin_panel/academic_year_confirm_delete.html`
- `admin_panel/templates/admin_panel/academic_year_form.html`
- `admin_panel/templates/admin_panel/academic_year_list.html`
- `admin_panel/templates/admin_panel/add_group.html`
- `admin_panel/templates/admin_panel/add_parent.html`
- `admin_panel/templates/admin_panel/add_section.html`
- `admin_panel/templates/admin_panel/add_student.html`
- `admin_panel/templates/admin_panel/admin_book_detail.html`
- `admin_panel/templates/admin_panel/admin_book_upload.html`
- `admin_panel/templates/admin_panel/admin_books_list.html`
- `admin_panel/templates/admin_panel/admin_panel_dashboard.html`
- `admin_panel/templates/admin_panel/admin_panel_dashboard1.html`
- `admin_panel/templates/admin_panel/admin_panel_home.html`
- `admin_panel/templates/admin_panel/admin_profile.html`
- `admin_panel/templates/admin_panel/admin_view_assignments.html`
- `admin_panel/templates/admin_panel/admin_view_diaries.html`
- `admin_panel/templates/admin_panel/admin_view_lecture_notes.html`
- `admin_panel/templates/admin_panel/admin_view_quizzes.html`
- `admin_panel/templates/admin_panel/admission_list.html`
- `admin_panel/templates/admin_panel/ai_analytics.html`
- `admin_panel/templates/admin_panel/all_questions.html`
- `admin_panel/templates/admin_panel/appraisal_admin_detail.html`
- `admin_panel/templates/admin_panel/appraisal_admin_kpis.html`
- `admin_panel/templates/admin_panel/appraisal_admin_list.html`
- `admin_panel/templates/admin_panel/approve_admission_credentials.html`
- `admin_panel/templates/admin_panel/assign_period.html`
- `admin_panel/templates/admin_panel/assign_role.html`
- `admin_panel/templates/admin_panel/base.html`
- `admin_panel/templates/admin_panel/bases.html`
- `admin_panel/templates/admin_panel/book_detail.html`
- `admin_panel/templates/admin_panel/book_list.html`
- `admin_panel/templates/admin_panel/bulk_upload_students.html`
- `admin_panel/templates/admin_panel/bulk_upload_teachers.html`
- `admin_panel/templates/admin_panel/class_confirm_delete.html`
- `admin_panel/templates/admin_panel/class_form.html`
- `admin_panel/templates/admin_panel/class_group_list.html`
- `admin_panel/templates/admin_panel/class_list.html`
- `admin_panel/templates/admin_panel/class_students.html`
- `admin_panel/templates/admin_panel/class_teacher_confirm_delete.html`
- `admin_panel/templates/admin_panel/class_teacher_form.html`
- `admin_panel/templates/admin_panel/class_teacher_list.html`
- `admin_panel/templates/admin_panel/create_admin_user.html`
- `admin_panel/templates/admin_panel/create_format.html`
- `admin_panel/templates/admin_panel/create_period.html`
- `admin_panel/templates/admin_panel/create_permission.html`
- `admin_panel/templates/admin_panel/create_role.html`
- `admin_panel/templates/admin_panel/create_user.html`
- `admin_panel/templates/admin_panel/delete_class_group.html`
- `admin_panel/templates/admin_panel/delete_period.html`
- `admin_panel/templates/admin_panel/delete_section.html`
- `admin_panel/templates/admin_panel/department_form.html`
- `admin_panel/templates/admin_panel/department_list.html`
- `admin_panel/templates/admin_panel/designation_form.html`
- `admin_panel/templates/admin_panel/designation_list.html`
- `admin_panel/templates/admin_panel/edit_format.html`
- `admin_panel/templates/admin_panel/edit_group.html`
- `admin_panel/templates/admin_panel/edit_section.html`
- `admin_panel/templates/admin_panel/employee_form.html`
- `admin_panel/templates/admin_panel/employee_list.html`
- `admin_panel/templates/admin_panel/footer.html`
- `admin_panel/templates/admin_panel/format_list.html`
- `admin_panel/templates/admin_panel/format_questions.html`
- `admin_panel/templates/admin_panel/generate_paper_confirm.html`
- `admin_panel/templates/admin_panel/generate_question_paper.html`
- `admin_panel/templates/admin_panel/header.html`
- `admin_panel/templates/admin_panel/id_card.html`
- `admin_panel/templates/admin_panel/includes/admin_ai_fab.html`
- `admin_panel/templates/admin_panel/index.html`
- `admin_panel/templates/admin_panel/job_type_form.html`
- `admin_panel/templates/admin_panel/job_type_list.html`
- `admin_panel/templates/admin_panel/leave_form.html`
- `admin_panel/templates/admin_panel/leave_list.html`
- `admin_panel/templates/admin_panel/leave_type_form.html`
- `admin_panel/templates/admin_panel/leave_type_list.html`
- `admin_panel/templates/admin_panel/list_roles.html`
- `admin_panel/templates/admin_panel/manage_fixture.html`
- `admin_panel/templates/admin_panel/manage_permissions.html`
- `admin_panel/templates/admin_panel/operations_confirm_delete.html`
- `admin_panel/templates/admin_panel/operations_dashboard.html`
- `admin_panel/templates/admin_panel/operations_form.html`
- `admin_panel/templates/admin_panel/operations_list.html`
- `admin_panel/templates/admin_panel/parent_list.html`
- `admin_panel/templates/admin_panel/period_list.html`
- `admin_panel/templates/admin_panel/permission_list.html`
- `admin_panel/templates/admin_panel/portfolio_timetable.html`
- `admin_panel/templates/admin_panel/query.html`
- `admin_panel/templates/admin_panel/registration.html`
- `admin_panel/templates/admin_panel/reject_reason.html`
- `admin_panel/templates/admin_panel/role_list.html`
- `admin_panel/templates/admin_panel/search_results.html`
- `admin_panel/templates/admin_panel/section_list.html`
- `admin_panel/templates/admin_panel/select_teacher.html`
- `admin_panel/templates/admin_panel/sidebar.html`
- `admin_panel/templates/admin_panel/staff_category_form.html`
- `admin_panel/templates/admin_panel/staff_category_list.html`
- `admin_panel/templates/admin_panel/stream_delete.html`
- `admin_panel/templates/admin_panel/stream_form.html`
- `admin_panel/templates/admin_panel/stream_list.html`
- `admin_panel/templates/admin_panel/student_id_card_list.html`
- `admin_panel/templates/admin_panel/subject_confirm_delete.html`
- `admin_panel/templates/admin_panel/subject_form.html`
- `admin_panel/templates/admin_panel/subject_list.html`
- `admin_panel/templates/admin_panel/teacher_book_detail.html`
- `admin_panel/templates/admin_panel/teacher_books_list.html`
- `admin_panel/templates/admin_panel/teacher_confirm_delete.html`
- `admin_panel/templates/admin_panel/teacher_form.html`
- `admin_panel/templates/admin_panel/teacher_list.html`
- `admin_panel/templates/admin_panel/teacher_profile.html`
- `admin_panel/templates/admin_panel/timetable.html`
- `admin_panel/templates/admin_panel/timetable_automation.html`
- `admin_panel/templates/admin_panel/timetable_pdf.html`
- `admin_panel/templates/admin_panel/update_parent.html`
- `admin_panel/templates/admin_panel/update_period.html`
- `admin_panel/templates/admin_panel/upload_book.html`
- `admin_panel/templates/admin_panel/upload_result.html`
- `admin_panel/templates/admin_panel/user_list.html`
- `admin_panel/templates/admin_panel/user_role_management.html`
- `admin_panel/templates/admin_panel/your_template.html`

Static asset counts: `.css`: 68, `.eot`: 23, `.gif`: 1, `.js`: 87, `.png`: 22, `.svg`: 12, `.ttf`: 12, `.woff`: 12, `.woff2`: 9.

## `admin_ai/`

Admin AI copilot, analytics, reports, student intelligence, tool execution, planning, and conversation memory.

### Python Modules

- `admin_ai/admin.py` - Django admin registration
- `admin_ai/agent.py` - python module
  - Functions:
    - `_fallback_answer()`, `run_admin_agent()`
- `admin_ai/apps.py` - Django application configuration
  - Classes:
    - `AdminAiConfig` (class, line 4)
- `admin_ai/llm.py` - python module
  - Classes:
    - `AdminLLMResult` (class, line 7)
  - Functions:
    - `generate_admin_ai_response()`
- `admin_ai/memory.py` - python module
  - Functions:
    - `build_session_memory()`
- `admin_ai/models.py` - data models
  - Classes:
    - `AdminAIConversation` (model, line 8); relations: created_by -> settings.AUTH_USER_MODEL
    - `AdminAIMessage` (model, line 21); relations: conversation -> AdminAIConversation
    - `AdminAIToolAuditLog` (model, line 43); relations: user -> settings.AUTH_USER_MODEL, conversation -> AdminAIConversation
    - `AdminAIReport` (model, line 60); relations: generated_by -> settings.AUTH_USER_MODEL
    - `AdminAIReportShareLog` (model, line 103); relations: report -> AdminAIReport, shared_by -> settings.AUTH_USER_MODEL
    - `AdminAIStudentProfileSnapshot` (model, line 135); relations: viewed_by -> settings.AUTH_USER_MODEL
- `admin_ai/planner.py` - python module
  - Functions:
    - `_looks_like_student_identifier()`, `_is_greeting_or_help()`, `_fallback_plan()`, `_clean_plan()`, `_guard_plan()`, `plan_admin_request()`
- `admin_ai/prompts.py` - python module
  - Functions:
    - `build_answer_prompt()`
- `admin_ai/security.py` - python module
  - Functions:
    - `can_use_admin_agent()`, `assert_can_use_admin_agent()`, `assert_tool_allowed()`, `sanitize_query()`
- `admin_ai/services.py` - domain services
  - Functions:
    - `_to_float()`, `_safe_count()`, `make_json_safe()`, `resolve_date_range()`, `_filter_class()`, `_class_name_for_id()`, `_series_by_day()`, `_month_bounds()`
    - `_series_by_month()`, `build_advanced_analytics()`, `parse_filter_request()`, `get_student_intelligence()`, `_extract_class_query()`, `_extract_student_id()`, `answer_admin_question()`
- `admin_ai/tools.py` - python module
  - Classes:
    - `ToolResult` (class, line 20)
  - Functions:
    - `_extract_class_query()`, `_extract_student_id()`, `_class_from_query()`, `_action()`, `_auto_report_action()`, `small_talk_tool()`, `attendance_summary_tool()`, `student_profile_tool()`
    - `fee_collection_tool()`, `teacher_workload_tool()`, `advanced_analytics_tool()`, `report_snapshot_tool()`, `general_overview_tool()`, `execute_tool()`, `serialize_tool_result()`
- `admin_ai/urls.py` - URL routing
- `admin_ai/views.py` - request handlers
  - Functions:
    - `_admin_context()`, `admin_ai_copilot()`, `admin_ai_copilot_message()`, `ai_analytics_advanced()`, `ai_analytics_advanced_data()`, `ai_analytics_reports()`, `ai_analytics_report_generate()`, `ai_analytics_report_auto_generate()`
    - `ai_analytics_report_detail()`, `_report_pdf_bytes()`, `_pdf_table()`, `ai_analytics_report_pdf()`, `ai_analytics_report_excel()`, `_add_sheet()`, `_add_chart_sheet()`, `ai_analytics_report_share()`
    - `student_intelligence()`, `student_intelligence_detail()`, `student_intelligence_pdf()`

### Routes

- `ai-copilot/` -> `views.admin_ai_copilot` name=`admin_ai_copilot`
- `ai-copilot/message/` -> `views.admin_ai_copilot_message` name=`admin_ai_copilot_message`
- `ai-analytics/advanced/` -> `views.ai_analytics_advanced` name=`ai_analytics_advanced`
- `ai-analytics/advanced/data/` -> `views.ai_analytics_advanced_data` name=`ai_analytics_advanced_data`
- `ai-analytics/reports/` -> `views.ai_analytics_reports` name=`ai_analytics_reports`
- `ai-analytics/reports/generate/` -> `views.ai_analytics_report_generate` name=`ai_analytics_report_generate`
- `ai-analytics/reports/auto-generate/` -> `views.ai_analytics_report_auto_generate` name=`ai_analytics_report_auto_generate`
- `ai-analytics/reports/<uuid:report_uuid>/` -> `views.ai_analytics_report_detail` name=`ai_analytics_report_detail`
- `ai-analytics/reports/<uuid:report_uuid>/pdf/` -> `views.ai_analytics_report_pdf` name=`ai_analytics_report_pdf`
- `ai-analytics/reports/<uuid:report_uuid>/excel/` -> `views.ai_analytics_report_excel` name=`ai_analytics_report_excel`
- `ai-analytics/reports/<uuid:report_uuid>/share/` -> `views.ai_analytics_report_share` name=`ai_analytics_report_share`
- `student-intelligence/` -> `views.student_intelligence` name=`admin_ai_student_intelligence`
- `student-intelligence/<str:student_id>/` -> `views.student_intelligence_detail` name=`admin_ai_student_intelligence_detail`
- `student-intelligence/<str:student_id>/pdf/` -> `views.student_intelligence_pdf` name=`admin_ai_student_intelligence_pdf`

### Templates

- `admin_ai/templates/admin_ai/advanced_analytics.html`
- `admin_ai/templates/admin_ai/copilot.html`
- `admin_ai/templates/admin_ai/includes/auto_report_modal.html`
- `admin_ai/templates/admin_ai/report_detail.html`
- `admin_ai/templates/admin_ai/reports.html`
- `admin_ai/templates/admin_ai/student_intelligence.html`
- `admin_ai/templates/admin_ai/student_intelligence_detail.html`

## `ai_tutor/`

Student AI tutor conversations, retrieval-augmented knowledge, safety, prompts, and tutor UI.

### Python Modules

- `ai_tutor/admin.py` - Django admin registration
  - Classes:
    - `AITutorSessionAdmin` (admin, line 15)
    - `AITutorMessageAdmin` (admin, line 22)
    - `StudentTopicMasteryAdmin` (admin, line 29)
    - `AIPracticeAttemptAdmin` (admin, line 36)
    - `StudentAIPreferenceAdmin` (admin, line 43)
    - `AIKnowledgeDocumentAdmin` (admin, line 49)
    - `AIAuditLogAdmin` (admin, line 56)
- `ai_tutor/apps.py` - Django application configuration
  - Classes:
    - `AiTutorConfig` (class, line 4)
- `ai_tutor/context_processors.py` - shared template context
  - Functions:
    - `ai_tutor_fab()`
- `ai_tutor/llm.py` - python module
  - Classes:
    - `LLMResult` (class, line 7)
  - Functions:
    - `generate_ai_tutor_response()`, `_generate_with_groq()`
- `ai_tutor/management/commands/index_ai_tutor_knowledge.py` - python module
  - Classes:
    - `Command` (class, line 9)
- `ai_tutor/models.py` - data models
  - Classes:
    - `AITutorSession` (model, line 5); relations: student -> 'student_profile.Student', subject -> 'admin_panel.Subject'
    - `AITutorMessage` (model, line 47); relations: session -> AITutorSession, student -> 'student_profile.Student'
    - `StudentTopicMastery` (model, line 85); relations: student -> 'student_profile.Student', subject -> 'admin_panel.Subject'
    - `AIPracticeAttempt` (model, line 120); relations: student -> 'student_profile.Student', session -> AITutorSession, subject -> 'admin_panel.Subject'
    - `StudentAIPreference` (model, line 158); relations: student -> 'student_profile.Student'
    - `AIKnowledgeDocument` (model, line 175); relations: class_fk -> 'admin_panel.Class', section -> 'admin_panel.Section', subject -> 'admin_panel.Subject'
    - `AIAuditLog` (model, line 244); relations: student -> 'student_profile.Student', session -> AITutorSession
- `ai_tutor/prompts.py` - python module
  - Functions:
    - `classify_intent()`, `build_system_prompt()`, `build_user_prompt()`, `build_feedback_prompt()`
- `ai_tutor/rag.py` - python module
  - Functions:
    - `retrieve_documents()`
- `ai_tutor/safety.py` - python module
  - Functions:
    - `_matches_any()`, `detect_other_student_data_request()`, `is_exam_restricted()`, `is_homework_allowed()`, `classify_query_safety()`, `validate_response_safety()`, `_blocked_message()`
- `ai_tutor/services.py` - domain services
  - Functions:
    - `get_or_create_preferences()`, `get_progress_summary()`, `handle_student_message()`, `evaluate_practice_answer()`, `create_sample_practice_attempt()`, `_increment_session()`, `_update_mastery_from_intent()`
- `ai_tutor/urls.py` - URL routing
- `ai_tutor/views.py` - request handlers
  - Functions:
    - `_student_from_request()`, `_student_subjects()`, `_student_scope_filter()`, `_latest_topic()`, `dashboard()`, `start_session()`, `chat()`, `send_message()`
    - `create_practice()`, `answer_practice()`, `progress()`, `study_plan()`, `sessions()`, `_payload()`

### Routes

- `<dynamic>` -> `views.dashboard` name=`ai_tutor_dashboard`
- `sessions/start/` -> `views.start_session` name=`ai_tutor_start_session`
- `sessions/` -> `views.sessions` name=`ai_tutor_sessions`
- `sessions/<int:session_id>/` -> `views.chat` name=`ai_tutor_chat`
- `sessions/<int:session_id>/message/` -> `views.send_message` name=`ai_tutor_send_message`
- `sessions/<int:session_id>/practice/` -> `views.create_practice` name=`ai_tutor_create_practice`
- `practice/<int:attempt_id>/answer/` -> `views.answer_practice` name=`ai_tutor_answer_practice`
- `progress/` -> `views.progress` name=`ai_tutor_progress`
- `study-plan/` -> `views.study_plan` name=`ai_tutor_study_plan`

### Templates

- `ai_tutor/templates/ai_tutor/chat.html`
- `ai_tutor/templates/ai_tutor/dashboard.html`
- `ai_tutor/templates/ai_tutor/progress.html`
- `ai_tutor/templates/ai_tutor/sessions.html`

## `teacher_dashboard/`

Teacher portal, LMS, attendance, lesson planning, assessments, result entry, and teacher workflows.

### Python Modules

- `teacher_dashboard/admin.py` - Django admin registration
  - Classes:
    - `TeacherAdmin` (admin, line 27)
  - Functions:
    - `mark_as_completed()`, `mark_as_missed()`, `mark_as_rescheduled()`
- `teacher_dashboard/appraisal_forms.py` - python module
  - Classes:
    - `TeacherAppraisalSubmissionForm` (form, line 8)
    - `TeacherActivityForm` (form, line 19)
    - `TeacherActivityBaseFormSet` (form, line 61)
- `teacher_dashboard/apps.py` - Django application configuration
  - Classes:
    - `TeacherDashboardConfig` (class, line 4)
- `teacher_dashboard/context_processors.py` - shared template context
  - Functions:
    - `lms_sidebar_context()`
- `teacher_dashboard/exam_views.py` - python module
  - Functions:
    - `get_active_year()`, `question_bank_list()`, `question_bank_detail()`, `add_question_to_bank()`, `approve_question()`, `ai_generate_questions()`, `exam_plan_list()`, `create_exam_plan()`
    - `exam_plan_detail()`, `add_exam_schedule()`, `create_blueprint()`, `generate_paper_view()`, `paper_approval_detail()`, `download_paper()`, `exam_conduct_dashboard()`, `mark_exam_attendance()`
    - `auto_generate_seating()`, `answer_sheet_list()`, `mark_answer_sheet()`, `compile_exam_results()`, `exam_results_list()`, `analytics_dashboard()`
- `teacher_dashboard/forms.py` - forms and validation
  - Classes:
    - `ExamFormatForm` (form, line 5)
    - `AddQuestionForm` (form, line 11)
    - `LessonPlanForm` (form, line 24)
    - `WorksheetGenerationForm` (form, line 35)
- `teacher_dashboard/lesson_plan_generator.py` - python module
  - Functions:
    - `clean_text()`, `build_units()`, `divide_units_into_periods()`, `learning_objectives_from_units()`, `assessment_from_units()`, `homework_from_units()`, `generate_rule_based_lesson_plan()`
- `teacher_dashboard/management/commands/backfill_lesson_ai.py` - python module
  - Classes:
    - `Command` (class, line 8)
- `teacher_dashboard/models.py` - data models
  - Classes:
    - `Teacher` (model, line 17); relations: user -> User, employee -> 'admin_panel.Employee', subjects -> Subject
    - `Attendance` (model, line 72); relations: student -> Student, class_fk -> Class, section -> Section, period -> AssignedPeriod, marked_by -> Teacher
    - `LectureNote` (model, line 120); relations: teacher -> Teacher, class_fk -> Class, section -> Section, subject -> Subject
    - `Assignment` (model, line 135); relations: teacher -> Teacher, class_fk -> Class, section -> Section, subject -> Subject
    - `Quiz` (model, line 150); relations: teacher -> Teacher, class_fk -> Class, section -> Section, subject -> Subject
  - Functions:
    - `filepath()`
- `teacher_dashboard/pdf_parsing.py` - python module
  - Classes:
    - `ContentBlock` (class, line 15)
    - `HeadingNode` (class, line 22)
    - `ChapterStructure` (class, line 31)
  - Functions:
    - `extract_text_from_pdf()`, `normalize_number_dots()`, `merge_broken_chapter_lines()`, `remove_footer_noise()`, `clean_text()`, `looks_like_table_line()`, `extract_headings_linear()`, `merge_duplicate_headings()`
    - `parse_content_blocks()`, `build_tree()`, `parse_book_text_to_structure()`, `_save_topics_and_subtopics()`, `save_book_structure_to_db()`, `parse_book_toc()`, `save_blocks_to_db()`, `parse_chapter_pdf()`
- `teacher_dashboard/templatetags/dict_extras.py` - python module
  - Functions:
    - `dict_key()`
- `teacher_dashboard/templatetags/dict_tags.py` - python module
  - Functions:
    - `dict_key()`
- `teacher_dashboard/templatetags/result_filters.py` - python module
  - Functions:
    - `get_result()`, `get_item()`
- `teacher_dashboard/urls.py` - URL routing
- `teacher_dashboard/utils.py` - python module
  - Functions:
    - `get_selected_or_logged_teacher()`
- `teacher_dashboard/views.py` - request handlers
  - Functions:
    - `get_selected_teacher()`, `get_next_school_day()`, `get_active_year()`, `teacher_dashboard_view()`, `view_students()`, `mark_attendance()`, `view_attendance()`, `attendance_summary()`
    - `upload_result()`, `merge_result()`, `lms_dashboard()`, `lms_actions_menu()`, `upload_lecture_note()`, `upload_assignment()`, `view_assignments()`, `upload_quiz()`
    - `view_assignment_submissions()`, `give_assignment_marks()`, `view_quiz_submissions()`, `submit_diary()`, `view_diary_student()`, `teacher_select_format()`, `add_question()`, `my_questions()`
    - `my_questions_by_format()`, `format_list()`, `teacher_dashboard_view()`, `mark_attendance()`, `submit_diary()`, `parse_ai_reply()`, `generate_lesson_plan_for_topic()`, `lesson_upload_chapter()`
    - `lesson_select_topics()`, `lms_books_list()`, `lms_create_book()`, `lms_book_chapters()`, `lms_chapter_lesson_plans()`, `lesson_plans_list()`, `lesson_plan_detail()`, `generate_lesson_plan_view()`
    - `generate_lesson_plan()`, `_safe_date_filter()`, `_compute_manual_score()`, `teacher_appraisal_submit()`, `get_active_year()`, `question_bank_list()`, `question_bank_detail()`, `add_question_to_bank()`
    - `approve_question()`, `ai_generate_questions()`, `exam_plan_list()`, `create_exam_plan()`, `exam_plan_detail()`, `add_exam_schedule()`, `create_blueprint()`, `generate_paper_view()`
    - `paper_approval_detail()`, `download_paper()`, `exam_conduct_dashboard()`, `mark_exam_attendance()`, `auto_generate_seating()`, `answer_sheet_list()`, `mark_answer_sheet()`, `compile_exam_results()`
    - `exam_results_list()`, `analytics_dashboard()`, `teacher_timetable_view()`

### Routes

- `teacher_dashboard/` -> `views.teacher_dashboard_view` name=`teacher_dashboard`
- `appraisal/submit/` -> `views.teacher_appraisal_submit` name=`teacher_appraisal_submit`
- `timetable/` -> `views.teacher_timetable_view` name=`teacher_timetable`
- `view-students/<int:class_id>/<int:section_id>/` -> `views.view_students` name=`view_students`
- `attendance/mark/<int:assigned_period_id>/` -> `views.mark_attendance` name=`mark_attendance`
- `attendance/view/<int:assigned_period_id>/` -> `views.view_attendance` name=`view_attendance`
- `attendance/summary/<int:assigned_period_id>/` -> `views.attendance_summary` name=`attendance_summary`
- `upload-result/<int:class_id>/<int:section_id>/<int:subject_id>/` -> `views.upload_result` name=`upload_result`
- `merge-result/<int:class_id>/<int:section_id>/` -> `views.merge_result` name=`merge_result`
- `lms/` -> `views.lms_dashboard` name=`lms_dashboard`
- `lesson-plans/` -> `views.lesson_plans_list` name=`lesson_plans_list`
- `lms/class/<int:class_id>/section/<int:section_id>/subject/<int:subject_id>/` -> `views.lms_actions_menu` name=`lms_actions_menu`
- `lms/class/<int:class_id>/section/<int:section_id>/subject/<int:subject_id>/upload-lecture/` -> `views.upload_lecture_note` name=`upload_lecture_note`
- `upload-assignment/<int:class_id>/<int:section_id>/<int:subject_id>/` -> `views.upload_assignment` name=`upload_assignment`
- `assignments/<int:class_id>/<int:section_id>/<int:subject_id>/` -> `views.view_assignments` name=`view_assignments`
- `view-submissions/<int:class_id>/<int:section_id>/<int:subject_id>/` -> `views.view_assignment_submissions` name=`view_assignment_submissions`
- `give-marks/<int:submission_id>/` -> `views.give_assignment_marks` name=`give_assignment_marks`
- `upload_quiz/<int:class_id>/<int:section_id>/<int:subject_id>/` -> `views.upload_quiz` name=`upload_quiz`
- `quiz_submissions/<int:class_id>/<int:section_id>/<int:subject_id>/` -> `views.view_quiz_submissions` name=`view_quiz_submissions`
- `diary/submit/<int:class_id>/<int:section_id>/<int:subject_id>/` -> `views.submit_diary` name=`submit_diary`
- `diary/view/<int:class_id>/<int:section_id>/<int:subject_id>/` -> `views.view_diary_student` name=`view_diary_student`
- `teacher/lms/class/<int:class_id>/section/<int:section_id>/subject/<int:subject_id>/books/` -> `views.lms_books_list` name=`lms_books_list`
- `lms/class/<int:class_id>/section/<int:section_id>/subject/<int:subject_id>/books/create/` -> `views.lms_create_book` name=`lms_create_book`
- `teacher/lms/book/<int:book_id>/chapters/` -> `views.lms_book_chapters` name=`lms_book_chapters`
- `teacher/lesson-planning/upload/` -> `views.lesson_upload_chapter` name=`lesson_upload_chapter`
- `teacher/lesson-planning/chapter/<int:chapter_id>/topics/` -> `views.lesson_select_topics` name=`lesson_select_topics`
- `teacher/lms/chapter/<int:chapter_id>/lesson-plans/` -> `views.lms_chapter_lesson_plans` name=`lms_chapter_lesson_plans`
- `exam/question-banks/` -> `views.question_bank_list` name=`question_bank_list`
- `exam/plans/` -> `views.exam_plan_list` name=`exam_plan_list`
- `exam/plans/create/` -> `views.create_exam_plan` name=`create_exam_plan`
- `exam/analytics/` -> `views.analytics_dashboard` name=`analytics_dashboard`
- `appraisal/submit/` -> `views.teacher_appraisal_submit` name=`teacher_appraisal_submit`

### Templates

- `teacher_dashboard/templates/teacher_dashboard/add_question.html`
- `teacher_dashboard/templates/teacher_dashboard/appraisal_teacher_submit.html`
- `teacher_dashboard/templates/teacher_dashboard/attendance_summary.html`
- `teacher_dashboard/templates/teacher_dashboard/base.html`
- `teacher_dashboard/templates/teacher_dashboard/bases.html`
- `teacher_dashboard/templates/teacher_dashboard/curriculum_form.html`
- `teacher_dashboard/templates/teacher_dashboard/edit_question.html`
- `teacher_dashboard/templates/teacher_dashboard/fetch_guides.html`
- `teacher_dashboard/templates/teacher_dashboard/footer.html`
- `teacher_dashboard/templates/teacher_dashboard/form-element.html`
- `teacher_dashboard/templates/teacher_dashboard/format_list.html`
- `teacher_dashboard/templates/teacher_dashboard/generate_lesson_details.html`
- `teacher_dashboard/templates/teacher_dashboard/header.html`
- `teacher_dashboard/templates/teacher_dashboard/lesson_plan_detail.html`
- `teacher_dashboard/templates/teacher_dashboard/lesson_plan_output.html`
- `teacher_dashboard/templates/teacher_dashboard/lesson_plan_preview.html`
- `teacher_dashboard/templates/teacher_dashboard/lesson_plans_list.html`
- `teacher_dashboard/templates/teacher_dashboard/lesson_select_topics.html`
- `teacher_dashboard/templates/teacher_dashboard/lesson_upload_chapter.html`
- `teacher_dashboard/templates/teacher_dashboard/lessonplan_create.html`
- `teacher_dashboard/templates/teacher_dashboard/lessonplan_detail.html`
- `teacher_dashboard/templates/teacher_dashboard/lms_action_base.html`
- `teacher_dashboard/templates/teacher_dashboard/lms_actions_menu.html`
- `teacher_dashboard/templates/teacher_dashboard/lms_base.html`
- `teacher_dashboard/templates/teacher_dashboard/lms_book_chapters.html`
- `teacher_dashboard/templates/teacher_dashboard/lms_books_list.html`
- `teacher_dashboard/templates/teacher_dashboard/lms_chapter_lesson_plans.html`
- `teacher_dashboard/templates/teacher_dashboard/lms_create_book.html`
- `teacher_dashboard/templates/teacher_dashboard/lms_dashboard.html`
- `teacher_dashboard/templates/teacher_dashboard/mark_attendance.html`
- `teacher_dashboard/templates/teacher_dashboard/merge_result.html`
- `teacher_dashboard/templates/teacher_dashboard/my_questions.html`
- `teacher_dashboard/templates/teacher_dashboard/my_questions_by_format.html`
- `teacher_dashboard/templates/teacher_dashboard/new_submit_diary.html`
- `teacher_dashboard/templates/teacher_dashboard/select_format.html`
- `teacher_dashboard/templates/teacher_dashboard/select_format_for_questions.html`
- `teacher_dashboard/templates/teacher_dashboard/sidebar.html`
- `teacher_dashboard/templates/teacher_dashboard/submit_diary.html`
- `teacher_dashboard/templates/teacher_dashboard/table-bootstrap-basic.html`
- `teacher_dashboard/templates/teacher_dashboard/table-datatable-basic.html`
- `teacher_dashboard/templates/teacher_dashboard/teacher_book_detail.html`
- `teacher_dashboard/templates/teacher_dashboard/teacher_books_list.html`
- `teacher_dashboard/templates/teacher_dashboard/teacher_dashboard.html`
- `teacher_dashboard/templates/teacher_dashboard/teacher_timetable.html`
- `teacher_dashboard/templates/teacher_dashboard/timetable.html`
- `teacher_dashboard/templates/teacher_dashboard/timetable1.html`
- `teacher_dashboard/templates/teacher_dashboard/upload_assignment.html`
- `teacher_dashboard/templates/teacher_dashboard/upload_lecture_note.html`
- `teacher_dashboard/templates/teacher_dashboard/upload_quiz.html`
- `teacher_dashboard/templates/teacher_dashboard/upload_result.html`
- `teacher_dashboard/templates/teacher_dashboard/view_assignment_submissions.html`
- `teacher_dashboard/templates/teacher_dashboard/view_assignments.html`
- `teacher_dashboard/templates/teacher_dashboard/view_attendance.html`
- `teacher_dashboard/templates/teacher_dashboard/view_diary.html`
- `teacher_dashboard/templates/teacher_dashboard/view_plans.html`
- `teacher_dashboard/templates/teacher_dashboard/view_quiz_submissions.html`
- `teacher_dashboard/templates/teacher_dashboard/view_saved_plans.html`
- `teacher_dashboard/templates/teacher_dashboard/view_students.html`

Static asset counts: `.css`: 27, `.eot`: 2, `.gif`: 1, `.js`: 78, `.png`: 12, `.svg`: 1, `.ttf`: 1, `.woff`: 1.

## `student_profile/`

Student portal, profile, attendance, results, assignments, quizzes, diary, timetable, and notifications.

### Python Modules

- `student_profile/admin.py` - Django admin registration
- `student_profile/apps.py` - Django application configuration
  - Classes:
    - `StudentProfileConfig` (class, line 4)
- `student_profile/email_utils.py` - python module
  - Functions:
    - `send_student_credentials_email()`, `send_password_reset_email()`
- `student_profile/models.py` - data models
  - Classes:
    - `Student` (model, line 25); relations: academic_year -> 'admin_panel.AcademicYear', user -> User, class_fk -> 'admin_panel.Class', section -> 'admin_panel.Section'
    - `AssignmentSubmission` (model, line 63); relations: assignment -> 'teacher_dashboard.Assignment', student -> Student
    - `QuizSubmission` (model, line 75); relations: quiz -> 'teacher_dashboard.Quiz', student -> Student
  - Functions:
    - `filepath()`
- `student_profile/templatetags/dict_filters.py` - python module
  - Functions:
    - `dictget()`
- `student_profile/urls.py` - URL routing
- `student_profile/views.py` - request handlers
  - Functions:
    - `student_dashboard()`, `create_student()`, `create_student()`, `resend_credentials()`, `student_attendance()`, `student_result()`, `student_assignments()`, `submit_assignment()`
    - `student_quizzes()`, `submit_quiz()`, `student_diary()`, `student_lecture_notes()`, `student_timetable()`

### Routes

- `dashboard/` -> `views.student_dashboard` name=`student_dashboard`
- `ai-tutor/` -> `include('ai_tutor.urls')`
- `create/` -> `views.create_student` name=`create_student`
- `<int:student_id>/resend-credentials/` -> `views.resend_credentials` name=`resend_credentials`
- `assignment/<int:assignment_id>/submit/` -> `views.submit_assignment` name=`submit_assignment`
- `quiz/<int:quiz_id>/submit/` -> `views.submit_quiz` name=`submit_quiz`
- `attendance/` -> `views.student_attendance` name=`student_attendance`
- `result/` -> `views.student_result` name=`student_result`
- `assignments/` -> `views.student_assignments` name=`student_assignments`
- `quizzes/` -> `views.student_quizzes` name=`student_quizzes`
- `diary/` -> `views.student_diary` name=`student_diary`
- `timetable/` -> `views.student_timetable` name=`student_timetable`

### Templates

- `student_profile/templates/student_profile/assignments.html`
- `student_profile/templates/student_profile/attendance.html`
- `student_profile/templates/student_profile/base.html`
- `student_profile/templates/student_profile/bases.html`
- `student_profile/templates/student_profile/create_student.html`
- `student_profile/templates/student_profile/dashboard.html`
- `student_profile/templates/student_profile/diary.html`
- `student_profile/templates/student_profile/error.html`
- `student_profile/templates/student_profile/footer.html`
- `student_profile/templates/student_profile/header.html`
- `student_profile/templates/student_profile/id_card.html`
- `student_profile/templates/student_profile/includes/ai_tutor_fab.html`
- `student_profile/templates/student_profile/lecture_notes.html`
- `student_profile/templates/student_profile/navbar.html`
- `student_profile/templates/student_profile/quizzes.html`
- `student_profile/templates/student_profile/result.html`
- `student_profile/templates/student_profile/sidebar.html`
- `student_profile/templates/student_profile/student_profile_home.html`
- `student_profile/templates/student_profile/student_timetable.html`
- `student_profile/templates/student_profile/submit_assignment.html`
- `student_profile/templates/student_profile/submit_quiz.html`
- `student_profile/templates/student_profile/timetable.html`

## `parent_dashboard/`

Parent portal and child-facing academic information.

### Python Modules

- `parent_dashboard/admin.py` - Django admin registration
- `parent_dashboard/apps.py` - Django application configuration
  - Classes:
    - `ParentDashboardConfig` (class, line 4)
- `parent_dashboard/models.py` - data models
  - Classes:
    - `Parent` (model, line 29); relations: user -> User, students -> 'student_profile.Student'
- `parent_dashboard/urls.py` - URL routing
- `parent_dashboard/views.py` - request handlers
  - Functions:
    - `parent_dashboard_home()`, `parent_list()`, `parent_dashboard()`, `parent_attendance()`, `parent_result()`, `parent_assignment()`, `parent_quizzes()`, `parent_diary()`
    - `parent_timetable()`

### Routes

- `home/` -> `views.parent_dashboard_home` name=`parent_dashboard_home`
- `<dynamic>` -> `views.parent_dashboard` name=`parent_dashboard`
- `list/` -> `views.parent_list` name=`parent_list`
- `attendance/` -> `views.parent_attendance` name=`parent_attendance`
- `result/` -> `views.parent_result` name=`parent_result`
- `assignments/` -> `views.parent_assignment` name=`parent_assignment`
- `quizzes/` -> `views.parent_quizzes` name=`parent_quizzes`
- `diary/` -> `views.parent_diary` name=`parent_diary`
- `timetable/` -> `views.parent_timetable` name=`parent_timetable`

### Templates

- `parent_dashboard/templates/parent_dashboard/assignments.html`
- `parent_dashboard/templates/parent_dashboard/attendance.html`
- `parent_dashboard/templates/parent_dashboard/base.html`
- `parent_dashboard/templates/parent_dashboard/dashboard.html`
- `parent_dashboard/templates/parent_dashboard/diary.html`
- `parent_dashboard/templates/parent_dashboard/parent_dashboard_home.html`
- `parent_dashboard/templates/parent_dashboard/parent_list.html`
- `parent_dashboard/templates/parent_dashboard/quizzes.html`
- `parent_dashboard/templates/parent_dashboard/result.html`
- `parent_dashboard/templates/parent_dashboard/sidebar.html`
- `parent_dashboard/templates/parent_dashboard/signup.html`
- `parent_dashboard/templates/parent_dashboard/timetable.html`

## `exam_system/`

Exam definitions, paper generation, question bank, marks, grading, analytics, and exam workflows.

### Python Modules

- `exam_system/models.py` - data models
  - Classes:
    - `QuestionBank` (model, line 18); relations: subject -> Subject, class_fk -> Class, academic_year -> AcademicYear, created_by -> User
    - `Question` (model, line 32); relations: bank -> QuestionBank, approved_by -> User
    - `ExamPlan` (model, line 83); relations: academic_year -> AcademicYear, class_fk -> Class, created_by -> User
    - `ExamSchedule` (model, line 105); relations: exam_plan -> ExamPlan, subject -> Subject
    - `PaperBlueprint` (model, line 120); relations: exam_plan -> ExamPlan, subject -> Subject, created_by -> User
    - `BlueprintRule` (model, line 131); relations: blueprint -> PaperBlueprint
    - `GeneratedPaper` (model, line 144); relations: blueprint -> PaperBlueprint, section -> Section, questions -> Question, generated_by -> User
    - `PaperApproval` (model, line 179); relations: paper -> GeneratedPaper, reviewed_by -> User
    - `PaperAccessLog` (model, line 206); relations: paper -> GeneratedPaper, accessed_by -> User
    - `ExamSeatingPlan` (model, line 225); relations: schedule -> ExamSchedule, student -> Student
    - `InvigilatorDuty` (model, line 238); relations: schedule -> ExamSchedule, teacher -> Teacher
    - `ExamAttendance` (model, line 247); relations: schedule -> ExamSchedule, student -> Student, marked_by -> Teacher
    - `AnswerSheet` (model, line 265); relations: schedule -> ExamSchedule, student -> Student, paper -> GeneratedPaper
    - `QuestionScore` (model, line 280); relations: answer_sheet -> AnswerSheet, question -> Question, verified_by -> User
    - `CentralizedResult` (model, line 300); relations: answer_sheet -> AnswerSheet
- `exam_system/services.py` - domain services
  - Functions:
    - `_call_groq()`, `generate_questions_ai()`, `generate_questions_from_pdf_text()`, `generate_paper_from_blueprint()`, `compile_results()`, `generate_final_pdf()`, `generate_paper_pdf()`
- `exam_system/urls.py` - URL routing
- `exam_system/views.py` - request handlers
  - Functions:
    - `get_active_year()`, `_extract_pdf_text()`, `_groq_generate()`, `question_bank_list()`, `delete_question_bank()`, `question_bank_detail()`, `upload_book_for_bank()`, `add_question_to_bank()`
    - `edit_question()`, `approve_question()`, `bulk_approve_questions()`, `toggle_approve_question()`, `ai_generate_questions()`, `exam_plan_list()`, `create_exam_plan()`, `exam_plan_detail()`
    - `add_exam_schedule()`, `create_blueprint()`, `generate_paper_view()`, `admin_paper_queue()`, `paper_approval_detail()`, `upload_pdf_for_paper()`, `download_paper()`, `exam_conduct_dashboard()`
    - `mark_exam_attendance()`, `auto_generate_seating()`, `answer_sheet_list()`, `mark_answer_sheet()`, `compile_exam_results()`, `exam_results_list()`, `analytics_dashboard()`, `build_exam_analytics_data()`
    - `analytics_data()`

### Routes

- `question-banks/` -> `views.question_bank_list` name=`question_bank_list`
- `question-banks/<int:bank_id>/delete/` -> `views.delete_question_bank` name=`delete_question_bank`
- `question-banks/<int:bank_id>/` -> `views.question_bank_detail` name=`question_bank_detail`
- `question-banks/<int:bank_id>/add-question/` -> `views.add_question_to_bank` name=`add_question_to_bank`
- `question-banks/<int:bank_id>/bulk-approve/` -> `views.bulk_approve_questions` name=`bulk_approve_questions`
- `question-banks/<int:bank_id>/ai-generate/` -> `views.ai_generate_questions` name=`ai_generate_questions`
- `question-banks/<int:bank_id>/upload-book/` -> `views.upload_book_for_bank` name=`upload_book_for_bank`
- `question-banks/<int:bank_id>/generate-from-pdf/` -> `views.upload_book_for_bank` name=`generate_questions_from_pdf`
- `questions/<int:question_id>/approve/` -> `views.approve_question` name=`approve_question`
- `questions/<int:question_id>/edit/` -> `views.edit_question` name=`edit_question`
- `questions/<int:question_id>/toggle-approve/` -> `views.toggle_approve_question` name=`toggle_approve_question`
- `plans/` -> `views.exam_plan_list` name=`exam_plan_list`
- `plans/create/` -> `views.create_exam_plan` name=`create_exam_plan`
- `plans/<int:plan_id>/` -> `views.exam_plan_detail` name=`exam_plan_detail`
- `plans/<int:plan_id>/add-schedule/` -> `views.add_exam_schedule` name=`add_exam_schedule`
- `plans/<int:plan_id>/blueprint/<int:subject_id>/` -> `views.create_blueprint` name=`create_blueprint`
- `papers/queue/` -> `views.admin_paper_queue` name=`admin_paper_queue`
- `blueprint/<int:blueprint_id>/generate-paper/` -> `views.generate_paper_view` name=`generate_paper_view`
- `papers/<int:paper_id>/approval/` -> `views.paper_approval_detail` name=`paper_approval_detail`
- `papers/<int:paper_id>/upload-pdf/` -> `views.upload_pdf_for_paper` name=`upload_pdf_for_paper`
- `papers/<int:paper_id>/download/` -> `views.download_paper` name=`download_paper`
- `conduct/<int:schedule_id>/` -> `views.exam_conduct_dashboard` name=`exam_conduct_dashboard`
- `conduct/<int:schedule_id>/attendance/` -> `views.mark_exam_attendance` name=`mark_exam_attendance`
- `conduct/<int:schedule_id>/seating/` -> `views.auto_generate_seating` name=`auto_generate_seating`
- `conduct/<int:schedule_id>/sheets/` -> `views.answer_sheet_list` name=`answer_sheet_list`
- `sheets/<int:sheet_id>/mark/` -> `views.mark_answer_sheet` name=`mark_answer_sheet`
- `conduct/<int:schedule_id>/compile/` -> `views.compile_exam_results` name=`compile_exam_results`
- `conduct/<int:schedule_id>/results/` -> `views.exam_results_list` name=`exam_results_list`
- `analytics/` -> `views.analytics_dashboard` name=`analytics_dashboard`
- `analytics/data/` -> `views.analytics_data` name=`analytics_data`

### Templates

- `exam_system/templates/exam_system/add_question.html`
- `exam_system/templates/exam_system/add_schedule.html`
- `exam_system/templates/exam_system/admin_paper_queue.html`
- `exam_system/templates/exam_system/ai_generate_questions.html`
- `exam_system/templates/exam_system/analytics_dashboard.html`
- `exam_system/templates/exam_system/approve_question.html`
- `exam_system/templates/exam_system/create_blueprint.html`
- `exam_system/templates/exam_system/create_exam_plan.html`
- `exam_system/templates/exam_system/exam_plan_detail.html`
- `exam_system/templates/exam_system/exam_plan_list.html`
- `exam_system/templates/exam_system/exam_results_list.html`
- `exam_system/templates/exam_system/generate_from_pdf.html`
- `exam_system/templates/exam_system/generate_paper.html`
- `exam_system/templates/exam_system/paper_approval_detail.html`
- `exam_system/templates/exam_system/paper_approval_detail1.html`
- `exam_system/templates/exam_system/question_bank_detail.html`
- `exam_system/templates/exam_system/question_bank_list.html`
- `exam_system/templates/exam_system/question_bank_list1.html`
- `exam_system/templates/exam_system/upload_book_for_bank.html`
- `exam_system/templates/exam_system/upload_book_for_bank2.html`
- `exam_system/templates/exam_system/upload_pdf_for_paper.html`

Static asset counts: `.css`: 1, `.js`: 1.

## `edupilot_core/`

Accounts, fees, salary, payments, notifications, automation, timetable fixtures, and generic data CRUD.

### Python Modules

- `edupilot_core/admin.py` - Django admin registration
  - Classes:
    - `TeacherAdmin` (admin, line 22)
    - `SalaryStructureAdmin` (admin, line 42)
    - `SalaryVoucherAdmin` (admin, line 48)
    - `SalaryAutomationSettingsAdmin` (admin, line 63)
    - `SalaryAutomationJobAdmin` (admin, line 74)
    - `SalaryAutomationJobDetailAdmin` (admin, line 80)
    - `FeeGenerationSettingsAdmin` (admin, line 87)
    - `NotificationQueueAdmin` (admin, line 93)
    - `FeeGenerationLogAdmin` (admin, line 99)
    - `AutomationJobAdmin` (admin, line 104)
    - `AutomationJobDetailAdmin` (admin, line 122)
    - `StudentAdmin` (admin, line 129)
    - `StudentPerformanceAdmin` (admin, line 135)
    - `TransactionAdmin` (admin, line 141)
    - `StaffAdmin` (admin, line 146)
    - `FeeHeadAdmin` (admin, line 152)
    - `FeePlanAdmin` (admin, line 158)
    - `FeePlanDetailAdmin` (admin, line 163)
    - `TransportRouteAdmin` (admin, line 168)
    - `ScholarshipAdmin` (admin, line 172)
    - `StudentFeeAssignmentAdmin` (admin, line 176)
    - `StudentLedgerAdmin` (admin, line 182)
    - `StudentBalanceAdmin` (admin, line 188)
    - `FeeVoucherItemInline` (class, line 192)
    - `FeeVoucherAdmin` (admin, line 197)
    - `FeeVoucherItemAdmin` (admin, line 221)
  - Functions:
    - `retry_failed_salary()`, `retry_failed_records()`
- `edupilot_core/api/serializers.py` - python module
  - Classes:
    - `FeeVoucherSerializer` (class, line 44)
    - `StudentDashboardSerializer` (class, line 49)
    - `StudentDashboardAPI` (view, line 61)
    - `ParentDashboardAPI` (view, line 72)
- `edupilot_core/apps.py` - Django application configuration
  - Classes:
    - `EdupilotCoreConfig` (class, line 16)
- `edupilot_core/canonical_sync.py` - canonical portal-to-automation mapping and compatibility synchronization
  - Functions:
    - `ensure_legacy_student()`, `ensure_legacy_teacher()`, `sync_portal_student()`, `sync_portal_teacher()`
- `edupilot_core/crud_views.py` - python module
  - Functions:
    - `get_config_or_404()`, `crud_list_view()`, `crud_create_view()`, `crud_update_view()`, `crud_delete_view()`
- `edupilot_core/forms.py` - forms and validation
  - Classes:
    - `StudentRegistrationForm` (form, line 5)
- `edupilot_core/models.py` - data models
  - Classes:
    - `FeeHead` (model, line 21)
    - `FeePlan` (model, line 30)
    - `FeePlanDetail` (model, line 38); relations: fee_plan -> FeePlan, fee_head -> FeeHead
    - `TransportRoute` (model, line 43)
    - `Scholarship` (model, line 50)
    - `Student` (model, line 59)
    - `StudentFeeAssignment` (model, line 71); relations: student -> Student, fee_plan -> FeePlan, transport_route -> TransportRoute, scholarship -> Scholarship
    - `StudentLedger` (model, line 77); relations: student -> Student
    - `StudentBalance` (model, line 86); relations: student -> Student
    - `FeeVoucher` (model, line 92); relations: student -> Student
    - `FeeVoucherItem` (model, line 112); relations: voucher -> FeeVoucher, fee_head -> FeeHead
    - `FeeGenerationSettings` (model, line 118)
    - `FeeGenerationLog` (model, line 124)
    - `AutomationJob` (model, line 134)
    - `AutomationJobDetail` (model, line 144); relations: job -> AutomationJob, student -> Student
    - `NotificationQueue` (model, line 158); relations: student -> Student, teacher -> 'Teacher'
    - `Teacher` (model, line 168)
    - `SalaryStructure` (model, line 191); relations: teacher -> Teacher
    - `SalaryVoucher` (model, line 195); relations: teacher -> Teacher
    - `SalaryAutomationSettings` (model, line 204)
    - `SalaryAutomationJob` (model, line 210)
    - `SalaryAutomationJobDetail` (model, line 218); relations: job -> SalaryAutomationJob, teacher -> Teacher
    - `Staff` (model, line 225)
    - `StudentPerformance` (model, line 230); relations: student -> Student
    - `Transaction` (model, line 236)
    - `CanonicalMappingAudit` - matched, ambiguous, and unmatched legacy mapping audit
    - `Period` (model, line 268); relations: teacher -> Teacher
    - `AssignedPeriods` (model, line 278); relations: teacher -> Teacher, period -> Period
    - `Fixture` (model, line 282); relations: absent_teacher -> Teacher, replacement_teacher -> Teacher, period -> Period
    - `Absence` (model, line 289); relations: teacher -> Teacher, period -> Period
  - Functions:
    - `get_dashboard_stats()`, `create_ledger_entry()`
- `edupilot_core/payment_service.py` - python module
  - Classes:
    - `DummyPaymentService` (class, line 12)
- `edupilot_core/services.py` - domain services
  - Classes:
    - `PDFGeneratorService` (class, line 21)
    - `SalaryPDFGeneratorService` (class, line 43)
    - `NotificationService` (class, line 63)
    - `NotificationDispatcherService` (class, line 74)
    - `FeeGenerationService` (class, line 86)
    - `SalaryAutomationService` (class, line 337)
    - `FixtureAutomationService` (class, line 396)
  - Functions:
    - `money()`
- `edupilot_core/updater.py` - python module
  - Functions:
    - `run_scheduled_job()`, `check_and_run_job()`, `check_salary_job()`, `start()`
- `edupilot_core/urls.py` - URL routing
- `edupilot_core/views.py` - request handlers
  - Classes:
    - `AdminDashboardAPI` (view, line 195)
  - Functions:
    - `_build_fee_collection_chart()`, `login_view()`, `logout_view()`, `admin_dashboard_view()`, `student_registration_view()`, `generate_fees_view()`, `student_dashboard()`, `teacher_dashboard()`
    - `parent_dashboard()`, `automation_logs()`, `automation_dashboard()`, `automation_graph_data()`, `fee_automation_view()`, `voucher_management_view()`, `notification_queue_view()`, `salary_automation_view()`
    - `payslip_management_view()`, `automation_settings_view()`, `timetable_list()`, `create_period()`, `mark_absence()`, `fixture_auto_assign()`, `timetable_list()`, `create_period()`
    - `mark_absence()`, `fixture_auto_assign()`, `mark_absence()`, `teacher_schedule()`, `timetable_logs()`

### Routes

- `<dynamic>` -> `views.automation_dashboard` name=`automation-dashboard`
- `graph-data/` -> `views.automation_graph_data` name=`automation-graph-data`
- `fee/` -> `views.fee_automation_view` name=`fee-automation`
- `vouchers/` -> `views.voucher_management_view` name=`voucher-management`
- `notifications/` -> `views.notification_queue_view` name=`notification-queue`
- `salary/` -> `views.salary_automation_view` name=`salary-automation`
- `payslips/` -> `views.payslip_management_view` name=`payslip-management`
- `logs/` -> `views.automation_logs` name=`automation-logs`
- `settings/` -> `views.automation_settings_view` name=`automation-settings`
- `data/<str:model_name>/` -> `crud_views.crud_list_view` name=`crud-list`
- `data/<str:model_name>/add/` -> `crud_views.crud_create_view` name=`crud-create`
- `data/<str:model_name>/<int:pk>/edit/` -> `crud_views.crud_update_view` name=`crud-update`
- `data/<str:model_name>/<int:pk>/delete/` -> `crud_views.crud_delete_view` name=`crud-delete`
- `feevoucher/generate-all-fees/` -> `views.generate_fees_view` name=`generate_fees_view`
- `api/dashboard/` -> `AdminDashboardAPI.as_view()` name=`edupilot-admin-dashboard-api`
- `timetable/` -> `views.timetable_list` name=`timetable-list`
- `periods/` -> `views.create_period` name=`create-period`
- `absence/` -> `views.mark_absence` name=`mark-absence`
- `fixtures/` -> `views.fixture_auto_assign` name=`fixtures-list`
- `teacher/schedule/` -> `views.teacher_schedule` name=`teacher-schedule`
- `timetable/logs/` -> `views.timetable_logs` name=`timetable-logs`

### Templates

- `edupilot_core/templates/automation/base_automation.html`
- `edupilot_core/templates/automation/crud_delete_confirm.html`
- `edupilot_core/templates/automation/crud_form.html`
- `edupilot_core/templates/automation/crud_list.html`
- `edupilot_core/templates/automation/dashboard.html`
- `edupilot_core/templates/automation/fee.html`
- `edupilot_core/templates/automation/logs.html`
- `edupilot_core/templates/automation/notifications.html`
- `edupilot_core/templates/automation/salary.html`
- `edupilot_core/templates/automation/settings.html`
- `edupilot_core/templates/automation/sidebar.html`
- `edupilot_core/templates/automation/vouchers.html`
- `edupilot_core/templates/base.html`
- `edupilot_core/templates/dashboard.html`
- `edupilot_core/templates/fee_voucher_change_list.html`
- `edupilot_core/templates/login.html`
- `edupilot_core/templates/notifications/center.html`
- `edupilot_core/templates/parent/dashboard.html`
- `edupilot_core/templates/register.html`
- `edupilot_core/templates/student_profile/assignments.html`
- `edupilot_core/templates/student_profile/attendance.html`
- `edupilot_core/templates/student_profile/base.html`
- `edupilot_core/templates/student_profile/bases.html`
- `edupilot_core/templates/student_profile/dashboard.html`
- `edupilot_core/templates/student_profile/diary.html`
- `edupilot_core/templates/student_profile/error.html`
- `edupilot_core/templates/student_profile/footer.html`
- `edupilot_core/templates/student_profile/header.html`
- `edupilot_core/templates/student_profile/id_card.html`
- `edupilot_core/templates/student_profile/lecture_notes.html`
- `edupilot_core/templates/student_profile/navbar.html`
- `edupilot_core/templates/student_profile/quizzes.html`
- `edupilot_core/templates/student_profile/result.html`
- `edupilot_core/templates/student_profile/student_profile_home.html`
- `edupilot_core/templates/student_profile/student_timetable.html`
- `edupilot_core/templates/student_profile/submit_assignment.html`
- `edupilot_core/templates/student_profile/submit_quiz.html`
- `edupilot_core/templates/student_profile/timetable.html`
- `edupilot_core/templates/teacher_dashboard/add_question.html`
- `edupilot_core/templates/teacher_dashboard/appraisal_teacher_submit.html`
- `edupilot_core/templates/teacher_dashboard/attendance_summary.html`
- `edupilot_core/templates/teacher_dashboard/base.html`
- `edupilot_core/templates/teacher_dashboard/bases.html`
- `edupilot_core/templates/teacher_dashboard/curriculum_form.html`
- `edupilot_core/templates/teacher_dashboard/edit_question.html`
- `edupilot_core/templates/teacher_dashboard/fetch_guides.html`
- `edupilot_core/templates/teacher_dashboard/footer.html`
- `edupilot_core/templates/teacher_dashboard/form-element.html`
- `edupilot_core/templates/teacher_dashboard/format_list.html`
- `edupilot_core/templates/teacher_dashboard/generate_lesson_details.html`
- `edupilot_core/templates/teacher_dashboard/header.html`
- `edupilot_core/templates/teacher_dashboard/lesson_plan_detail.html`
- `edupilot_core/templates/teacher_dashboard/lesson_plan_output.html`
- `edupilot_core/templates/teacher_dashboard/lesson_plan_preview.html`
- `edupilot_core/templates/teacher_dashboard/lesson_plans_list.html`
- `edupilot_core/templates/teacher_dashboard/lesson_select_topics.html`
- `edupilot_core/templates/teacher_dashboard/lesson_upload_chapter.html`
- `edupilot_core/templates/teacher_dashboard/lessonplan_create.html`
- `edupilot_core/templates/teacher_dashboard/lessonplan_detail.html`
- `edupilot_core/templates/teacher_dashboard/lms_action_base.html`
- `edupilot_core/templates/teacher_dashboard/lms_actions_menu.html`
- `edupilot_core/templates/teacher_dashboard/lms_base.html`
- `edupilot_core/templates/teacher_dashboard/lms_book_chapters.html`
- `edupilot_core/templates/teacher_dashboard/lms_books_list.html`
- `edupilot_core/templates/teacher_dashboard/lms_chapter_lesson_plans.html`
- `edupilot_core/templates/teacher_dashboard/lms_create_book.html`
- `edupilot_core/templates/teacher_dashboard/lms_dashboard.html`
- `edupilot_core/templates/teacher_dashboard/mark_attendance.html`
- `edupilot_core/templates/teacher_dashboard/merge_result.html`
- `edupilot_core/templates/teacher_dashboard/my_questions.html`
- `edupilot_core/templates/teacher_dashboard/my_questions_by_format.html`
- `edupilot_core/templates/teacher_dashboard/new_submit_diary.html`
- `edupilot_core/templates/teacher_dashboard/select_format.html`
- `edupilot_core/templates/teacher_dashboard/select_format_for_questions.html`
- `edupilot_core/templates/teacher_dashboard/submit_diary.html`
- `edupilot_core/templates/teacher_dashboard/table-bootstrap-basic.html`
- `edupilot_core/templates/teacher_dashboard/table-datatable-basic.html`
- `edupilot_core/templates/teacher_dashboard/teacher_book_detail.html`
- `edupilot_core/templates/teacher_dashboard/teacher_books_list.html`
- `edupilot_core/templates/teacher_dashboard/teacher_dashboard.html`
- `edupilot_core/templates/teacher_dashboard/teacher_timetable.html`
- `edupilot_core/templates/teacher_dashboard/upload_assignment.html`
- `edupilot_core/templates/teacher_dashboard/upload_lecture_note.html`
- `edupilot_core/templates/teacher_dashboard/upload_quiz.html`
- `edupilot_core/templates/teacher_dashboard/upload_result.html`
- `edupilot_core/templates/teacher_dashboard/view_assignment_submissions.html`
- `edupilot_core/templates/teacher_dashboard/view_assignments.html`
- `edupilot_core/templates/teacher_dashboard/view_attendance.html`
- `edupilot_core/templates/teacher_dashboard/view_diary.html`
- `edupilot_core/templates/teacher_dashboard/view_plans.html`
- `edupilot_core/templates/teacher_dashboard/view_quiz_submissions.html`
- `edupilot_core/templates/teacher_dashboard/view_saved_plans.html`
- `edupilot_core/templates/teacher_dashboard/view_students.html`

## Shared Templates

- `templates/base.html`
- `templates/shared/header/portal_header.html`
- `templates/shared/sidebar/shell.html`

## Cross-App Dependencies

- `admin_ai` -> `admin_panel`
- `admin_ai` -> `student_profile`
- `admin_ai` -> `teacher_dashboard`
- `admin_panel` -> `parent_dashboard`
- `admin_panel` -> `student_profile`
- `admin_panel` -> `teacher_dashboard`
- `ai_tutor` -> `admin_panel`
- `ai_tutor` -> `student_profile`
- `ai_tutor` -> `teacher_dashboard`
- `exam_system` -> `admin_panel`
- `exam_system` -> `student_profile`
- `exam_system` -> `teacher_dashboard`
- `parent_dashboard` -> `admin_panel`
- `parent_dashboard` -> `teacher_dashboard`
- `student_profile` -> `admin_panel`
- `student_profile` -> `teacher_dashboard`
- `teacher_dashboard` -> `admin_panel`
- `teacher_dashboard` -> `exam_system`
- `teacher_dashboard` -> `student_profile`

## Fast Change Lookup

| Request | Start With | Then Check |
|---|---|---|
| Fee generation or voucher behavior | `edupilot_core/services.py`, `edupilot_core/models.py` | `edupilot_core/views.py`, automation templates |
| Payment or ledger behavior | `edupilot_core/payment_service.py`, `edupilot_core/models.py` | fee/student/parent views |
| Notification delivery | `edupilot_core/services.py`, notification models | automation queue templates and logs |
| Admin dashboard data/UI | `admin_panel/views.py`, `admin_panel/templates/admin_panel/index.html` | dashboard CSS/JS and canonical app models |
| AI analytics/Copilot | `admin_ai/`, `admin_panel/templates/admin_panel/ai_analytics.html` | `admin_panel/views.py`, shared AI CSS/JS |
| Teacher LMS/attendance | `teacher_dashboard/views.py`, `teacher_dashboard/models.py` | teacher templates/forms |
| Student portal | `student_profile/views.py`, `student_profile/models.py` | student templates and shared portal shell |
| Parent portal | `parent_dashboard/views.py` | parent templates and student-linked data |
| Exams/papers/results | `exam_system/views.py`, `exam_system/services.py`, `exam_system/models.py` | teacher exam views and templates |
| HR/leaves/appraisal | `admin_panel/models.py`, `admin_panel/views.py`, appraisal services | HR/appraisal templates and forms |
| Procurement/fleet | `admin_panel/models.py`, `admin_panel/views.py` | operations templates and dashboard endpoint |
| Sidebar/header/button/chart system | `templates/shared/`, `admin_panel/static/admin_panel/css/` | portal base templates and shared JS |

## Maintenance Rules

1. Read this map first, but verify targeted files before editing.
2. Update this map when apps, models, routes, services, or template ownership changes.
3. Do not edit `staticfiles/`, migrations, media uploads, or generated bundles for normal feature work.
4. Preserve form methods, CSRF tokens, input names, URL names, permissions, and JavaScript data hooks during UI-only work.
5. `PROJECT_MAP.json` is the machine-readable source for automated lookup.
