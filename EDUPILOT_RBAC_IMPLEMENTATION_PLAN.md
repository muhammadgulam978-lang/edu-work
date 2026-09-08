# EduPilot role based access and workflow implementation plan

Prepared 7 September 2026 from `EduPilot_Role_Based_Access_and_Workflow_Design.docx` and the current `D:\edu-work` source tree.

## Objective and change boundary

Implement the specification as working, persistent, server-enforced authorization and approval workflows while preserving the existing UI and unrelated behavior. This deliverable is a plan only; it does not implement application changes.

The attached document supplies product requirements. Its delivery instructions and release recommendations are reference material, not authorization to deploy, redesign screens, contact users, or change unrelated modules.

- Preserve existing layouts, CSS, typography, colors, charts, page structure, URL names, form contracts, and responsive behavior.
- Reuse existing screens and services. Correct role labels and permission-dependent data/actions through existing bindings. These intended access changes must be documented in the acceptance baseline.
- Keep calculations and valid existing business outcomes unchanged unless a specific requirement requires approval, locking, privacy, or scope restrictions.
- Do not refactor unrelated code, replace the authentication user model, edit collected `staticfiles/`, rewrite historical migrations, or alter existing uncommitted work.
- If a required user interaction has no existing control, record it as an explicit UI dependency. A backend API alone does not count as a complete user workflow. Under a literal zero-UI-change constraint, those requirements remain blocked until an acceptable existing control is identified or a narrow exception is agreed.

## Verified starting point

These are source observations, not a production runtime audit. The finance exception reported in the document has not been reproduced.

| Area | Current evidence | Implementation implication |
| --- | --- | --- |
| Identity | `login/views.py` routes four portal groups; `admin_panel/models.py` has a single-role `UserRole`; role views and context processors use separate role/profile rules | Establish one effective-role resolver and scoped multiple assignments; preserve portal entry points |
| Authorization | `admin_panel/decorators.py` bypasses checks for superusers; default Admin setup grants all Django permissions | Distinguish institution roles from technical superuser privilege and enforce domain restrictions |
| Academic setup | `AcademicYear` already exists with `year` and `is_active`; list/add/update/delete routes exist | Extend lifecycle and rollover; do not build a duplicate subsystem |
| Family links | `Parent.students` and `StudentGuardian` both exist; parent and communication queries use the older relationship | Reconcile into one authoritative access rule, including revocation and verification |
| Teacher scope | `ClassTeacher`, subject relationships, and timetable assignments exist | Reuse actual year/class/section/subject assignment records |
| Exams | `GeneratedPaper`, staged `PaperApproval`, and `PaperAccessLog` exist | Extend and enforce existing workflow rather than replace it |
| Finance | Active `/automation/` routes use `edupilot_core`; a `DummyPaymentService` exists | Trace active callers, retain calculations, and prevent simulation from confirming real payments |
| Data ownership | Student, teacher, and finance model families are duplicated | Use canonical portal models and existing `canonical_sync`; never infer ownership from class name alone |
| Isolation | No tenant/campus/institution fields were found in the searched active model files | Add explicit ownership and validated migration mapping before claiming tenant isolation |
| Error handling | `sms/settings.py` sets `DEBUG = True` | Separate production error behavior from local development |

## 1 Baseline and requirement inventory

1. Record the working-tree baseline, existing test failures, route inventory, and template resolution. Preserve current local edits in student views/tests and admin/student templates.
2. Map every specification section to an existing endpoint/service/model, required extension, test, and completion status. Include library, lab, health, platform support, and operational modules even where implementation is absent.
3. Inventory HTML, JSON, exports, print/download routes, Django admin, WebSockets, scheduled jobs, notifications, search, and AI tool entry points. Each needs an explicit action and scope policy.
4. Capture screenshots and business outputs for representative authorized users before implementation. Use a test database with two institutions, multiple campuses, overlapping class names, multiple roles, two families, and expired assignments.
5. Reproduce the reported finance error with controlled fixtures and protected logs before selecting its fix.

Exit: a complete route-to-policy inventory and baseline that distinguish pre-existing defects from new regressions.

