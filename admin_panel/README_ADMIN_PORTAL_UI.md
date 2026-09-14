# EduPilot Admin Portal UI Inventory

This document is the source map for improving the **real Admin Portal UI** without changing business logic, permissions, routes, forms, AJAX contracts, or existing workflows. It records the current screens, shared components, frontend assets, and the files that control them.

## 1. Scope and entry points

| Item | Location |
|---|---|
| Admin portal URL prefix | `/admin_panel/` |
| Project URL registration | `sms/urls.py` |
| Main admin routes | `admin_panel/urls.py` |
| Main admin views | `admin_panel/views.py` and `admin_panel/admission_views.py` |
| Admin templates | `admin_panel/templates/admin_panel/` |
| Admin CSS | `admin_panel/static/admin_panel/css/` |
| Admin JavaScript | `admin_panel/static/admin_panel/js/` |
| Admin images, icons and vendor libraries | `admin_panel/static/admin_panel/` |
| Sidebar/menu definition | `admin_panel/templates/admin_panel/sidebar.html` |

The admin portal also links to screens owned by `admin_ai`, `exam_system`, `finance`, `helpdesk`, `communication`, and `edupilot_core`. Those screens are included below because they are part of the admin user's visible product experience.

## 2. Shared page shell and reusable components

The two current base layouts are:

| Component | File | Purpose |
|---|---|---|
| Primary admin shell | `admin_panel/templates/admin_panel/bases.html` | Loads the current theme, shared header/sidebar, page content, AI action button, footer, and global scripts. Uses `.content-body`. |
| Alternate admin shell | `admin_panel/templates/admin_panel/base.html` | Alternate/older shell used by several pages. Uses `.main-content` and loads Chart.js plus `base.js`. |
| Header adapter | `admin_panel/templates/admin_panel/header.html` | Includes the shared portal header with `portal_kind='admin'`. |
| Shared portal header | `templates/shared/header/portal_header.html` | Common top navigation/header UI. |
| Sidebar shell | `templates/shared/sidebar/shell.html` | Common sidebar wrapper and responsive/collapse structure. |
| Admin menu | `admin_panel/templates/admin_panel/sidebar.html` | All admin menu groups, links, icons, active states, and permission checks. |
| Footer | `admin_panel/templates/admin_panel/footer.html` | Footer and legacy/global vendor script loading. |
| Admin AI floating button | `admin_panel/templates/admin_panel/includes/admin_ai_fab.html` | Global AI command entry available from admin pages. |
| Guardian row partial | `admin_panel/templates/admin_panel/includes/admission_guardian_row.html` | Repeatable guardian fields used during admission/enrollment. |
| Automation progress tracker | `edupilot_core/templates/automation/_progress_tracker.html` | Reusable progress display for long-running automation jobs. |
| AI report modal | `admin_ai/templates/admin_ai/includes/auto_report_modal.html` | Reusable automatic report generation modal. |
| Shared announcement feed | `templates/shared/announcements/feed_content.html` | Shared announcement/feed content. |
| Shared help/support layouts | `templates/shared/help_support/` | Report issue, requested reports, suggestion bucket, and support layout partials. |

Current layout flow:

```text
bases.html or base.html
├── shared/header/portal_header.html
├── shared/sidebar/shell.html
│   └── admin_panel/sidebar.html
├── page template content block
├── admin_panel/includes/admin_ai_fab.html
└── admin_panel/footer.html (primary shell)
```

Before redesigning a page, first check which base it extends. The two shells use different content wrappers and load a different set/order of scripts.

## 3. Admin navigation map

The visible sidebar is organized into these groups:

