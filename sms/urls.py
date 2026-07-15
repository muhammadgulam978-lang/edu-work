from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from admin_panel.views import custom_login 
from login import views as login_views
from django.urls import path, include

urlpatterns = [
    path('', login_views.role_select_view, name='home'), 
    path('login/', login_views.role_select_view, name='login'),
    path('login/admin/', login_views.admin_login, name='login_admin'),
    path('login/teacher/', login_views.teacher_login, name='login_teacher'),
    path('login/student/', login_views.student_login, name='login_student'),
    path('login/parent/', login_views.parent_login, name='login_parent'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('auth/', include('login.urls')),

    path('admin/', admin.site.urls), 
    path('parent/', include('parent_dashboard.urls')),
    path('student/', include('student_profile.urls')),
    path('teacher/', include('teacher_dashboard.urls')),
    path('teacher_dashboard/', include('teacher_dashboard.urls')),
    path('admin_panel/', include('admin_panel.urls',)),

    path('exam/', include('exam_system.urls')), 
    path('automation/', include('edupilot_core.urls')),   # ← YE NAYI LINE ADD KAREIN
    # path('accounts/', include('django.contrib.auth.urls')),
]

from django.conf import settings
from django.conf.urls.static import static

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