## 2 Shared authorization foundation

Add a small dedicated Django app, proposed name `access_control`, without replacing `auth.User` or domain apps.

Proposed records:

- Institution and Campus; user access profile with account status, assurance/MFA state, and authorization version.
- RoleDefinition linked to existing Groups where useful; PermissionDefinition with resource/action/sensitivity; role grants and explicit denies.
- RoleAssignment with institution, role, start/end, grantor, approval state, and permitted scopes. Keep role and scope paired so one role's permission cannot combine with another role's broader scope.
- Explicit scope relationships for campus, department, academic year, class, section, subject, self, linked child, and assigned workflow. Validate foreign-key ownership consistently.
- Access requests/reviews, expiring support grants, and durable audit events.

Use one policy service for action decisions and scoped querysets. Require active account, active approved assignment, permitted action, matching scope, valid workflow state, and applicable time/device/MFA conditions. Missing context fails closed. Explicit restrictions and segregation of duties remain effective even when a person holds several roles.

Define actions separately: view, create, edit, submit, review, approve, publish, export, soft-delete, configure. Use fully qualified permission names rather than ambiguous cross-app codenames.

Seed all 20 detailed roles in section 4. Add explicit restricted definitions for Support Engineer and Reception, which appear elsewhere without full role specifications, and an Admission Committee reviewer assignment. Undefined powers stay denied. Resolve matrix ambiguities using the more restrictive detailed rule: a broad Health read cell cannot grant access to clinical notes, and broad finance access cannot permit self-approval.

Institution Super Admin must not inherit unrestricted technical superuser access. Platform administrators get technical metadata by default; school-content access requires a tenant-approved, scoped, expiring support grant. Map existing administrators through a reviewed migration; do not silently grant every legacy administrator institution-wide powers.

Exit: policy tests prove action, scope, multi-role behavior, explicit restrictions, and cross-institution denial independently of page visibility.

## 3 Safe ownership and relationship migration

Use additive migrations: add ownership links, backfill, validate, then enforce non-null and uniqueness constraints. Create an initial institution/campus only after confirming the existing dataset's ownership. Quarantine ambiguous records for reconciliation; never interpret missing ownership as global access.

Preserve IDs, historical records, balances, voucher references, canonical mappings, and parent/teacher relationships. Update uniqueness rules where names currently assume one institution. Add indexes for scoped list queries and validate cross-institution foreign keys on writes and bulk operations.

Make verified, active `StudentGuardian` authority the access source. Reconcile the old many-to-many relation without treating every old link as newly verified. Maintain compatibility reads only when they cannot restore revoked access. Store relationship dates, verification, consent, invitation status, and access revocation.

Add academic-year states and dates for draft, active, closed, archived; define the activation boundary and uniqueness constraint. Rollover is previewed and idempotent, preserves history, and explicitly maps promotions, repeats, sections, and teaching assignments. Closed-year changes require a documented controlled exception.

Exit: migration rehearsal reconciles row counts, financial totals, ownership, and relationship access with no lost history.

## 4 Identity and enforcement integration

Integrate the shared resolver into `login/views.py`, role management in `admin_panel/views.py`, context processors, and existing header/sidebar bindings. Separate profile type from effective authorization role. Conflicting claims block access with an audit event; they must not produce a guessed Student/Admin label.

Check authorization before queryset serialization, aggregation, object lookup, mutation, download, and export. Constrain submitted related IDs as well as the top-level record. Return 403 for denied actions and 404 where revealing existence would leak information. Apply field masking before data enters templates, JSON, logs, AI prompts, or exports.

Cover both teacher URL mounts, `/admin/`, generic automation CRUD, communication consumers, voucher delivery, files under media storage, and background tasks. Sensitive files require authenticated delivery or short-lived scoped links; protecting the page alone is insufficient. Workers recheck the originating actor or narrowly scoped service identity when executing queued work.

Increment authorization versions on suspension, role/scope/guardian changes, and expiry. Revalidate on requests and WebSocket events, revoke sessions/tokens where used, and close affected live subscriptions. Cache keys include institution, effective assignment, authorization version, and relevant scope.