1. **Main:** dashboard.
2. **AI Command Center:** AI overview, copilot, advanced analytics, reports, student intelligence, risk index, and system health.
3. **Academics:** classes, sections, subjects, groups, fixtures, class teachers, duty roster, event duties, timetable report, and academic calendar.
4. **Admissions:** academic years, applications, queries, ID cards, and bulk student upload.
5. **Teachers:** teacher list, teacher creation, and bulk teacher upload.
6. **Timetable:** automation, timetable view, periods, and period assignment.
7. **Examinations:** question banks, exam plans, approval queue, analytics, exam formats, and questions.
8. **People & HR:** HR dashboard, setup lists, employees, payroll automation, payslips, leave, and appraisals.
9. **Communication:** inbox, announcements, and helpdesk.
10. **Finance:** financial ledger, voucher workbench, reports, accounts dashboard, fee automation, voucher management, notifications, fee configuration, student ledgers, and transactions.
11. **Operations:** procurement and transportation.
12. **Reports & Settings:** AI reports, user/role management, automation settings, and admin profile.

## 4. Core dashboard, search and account screens

| Screen/workflow | URL name or path | Template | Backend |
|---|---|---|---|
| Main admin dashboard | `admin_panel_dashboard`, `/admin_panel/` | `admin_panel/index.html` | `admin_panel/views.py` |
| Secondary dashboard | `admin_dashboard`, `/admin_panel/dashboard/` | `admin_panel/index.html` | `admin_panel/views.py` |
| AI analytics overview | `ai_analytics_dashboard` | `admin_panel/ai_analytics.html` | `admin_panel/views.py` |
| Global admin search | `admin_search` | `admin_panel/search_results.html` | `admin_panel/views.py` |
| Search suggestions/data | `admin_search_suggestions` | JSON endpoint | `admin_panel/views.py` |
| Header live data | `admin_header_data` | JSON endpoint | `admin_panel/views.py` |
| Admin profile | `admin_profile` | `admin_panel/admin_profile.html` | `admin_panel/views.py` |
| Users | `user_list` | `admin_panel/user_list.html` | `admin_panel/views.py` |
| User and role workspace | `user_role_management` | `admin_panel/user_role_management.html` | `admin_panel/views.py` |
| Role creation/list/assignment | `create_role`, `list_roles`, `assign_role` | `create_role.html`, `list_roles.html`, `assign_role.html` | `admin_panel/views.py` |

Dashboard-specific frontend files include `admin_panel_dashboard.css`, `admin_panel_dashboard.js`, `live-dashboard.css`, `live-dashboard.js`, `ai-overview.css`, `ai-overview.js`, `ai-graphs.css`, `ai-graphs.js`, `edupilot-charts.css`, and `edupilot-charts.js`.

## 5. Admissions and student administration

| Screen/workflow | Route group | Templates |
|---|---|---|
| Admission registration | `registration` | `registration.html` |
| Admission applications | `admission_list` | `admission_list.html` |
| New student admission workspace | `student_admissions` | `student_admissions.html` |
| Enrollment profile | `admission_enrollment_profile` | `admission_enrollment_profile.html` |
| Approve account credentials | `approve_admission_credentials` | `approve_admission_credentials.html` |
| Reject application | `reject_reason` | `reject_reason.html` |
| Admission query/search | `query` | `query.html` |
| Student ID card list | `student_id_card_list` | `student_id_card_list.html` |
| Individual ID card/print | `generate_id_card` | `id_card.html` |
| Bulk student import | `bulk_upload_students` | `bulk_upload_students.html` |
| Parent list/create/update | legacy or supporting views | `parent_list.html`, `add_parent.html`, `update_parent.html` |

Related request/data endpoints include admission lookups, status changes, voucher retry, student photo upload, and bulk delete. Page styles/scripts include `registration.css`, `admission_list.css`, `student-admissions.css`, `student-admissions.js`, `add_student.css`, `bulk-student-upload.css`, `bulk-student-progress.css`, and `bulk-student-upload.js`.

## 6. Academics setup and scheduling

