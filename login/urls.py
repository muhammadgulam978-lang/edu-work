from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .views import custom_logout 

urlpatterns = [
    path('login/', views.login_view, name='login'),  
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
    # path('login/', auth_views.LoginView.as_view(template_name='login/login.html'), name='login'),
    path('logout/', custom_logout, name='custom_logout'),

]

