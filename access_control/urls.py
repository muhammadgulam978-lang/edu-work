from django.urls import path
from . import views
from . import workspace
from . import management_views as management

urlpatterns = [
    path('manage/', management.security_center, name='access_security_center'),
    path('manage/institutions/', management.institutions, name='access_institutions'),
    path('manage/institutions/add/', management.institution_add, name='access_institution_add'),
    path('manage/institutions/<int:pk>/edit/', management.institution_edit, name='access_institution_edit'),
    path('manage/campuses/', management.campuses, name='access_campuses'),
    path('manage/campuses/add/', management.campus_add, name='access_campus_add'),
    path('manage/campuses/<int:pk>/edit/', management.campus_edit, name='access_campus_edit'),
    path('manage/accounts/', management.accounts, name='access_accounts'),
    path('manage/accounts/add/', management.account_add, name='access_account_add'),
    path('manage/accounts/<int:pk>/edit/', management.account_edit, name='access_account_edit'),
    path('manage/roles/', management.roles, name='access_roles'),
    path('manage/roles/add/', management.role_add, name='access_role_add'),
    path('manage/roles/<int:pk>/edit/', management.role_edit, name='access_role_edit'),
    path('manage/roles/seed/', management.seed_role_templates, name='access_seed_roles'),
    path('manage/assignments/', management.assignments, name='access_assignments'),
    path('manage/assignments/add/', management.assignment_add, name='access_assignment_add'),
    path('manage/assignments/<int:pk>/edit/', management.assignment_edit, name='access_assignment_edit'),
    path('manage/assignments/<int:pk>/action/', management.assignment_action, name='access_assignment_action'),
    path('manage/student-campus-mapping/', management.student_mapping, name='access_student_mapping'),
    path('manage/ownership/', management.ownership_registry, name='access_ownership_registry'),
    path('manage/approvals/', management.approvals, name='access_approvals'),
    path('manage/payment-receipts/', management.payment_receipts, name='access_payment_receipts'),
    path('manage/authenticators/', management.mfa_devices, name='access_mfa_devices'),
    path('manage/authenticators/<int:pk>/revoke/', management.revoke_mfa_device, name='access_revoke_mfa'),
    path('manage/audit/', management.audit_log, name='access_audit_log'),
    path('workspace/', workspace.home, name='access_workspace'),
    path('authenticator/', workspace.authenticator, name='access_authenticator'),
    path('approvals/<int:pk>/', workspace.approval_detail, name='access_approval_detail'),
    path('approvals/<int:pk>/decision/', views.approval_decision, name='access_approval_decision'),
    path('vouchers/<int:voucher_id>/receipt/', views.payment_receipt, name='access_payment_receipt'),
]