Preserve current portal designs. Teacher access follows actual assignment; student data is self-only and publication-aware; parent data follows verified child links. Reuse the existing parent selector while validating its identifier server-side. Replace broad staff communication shortcuts with scoped recipient policies.

Exit: direct URLs, APIs, alternate mounts, exports, caches, files, and live channels obey the same rules immediately after revocation.

## 5 Controlled workflows

Provide shared approval infrastructure with domain-specific transition rules. Persist maker, assigned reviewers, stage, version, reasons, timestamps, and decision history. Use database transactions and row locking to prevent concurrent approval, duplicate execution, and stale decisions. Any material edit invalidates the approvals tied to the previous version. Prevent self-approval by user identity across all roles and delegated sessions.

| Workflow | Required implementation and completion test |
| --- | --- |
| Admissions | Extend `admin_panel/admission_services.py`: document verification, deterministic eligibility, exception/committee decision, human-verified subjective scores, approved offer/voucher, verified payment, enrollment/account handoff, guardian invitation. Retry cannot duplicate enrollment or accounts |
| Academic delivery | Approved curriculum/calendar, teacher-owned drafts, optional policy-based HOD review, assignment delivery, student submission, teacher feedback, controlled publication. AI early-warning recommendations remain pending human validation |
| Examination papers | Extend `exam_system/models.py`, services/views and teacher exam entry points: draft → AI advisory review → coordinator review → HOD approval → controller verification → locked → authorized print/publication → archive. Revisions return for review; deadlines, assignment and access windows are enforced |
| Results | Teacher marks → moderation/review → lock → authorized result-release approval → controller publication. Post-lock corrections preserve original values, reason and independent approval; students/parents never receive draft results |
| Fees | Approved fee structure and open period → idempotent voucher generation → verified receipt. Refund/concession/reversal/write-off requires a separate approver and reason. Period reopening requires senior approval |
| Payroll | Approved HR inputs → payroll preparation → independent verification/approval → payslip publication. Preserve existing calculations and restrict payslips to the employee; retain before/after adjustment evidence |
| Procurement | Request → independent approval → confidential quotations/evaluation → approved vendor/PO → receipt → invoice/order/receipt match. Enforce conflicts, sealed-bid timing and no self-approval |
| Library | Scoped identity/eligibility lookup, catalog/copies, issue/return/reservation, condition/fines and overdue delivery; no unrelated academic, health or finance access |
| Laboratory | Assigned-lab inventory, consumables, bookings, safety checks/incidents and controlled practical evidence; restrict student lookup and incident escalation |
| Health/counselling | Case-based access, consent, encrypted confidential fields, controlled referral and restricted alerts; audited emergency access requires reason and expiry |
| Transport | Extend existing fleet/routes/trips: assigned rider lists, stops, attendance/incidents, guardian verification, parent alerts and location retention; expose only emergency health indicators |

Treat absent library/lab/health or support functionality as genuine implementation work, not complete merely because a permission exists. Each workflow must have a usable path through existing controls; list missing interactions before claiming end-to-end completion.

For payments, preserve calculation rules while adding verified gateway signatures, amount/currency/account checks, replay protection, unique transaction references, cumulative partial-payment handling and atomic ledger posting. Test duplicate and concurrent callbacks. Gateway selection and credentials are deployment dependencies, not facts established by this review.

For paper release, use encrypted private storage, watermarked exports, expiring/redeem-once print jobs, authorized copy counts and reconciliation. A browser cannot guarantee physical copy control or device binding by itself; the required print-device integration must be specified and tested.

Exit: every workflow succeeds with persisted records, rejects illegal transitions and self-approval, and remains correct under retries and concurrency.

## 6 Account lifecycle audit and AI controls

Implement request, owner approval, second approval for privileged grants, unique-account provisioning, verified activation, initial password change, required MFA, periodic certification, transfer, suspension and closure. Preserve records on closure while revoking access and reassigning owned work. Use existing screens where possible; MFA enrollment, role switching, support-session recording and approval-history interactions need explicit UI/integration coverage.

