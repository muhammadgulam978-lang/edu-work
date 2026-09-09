from django.urls import path

from .api import StudentLoginView, StudentLogoutView, StudentMeView, StudentTokenRefreshView


urlpatterns = [
    path("auth/student/login/", StudentLoginView.as_view(), name="api-student-login"),
    path("auth/token/refresh/", StudentTokenRefreshView.as_view(), name="api-token-refresh"),
    path("auth/me/", StudentMeView.as_view(), name="api-student-me"),
    path("auth/logout/", StudentLogoutView.as_view(), name="api-student-logout"),
]