| Area | Routes | Templates |
|---|---|---|
| Classes | `class_list`, `class_create`, `class_update`, `class_delete`, `class_students` | `class_list.html`, `class_form.html`, `class_confirm_delete.html`, `class_students.html` |
| Academic years | `academic_year_list`, `add_academic_year`, `update_academic_year`, `delete_academic_year` | `academic_year_list.html`, `academic_year_form.html`, `academic_year_confirm_delete.html` |
| Sections | `section_list`, `add_section`, `edit_section`, `delete_section` | `section_list.html`, `add_section.html`, `edit_section.html`, `delete_section.html` |
| Subjects | `subject_list`, `add_subject`, `edit_subject`, `delete_subject` | `subject_list.html`, `subject_form.html`, `subject_confirm_delete.html` |
| Streams | `stream_list`, `add_stream`, `edit_stream`, `delete_stream` | `stream_list.html`, `stream_form.html`, `stream_delete.html` |
| Class groups | `class_group_list`, `add_class_group`, `edit_class_group`, `delete_class_group` | `class_group_list.html`, `add_group.html`, `edit_group.html`, `delete_class_group.html` |
| Class teachers | `class_teacher_list/create/update/delete` | `class_teacher_list.html`, `class_teacher_form.html`, `class_teacher_confirm_delete.html` |
| Periods | `period_list`, `create_period`, `update_period`, `delete_period` | `period_list.html`, `create_period.html`, `update_period.html`, `delete_period.html` |
| Timetable automation | `timetable_automation` | `timetable_automation.html` |
| Timetable view | `timetable_view` | `timetable.html` |
| Period assignment | `assign_period` | `assign_period.html` |
| Fixture management | `manage_fixture` | `manage_fixture.html` |
| Portfolio timetable | `portfolio_timetable` | `portfolio_timetable.html` |
| Timetable PDF/print | `timetable_pdf` | `timetable_pdf.html` |
| Academic calendar | `academic_calendar_page` | `academic_calendar.html` |

Scheduling uses several AJAX endpoints in `admin_panel/urls.py` for subjects, classes, sections, teachers, days, time slots, and assignment deletion. Preserve their element IDs, query parameters, response keys, and event hooks during visual work. Relevant page assets include `academics_gateway.css`, `class_list.css`, `section_list.css`, `subject_list.css`, and `assign_period.js`.

## 7. Teachers, duties and learning content

| Screen/workflow | Route | Template |
|---|---|---|
| Teacher directory | `teacher_list` | `teacher_list.html` |
| Create/edit teacher | `teacher_add`, `teacher_edit` | `teacher_form.html` |
| Teacher profile | `teacher_profile` | `teacher_profile.html` |
| Delete confirmation | `teacher_delete` | `teacher_confirm_delete.html` |
| Bulk teacher import | `bulk_upload_teachers` | `bulk_upload_teachers.html` |
| Teacher duty roster | `teacher_duty_roster` | `teacher_duty_roster.html` |
| Special duty events | `event_list`, `event_detail`, related actions | `duty_event_list.html`, `duty_event_detail.html` |
| Books/resources | `book_list`, `book_detail`, `upload_book` | `book_list.html`, `book_detail.html`, `upload_book.html` |
| Admin assignment view | `admin_view_assignments` | `admin_view_assignments.html` |
| Admin quiz view | `admin_view_quizzes` | `admin_view_quizzes.html` |
| Admin diary view | `admin_view_diaries` | `admin_view_diaries.html` |
| Admin lecture notes | `admin_view_lecture_notes` | `admin_view_lecture_notes.html` |

There are also alternate book templates (`admin_book_*` and `teacher_book*`) in the same template directory. Verify their callers before consolidating them. Teacher UI assets include `teacher_list.css`, `teacher_form.css`, `teacher_form.js`, and `bulk-student-upload.js`-style upload behavior where reused.

## 8. Examinations

The older exam-format workflow remains in `admin_panel`:

- `format_list.html`, `create_format.html`, `edit_format.html`, `format_questions.html`
- `all_questions.html`, `generate_paper_confirm.html`, `generate_question_paper.html`
- routes: `format_list`, `create_format`, `edit_format`, `delete_format`, `format_questions`, `generate_paper_confirm`, `generate_question_paper`, and PDF generation.