Audit sensitive reads, denied requests, exports, mutations, approvals/rejections, role changes and high-impact AI decisions. Store actor, effective assignment, institution/scope, resource, time, IP/device, outcome, correlation ID and before/after evidence. Avoid logging raw secrets or unnecessary health data. Application-level append-only code is insufficient for immutability: enforce restricted database credentials and export to protected immutable retention storage with integrity verification. Audit failure must not silently allow a sensitive operation.

Extend `admin_ai` and `ai_tutor` at their service/tool boundaries. Scope retrieval before prompting and recheck policy before any side effect. Store model, prompt-template version, approved sources, output, reviewer, edits, decision, timestamp, cost and final outcome for high-impact interactions. Pending AI recommendations cannot finalize marks, admissions, appraisals, risk flags, payroll or permissions. External delivery requires the prescribed human authorization; preserve authorized existing notification workflows.

Apply communication recipient preview/approval where required, attachment moderation, quiet hours, restricted health channels, reporting/blocking and per-recipient privacy. Recheck guardian authority before voucher/reminder delivery, including queued messages.

Exit: no AI or automation bypasses authorization, approval, sensitive-data boundaries or audit requirements.

## 7 Verification and rollout

Run focused tests during each increment and the relevant existing suite before release. Use isolated test data; planning does not require executing production jobs or sending messages.

- Policy matrix: positive and negative cases for every role/action/scope, including privileged roles, conflicting claims, expired assignments and maker-checker conflicts.
- Isolation: two institutions/campuses and object-ID swapping across list/detail/search/export/download/cache/WebSocket/API paths; reject foreign related IDs and mass-assignment privilege changes.
- Community: teacher assignment changes, removed guardian links, multiple children, student self-only access, published-only results and appropriately scoped vouchers/messages.
- Transactions: repeated/concurrent payments, voucher generation, imports, approvals, payroll and enrollment; no duplicate posting or unauthorized state transition.
- Sensitive operations: sealed-paper stage/window, print-token replay, salary masking, confidential notes, support expiry and AI side-effect attempts.
- Compatibility: existing admissions, attendance, assignments, quizzes, timetables, dashboards, canonical synchronization, voucher/email delivery and exam analytics tests. Compare authorized-user business outputs against baseline.
- UI: compare screenshots at existing desktop/mobile sizes, plus keyboard behavior and validation. Expected changes are limited to approved role/data/action visibility and accurate labels; no layout/style regression.
- Production safety: reproduce/fix the finance error; verify generic error responses with production settings, protected logs, MFA/provider integrations, audit storage and backup restoration.

Roll out in dependency order: baseline → authorization/ownership → identity/setup/community → controlled operations → AI/integrations → assurance. Use isolated staging and a pilot institution. Shadow comparisons may identify compatibility gaps on existing paths, but newly protected or unresolved cross-tenant paths must fail closed. Do not add a production flag that restores unrestricted access.

Take a recoverable database snapshot before migration. Keep migrations additive and rehearse restore. If rollout fails, restrict the affected capability and roll back to a compatible secure build; do not reverse schema over newly written data or re-enable a known authorization bypass.

Release requires all specification acceptance/UAT cases, complete user workflows, no unauthorized data exposure, unchanged unrelated business results/UI, migration reconciliation, and operational sign-off. Track infrastructure and missing-control dependencies explicitly rather than marking backend-only features complete.

## First implementation increment

Start with the route/permission inventory, effective-role resolver, identity reconciliation report, authorization tests, production error handling and a reproducible finance-error test. Then add scoped assignments and ownership migrations before expanding role templates and workflows. This provides a reviewable foundation without mixing UI redesign or unrelated fixes into the work.

## Dependencies to settle during implementation

Confirm real institution/campus ownership of legacy data, final role owners and approvers, exceptional-admission rules, closure/rollover policy, retention periods, permitted time/device policies, and infrastructure for MFA, payment verification, immutable audit storage and secure printing. Resolve multi-role selection and missing workflow controls against the zero-UI-change boundary. These do not block preparing this plan, but they do gate the affected production capabilities.
