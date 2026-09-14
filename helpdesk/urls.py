from django.urls import path

from . import views

app_name = 'helpdesk'

urlpatterns = [
    path('', views.portal_dashboard, name='portal'),
    path('new/', views.ticket_create, name='ticket_create'),
    path('tickets/<int:pk>/', views.ticket_detail, name='ticket_detail'),
    path('tickets/<int:pk>/<str:action>/', views.ticket_portal_action, name='ticket_portal_action'),
    path('staff/', views.staff_dashboard, name='staff_dashboard'),
    path('staff/tickets/<int:pk>/', views.staff_ticket_detail, name='staff_ticket_detail'),
    path('staff/tickets/<int:pk>/<str:action>/', views.staff_ticket_action, name='staff_ticket_action'),
    path('attachments/<int:pk>/download/', views.attachment_download, name='attachment_download'),
]