The newer examination product is mounted at `/exam/` and its UI is in `exam_system/templates/exam_system/`:

| Feature | Templates |
|---|---|
| Question banks | `question_bank_list.html`, `question_bank_detail.html`, `add_question.html`, `edit_question.html`, `approve_question.html` |
| AI/book/PDF question generation | `ai_generate_questions.html`, `upload_book_for_bank.html`, `generate_from_pdf.html` |
| Exam plans and schedules | `exam_plan_list.html`, `create_exam_plan.html`, `exam_plan_detail.html`, `add_schedule.html` |
| Blueprint/configuration | `create_blueprint.html`, `assessment_component_config.html`, `term_weightage_config.html`, `create_grading_scale.html`, `grading_scale_list.html` |
| Paper generation/approval | `generate_paper.html`, `admin_paper_queue.html`, `paper_approval_detail.html`, `upload_pdf_for_paper.html` |
| Conduct and marking | `exam_conduct_dashboard.html`, `mark_exam_attendance.html`, `answer_sheet_list.html`, `mark_answer_sheet.html` |
| Results and analytics | `compile_results_confirm.html`, `exam_results_list.html`, `analytics_dashboard.html` |

Files ending in `1` or `2` in this module are parallel versions and should be traced before removal or redesign.

## 9. People, HR, payroll and appraisals

| Area | Routes | Templates |
|---|---|---|
| HR dashboard | `hr_dashboard` | `hr_dashboard.html` |
| HR setup workspace | `hr_setup` | `hr_setup.html` |
| Departments | list/create and AJAX delete | `department_list.html`, `department_form.html` |
| Designations | list/create and AJAX delete | `designation_list.html`, `designation_form.html` |
| Staff categories | list/create | `staff_category_list.html`, `staff_category_form.html` |
| Job types | list/create/edit | `job_type_list.html`, `job_type_form.html` |
| Employees | list/create/edit/profile | `employee_list.html`, `employee_form.html`, `employee_profile.html` |
| Bulk employee import | supporting/alternate bulk workflow | `bulk_upload_employees.html` |
| Employee profile PDF | `employee_profile_pdf` | Generated report response |
| Leaves | list/apply/edit/delete/action | `leave_list.html`, `leave_form.html` |
| Leave types | list/create/edit/delete/toggle | `leave_type_list.html`, `leave_type_form.html` |
| KPI builder | `admin_kpi_builder` | `appraisal_admin_kpis.html` |
| Appraisal submissions | `admin_appraisal_list`, `admin_appraisal_detail` | `appraisal_admin_list.html`, `appraisal_admin_detail.html` |

HR pages share `hr_admin.css`. Salary automation and payslip management are owned by the automation module, documented in section 12.

## 10. Communication, announcements and helpdesk

| Screen/workflow | URL prefix | Template/location |
|---|---|---|
| Inbox and conversations | `/communication/` | `communication/templates/communication/inbox.html` |
| Announcement center | `/admin_panel/announcements/` | `admin_panel/announcement_center.html` |
| Admin/staff helpdesk dashboard | `/helpdesk/staff/` | `helpdesk/staff_dashboard.html` |
| Staff ticket detail and actions | `/helpdesk/staff/tickets/<id>/` | `helpdesk/staff_ticket_detail.html` |
| Portal ticket list/detail/create | `/helpdesk/` | `portal_dashboard.html`, `ticket_detail.html`, `ticket_form.html` |

Announcement assets are `announcement-center.css` and `announcement-center.js`. Helpdesk uses `helpdesk/templates/helpdesk/staff_base.html` plus portal/theme CSS such as `help-support-layout-fix.css` and shared help/support partials. Communication endpoints also provide direct/group conversation creation, message pagination, live updates, actions, and presence.

## 11. Finance and accounts

The accounting UI is mounted at `/finance/` and owned by `finance/urls.py`, `finance/views.py`, and `finance/templates/finance/`.

