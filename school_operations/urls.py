from django.urls import path
from . import views

urlpatterns = [
    path('cases/<int:pk>/', views.case_detail, name='operations_case_detail'),
    path('<str:kind>/', views.records, name='operations_records'),
    path('<str:kind>/add/', views.create_record, name='operations_create'),
    path('<str:kind>/<int:pk>/action/', views.record_action, name='operations_action'),
]
