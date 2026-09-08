# EduPilot implementation checkpoint — 8 September 2026

The specification is **not fully implemented or production-verified**. This checkpoint distinguishes implemented work from remaining requirements.

## Confirmed decisions

- One institution with multiple campuses.
- Preserve existing screens and styles; matching controls may be added for missing workflows.
- Campus names and existing-record mapping remain pending. Do not infer them from class or department names.
- Payment gateway selection and credentials remain pending; demo payments are blocked by default.

## Implemented foundations

- Institution/campus scope registry, explicit role grants, independently approved assignments, assignment expiry and primary role selection.
- Permission evaluation ties each allowed action to the same assignment's scope; no superuser bypass in this policy service.
- Session invalidation after access changes, portal boundaries, verified guardian access and voucher recipient rechecks.
- Versioned independent approval service and payment receipt idempotency/balance checks.
- Paper reviewer assignments, stage order, locking and human-mark requirements.
- Academic-year archival and procurement approval checks.

## New workspace

URL: `/access/workspace/`. Scoped operations users can enter through the existing Admin login page and are directed here.

- Scoped library catalog and loans: create inventory, issue available copies, return books.
- Laboratory equipment and bookings: request, independent approval/rejection, overlap prevention, requester cancellation before start.
- Confidential cases: encrypted notes, verified authenticator and assigned worker required, case closure.
- Approval review controls and authenticator enrollment/verification.
- Templates reuse existing styles and sidebar/header components. Security Center and the role permission matrix were visually verified in an isolated local browser database.

## Integrated administration UI

Access setup no longer depends on Django's technical admin for daily work. The existing EduPilot sidebar now includes **Access & Security** for Super Admin, with custom screens for institutions, campuses, accounts, role permission matrices, assignments, independent approval/revocation, student-campus mapping, generic record ownership, workflow approvals, verified payment receipts, authenticator status/revocation, and the read-only audit log. The older EduPilot role-management URLs now open these scoped screens. Standard role templates can also be created from Security Center without a command.

The same sidebar includes Campus Services links for library, loans, laboratory, bookings and health cases. Scoped staff continue to use their restricted workspace.

## Local setup

Pending migrations were applied to the configured local database on 8 September. A field-encryption key was initialized in the ignored `.env` file without displaying it. Preserve that key securely; changing or losing it prevents decryption of existing authenticator secrets and clinical notes. Restart any already-running Django process to load it.

Database inspection found zero institutions, zero campuses and zero mapped student records. No institution names, assignments or student mappings were invented.

Using Windows CMD:

```bat
cd /d D:\edu-work
set DJANGO_DEBUG=true
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000/`. PostgreSQL must be running with the project's configured connection. For a fresh environment, install `requirements.txt`; the newly used encryption dependency is included there.

After the actual institution/campuses are configured, seed conservative role templates with:

```bat
python manage.py seed_access_roles --institution INSTITUTION_ID
```

Replace `INSTITUTION_ID` with the actual database ID. Seeding does not assign user access. Existing role MFA preferences are preserved; review them explicitly. Student ownership and independently approved campus assignments are required before scoped workflows can operate on real data.

## Validation and limits

- Combined regression run passed 63 tests before the final cancellation/closure and additional endpoint cases.
- The subsequent seven-test operations suite passed, including cancellation, case closure, forged campus submissions, session revocation and cross-campus record identifiers.
- Django migration consistency check: no changes detected.
- Tests use isolated SQLite and in-memory email/storage; installed Django is 6.0.6, while requirements currently pin 5.2.3. This is not verification of the pinned dependency environment or PostgreSQL concurrency behavior.
- Existing local warning: configured `D:\edu-work\static` directory does not exist.

## Remaining specification work

Campus scoping is not yet enforced across every legacy endpoint. Further work includes domain-specific approval execution and publication flows, finance gateway/refunds and period controls, payroll approvals, admissions review, full library reservations/fines, laboratory incidents, clinical updates/referrals/break-glass access, support access lifecycle, MFA recovery and broader enforcement, academic rollover, access reviews, AI evidence rules, audit retention/storage hardening, and end-to-end browser/deployment testing.

Do not label the project “100% complete” based on the foundation and regression tests alone. Preserve unrelated concurrent workspace edits, including bulk import and existing student/dashboard changes.