| Screen/workflow | Route | Template |
|---|---|---|
| Finance dashboard / General Ledger overview | `finance:dashboard` | `finance/dashboard.html` |
| Chart of Accounts and setup | `finance:setup` | `finance/setup.html` |
| Voucher workbench | `finance:voucher_list` | `finance/voucher_list.html` |
| Voucher create | `finance:voucher_create` | `finance/voucher_form.html` |
| Voucher detail, workflow and reversal | `finance:voucher_detail`, `finance:voucher_action` | `finance/voucher_detail.html` |
| Financial statements/reports | `finance:reports` | `finance/reports.html` |
| Audit trail | `finance:audit` | `finance/audit.html` |
| Cash sessions, budgets and bank reconciliation | finance operation routes | `finance/operations.html` |
| Bank statement detail/matching | `finance:bank_statement_detail` | `finance/bank_statement_detail.html` |
| Finance requests | `finance:request_list`, actions | `finance/request_list.html` |
| User-side request form | `finance:portal_request` | `finance/request_form.html` |
| Role-aware finance portal | `finance:portal` | `finance/portal.html` |

The shared finance layout is `finance/templates/finance/base.html`. Download endpoints generate fee invoices, receipts, and payslips. Related account/fee screens exposed through automation are listed next.

## 12. Automation, fee management and payroll

The automation application is mounted at `/automation/` and owned by `edupilot_core/urls.py`.

| Screen/workflow | Route | Template |
|---|---|---|
| Accounts/automation dashboard | `automation-dashboard` | `automation/dashboard.html` |
| Fee automation | `fee-automation` | `automation/fee.html` |
| Voucher management | `voucher-management` | `automation/vouchers.html` |
| Notification queue | `notification-queue` | `automation/notifications.html` |
| Salary automation | `salary-automation` | `automation/salary.html` |
| Payslip management | `payslip-management` | `automation/vouchers.html` or configured automation view template |
| Automation logs | `automation-logs` | `automation/logs.html` |
| Automation settings | `automation-settings` | `automation/settings.html` |
| Configurable data CRUD | `crud-list/create/update/delete` | `crud_list.html`, `crud_form.html`, `crud_delete_confirm.html` |
| Announcement feed | `automation-announcements` | `announcements_feed.html` |

The module shell is `edupilot_core/templates/automation/base_automation.html`; its local menu is `automation/sidebar.html`. Progress and dashboard assets include `automation-progress.css`, `automation-progress.js`, and `_progress_tracker.html`.

## 13. Procurement and transportation

Both modules reuse three generic templates in `admin_panel/templates/admin_panel/`:

- `operations_dashboard.html` for overview metrics and charts.
- `operations_list.html` for searchable tables.
- `operations_form.html` and `operations_confirm_delete.html` for create/edit/delete flows.

| Module | Screens/routes |
|---|---|
| Procurement | Dashboard; categories; vendors; purchase requests; inventory items; stock movements; add/edit/delete screens for each entity. |
| Transportation | Dashboard; vehicles; routes; transport assignments; trips; maintenance records; add/edit/delete screens for each entity. |

Routes are under `/admin_panel/operations/procurement/` and `/admin_panel/operations/transportation/`. Their presentation is primarily controlled by `operations_admin.css` and `operations-dashboard.js`.

## 14. AI Command Center

Admin AI routes are included directly inside `/admin_panel/` through `admin_panel/urls.py`.

| Screen/workflow | Route | Template |
|---|---|---|
| AI Copilot | `admin_ai_copilot` | `admin_ai/copilot.html` |
| Advanced analytics | `ai_analytics_advanced` | `admin_ai/advanced_analytics.html` |
| AI reports | `ai_analytics_reports` | `admin_ai/reports.html` |
| Report detail/export/share | report UUID routes | `admin_ai/report_detail.html` plus generated PDF/Excel responses |
| Student intelligence list | `admin_ai_student_intelligence` | `admin_ai/student_intelligence.html` |
| Student intelligence detail | `admin_ai_student_intelligence_detail` | `admin_ai/student_intelligence_detail.html` |

