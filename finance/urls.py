from django.urls import path

from . import views

app_name = 'finance'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('setup/', views.setup, name='setup'),
    path('vouchers/', views.voucher_list, name='voucher_list'),
    path('vouchers/create/', views.voucher_create, name='voucher_create'),
    path('vouchers/<int:pk>/', views.voucher_detail, name='voucher_detail'),
    path('vouchers/<int:pk>/<str:action>/', views.voucher_action, name='voucher_action'),
    path('reports/', views.reports, name='reports'),
    path('periods/<int:pk>/<str:action>/', views.period_action, name='period_action'),
    path('audit/', views.audit_log, name='audit'),
    path('cash-sessions/', views.cash_sessions, name='cash_sessions'),
    path('cash-sessions/<int:pk>/<str:action>/', views.cash_session_action, name='cash_session_action'),
    path('bank-reconciliation/', views.bank_reconciliation, name='bank_reconciliation'),
    path('bank-reconciliation/<int:pk>/', views.bank_statement_detail, name='bank_statement_detail'),
    path('bank-lines/<int:pk>/match/', views.bank_line_match, name='bank_line_match'),
    path('bank-reconciliation/<int:pk>/<str:action>/', views.bank_statement_action, name='bank_statement_action'),
    path('budgets/', views.budgets, name='budgets'),
    path('requests/', views.request_list, name='request_list'),
    path('requests/<int:pk>/<str:action>/', views.request_action, name='request_action'),
    path('portal/', views.portal_dashboard, name='portal'),
    path('portal/request/', views.portal_request, name='portal_request'),
    path('portal/fee/<int:pk>/download/', views.fee_document, name='fee_document'),
    path('portal/receipt/<int:pk>/download/', views.receipt_document, name='receipt_document'),
    path('portal/payslip/<int:pk>/download/', views.payslip_document, name='payslip_document'),
]