Message, chart-data, report generation, export, and share routes are supporting endpoints and must keep their current JSON/form contracts when visuals are changed.

## 15. Complete admin template file index

This index prevents smaller or supporting screens from being missed. All paths below are relative to `admin_panel/templates/admin_panel/`.

### Shell, dashboard and shared

`base.html`, `bases.html`, `header.html`, `footer.html`, `sidebar.html`, `index.html`, `admin_panel_dashboard.html`, `admin_panel_dashboard1.html`, `admin_panel_home.html`, `admin_profile.html`, `search_results.html`, `ai_analytics.html`, `includes/admin_ai_fab.html`, `includes/admission_guardian_row.html`.

### Admissions, students, parents and users

`registration.html`, `admission_list.html`, `student_admissions.html`, `admission_enrollment_profile.html`, `approve_admission_credentials.html`, `reject_reason.html`, `query.html`, `student_id_card_list.html`, `id_card.html`, `bulk_upload_students.html`, `add_student.html`, `upload_result.html`, `parent_list.html`, `add_parent.html`, `update_parent.html`, `user_list.html`, `create_user.html`, `create_admin_user.html`, `user_role_management.html`, `create_role.html`, `list_roles.html`, `role_list.html`, `assign_role.html`, `create_permission.html`, `permission_list.html`, `manage_permissions.html`.

### Academics and scheduling

`academic_year_list.html`, `academic_year_form.html`, `academic_year_confirm_delete.html`, `class_list.html`, `class_form.html`, `class_confirm_delete.html`, `class_students.html`, `section_list.html`, `add_section.html`, `edit_section.html`, `delete_section.html`, `subject_list.html`, `subject_form.html`, `subject_confirm_delete.html`, `stream_list.html`, `stream_form.html`, `stream_delete.html`, `class_group_list.html`, `add_group.html`, `edit_group.html`, `delete_class_group.html`, `class_teacher_list.html`, `class_teacher_form.html`, `class_teacher_confirm_delete.html`, `period_list.html`, `create_period.html`, `update_period.html`, `delete_period.html`, `timetable.html`, `timetable_automation.html`, `assign_period.html`, `manage_fixture.html`, `portfolio_timetable.html`, `timetable_pdf.html`, `academic_calendar.html`.

### Teachers, resources and LMS review

`teacher_list.html`, `teacher_form.html`, `teacher_profile.html`, `teacher_confirm_delete.html`, `bulk_upload_teachers.html`, `teacher_duty_roster.html`, `select_teacher.html`, `duty_event_list.html`, `duty_event_detail.html`, `book_list.html`, `book_detail.html`, `upload_book.html`, `admin_books_list.html`, `admin_book_detail.html`, `admin_book_upload.html`, `teacher_books_list.html`, `teacher_book_detail.html`, `admin_view_assignments.html`, `admin_view_quizzes.html`, `admin_view_diaries.html`, `admin_view_lecture_notes.html`.

### Exams

`format_list.html`, `create_format.html`, `edit_format.html`, `format_questions.html`, `all_questions.html`, `generate_paper_confirm.html`, `generate_question_paper.html`.

### HR and appraisals

`hr_dashboard.html`, `hr_setup.html`, `department_list.html`, `department_form.html`, `designation_list.html`, `designation_form.html`, `staff_category_list.html`, `staff_category_form.html`, `job_type_list.html`, `job_type_form.html`, `employee_list.html`, `employee_form.html`, `employee_profile.html`, `bulk_upload_employees.html`, `leave_list.html`, `leave_form.html`, `leave_type_list.html`, `leave_type_form.html`, `appraisal_admin_kpis.html`, `appraisal_admin_kpis1.html`, `appraisal_admin_list.html`, `appraisal_admin_detail.html`.

### Communication and operations

`announcement_center.html`, `operations_dashboard.html`, `operations_list.html`, `operations_form.html`, `operations_confirm_delete.html`.

### Miscellaneous or needs caller verification

`admin_panel_dashboard1.html`, `appraisal_admin_kpis1.html`, `your_template.html`, and some parallel book templates appear to be alternate or historical versions. They are part of the inventory, but their active callers must be verified before editing or deleting them.

## 16. CSS inventory

All paths are relative to `admin_panel/static/admin_panel/css/`.

| Layer | Files |
|---|---|
| Global shell/theme | `style.css`, `base.css`, `admin-inner-theme.css`, `reference-sidebar.css`, `deznav-sidebar.css`, `portal-header.css` |
| Shared design primitives | `edupilot-buttons.css`, `edupilot-surfaces.css`, `edupilot-contrast-fix.css` |
| Dashboard/data visualization | `admin_panel_dashboard.css`, `admin_panel_home.css`, `live-dashboard.css`, `edupilot-charts.css`, `ai-overview.css`, `ai-graphs.css`, `ai-admin-design.css` |
| Admissions/people | `registration.css`, `admission_list.css`, `student-admissions.css`, `student_gateway.css`, `add_student.css`, `parent_list.css`, `add_teacher.css`, `teacher_form.css`, `teacher_list.css`, `update_parent.css`, `update_student.css`, `update_teacher.css` |
| Academics | `academics_gateway.css`, `class_list.css`, `section_list.css`, `subject_list.css`, `add_student.css`, `add_teacher.css`, `delete_section.css`, `edit_section.css` |
| Feature modules | `hr_admin.css`, `lms_admin.css`, `operations_admin.css`, `announcement-center.css`, `automation-progress.css`, `bulk-student-upload.css`, `bulk-student-progress.css`, `portal-vouchers.css`, `query.css` |
| Support/help | `help-support-layout-fix.css`, `parent-help-support.css` |

Several pages also contain inline `<style>` blocks. During modernization, move repeated rules into the shared component/theme layer only after checking selector specificity and template dependencies.

## 17. JavaScript inventory

All paths are relative to `admin_panel/static/admin_panel/js/`.

| Layer | Files |
|---|---|
| Shell/header/sidebar | `base.js`, `admin-header-live.js`, `portal-header.js`, `deznav-sidebar.js`, `deznav-init.js`, `custom.min.js` |
| Dashboard/charts | `admin_panel_dashboard.js`, `live-dashboard.js`, `edupilot-charts.js`, `ai-overview.js`, `ai-graphs.js`, `legacy-dashboard-charts.js`, `dashboard/dashboard-1.js`, `dashboard/profile.js`, `dashboard/statistics.js` |
| Page workflows | `student-admissions.js`, `bulk-student-upload.js`, `teacher_form.js`, `assign_period.js`, `announcement-center.js`, `automation-progress.js`, `operations-dashboard.js`, `portal-vouchers.js`, `add_parent.js` |
| Theme/demo | `demo.js`, `styleSwitcher.js` |
| Plugin initialization | `plugins-init/` contains setup scripts for DataTables, Select2, charts, calendars, pickers, validation, maps, notifications, and other vendor widgets. |

The complete plugin initializer list is: `bs-daterange-picker-init.js`, `chartist-init.js`, `chartjs-init.js`, `clock-picker-init.js`, `datatables.init.js`, `flot-init.js`, `fullcalendar-init.js`, `jquery-asColorPicker.init.js`, `jquery.validate-init.js`, `jqvmap-init.js`, `material-date-picker-init.js`, `morris-init.js`, `nestable-init.js`, `nouislider-init.js`, `pickadate-init.js`, `piety-init.js`, `select2-init.js`, `sparkline-init.js`, `sweetalert.init.js`, `toastr-init.js`, and `widgets-script-init.js`.

Do not rename or remove DOM IDs, `data-*` attributes, CSS state classes, form field names, or URL values used by these scripts until all references have been traced with `rg`.

## 18. Third-party UI dependencies

The local vendor directory is `admin_panel/static/admin_panel/vendor/`. It includes Bootstrap-related components, Bootstrap Select, Chart.js, Chartist, ApexCharts, DataTables, Dropzone, FullCalendar, CKEditor, SweetAlert2, Toastr, Select2, Owl Carousel, Perfect Scrollbar, jQuery UI/validation, date/time pickers, Peity, Morris, and Flot. The current footer also loads jQuery and Select2 from CDNs.

Any professional redesign should first decide which vendor stack remains canonical. Loading duplicate versions can change spacing, colors, focus states, component behavior, and JavaScript initialization order.

## 19. Reusable UI patterns to standardize

These patterns already exist across the portal and should become shared, consistent components:

- Page header: title, breadcrumb, description, and primary action.
- Metric cards: icon, label, value, trend, and drill-down action.
- Content cards/panels: header, body, footer, loading, empty, and error states.
- Data tables: search, filters, sorting, pagination, bulk selection, row actions, and responsive layout.
- Forms: labels, help text, required/error states, grouped fields, Select2 inputs, date fields, and action footer.
- Status display: badges for draft, pending, approved, rejected, paid, overdue, active, and inactive.
- Feedback: toast, inline alert, modal confirmation, progress tracker, and validation message.
- Navigation: header, sidebar group, active item, collapsed state, mobile drawer, profile menu, and notifications.
- Charts: title, legend, timeframe/filter, empty state, tooltip, and accessible data summary.
- Uploads: drag/drop area, template download, validation preview, progress, result summary, and error export.
- Record detail: summary header, tabs, key/value data, timeline/audit trail, attachments, and actions.
- Print/PDF: ID cards, timetables, employee profiles, reports, receipts, payslips, and exam papers.

## 20. UI modernization guardrails

The UI can be redesigned safely if these contracts remain unchanged:

1. Keep URL patterns and URL names stable.
2. Keep permissions, role checks, and object-level access rules intact.
3. Keep form field names, formsets, management fields, CSRF tokens, and POST action values intact.
4. Keep AJAX endpoint payloads, response keys, query parameters, and status handling intact.
5. Keep JavaScript selectors and `data-*` hooks intact until callers are updated together.
6. Keep pagination, filters, exports, uploads, approval actions, and download flows working.
7. Keep printable/PDF templates separate from responsive application screens where required.
8. Test desktop, tablet, and mobile widths plus keyboard focus, contrast, empty, loading, validation, and error states.

## 21. Current UI risks and cleanup candidates

- Two admin base templates create different wrappers and dependency orders.
- Global styling is split across `style.css`, `base.css`, `admin-inner-theme.css`, `reference-sidebar.css`, `edupilot-surfaces.css`, and page-specific overrides.
- The footer closes shell markup and also owns global scripts, which makes page structure harder to reason about.
- Both local and CDN copies of some libraries are loaded.
- `legacy-dashboard-charts.js` and numbered templates indicate parallel implementations that need caller verification.
- Feature UIs live across multiple Django apps, so changing only `admin_panel/templates` will not fully modernize the admin experience.
- Inline styles and page-specific selectors can override shared tokens unexpectedly.

These are documentation findings only; this inventory does not change current UI or functionality.

## 22. Recommended implementation order for a professional UI

1. Define visual tokens: color, typography, spacing, radius, shadow, icon size, breakpoints, and motion.
2. Consolidate the admin shell while maintaining compatibility with both content wrapper styles.
3. Standardize shared buttons, inputs, cards, badges, tables, modals, alerts, loading states, and empty states.
4. Modernize the dashboard, header, sidebar, search, profile, and responsive navigation.
5. Apply the shared components to list and CRUD screens module by module.
6. Modernize complex workflows: admissions, timetable, exams, HR, finance, automation, helpdesk, and operations.
7. Verify role permissions, JavaScript behavior, responsive layouts, accessibility, print/PDF output, and regression-sensitive workflows.

This order gives the admin portal one professional design language while preserving its working backend and user flows.
