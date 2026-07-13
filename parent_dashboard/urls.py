# from django.urls import path
# from .import views

# urlpatterns = [
#     path('home/', views.parent_dashboard_home, name='parent_dashboard_home'),
#     path('dashboard/', views.parent_dashboard, name='parent_dashboard'),
#     path('list/', views.parent_list, name='parent_list'),  # ← ye add karo
# ]







from django.urls import path
from parent_dashboard import views

urlpatterns = [
    
    path(
        "home/",
        views.parent_dashboard_home,
        name="parent_dashboard_home"
    ),

    path(
        "",
        views.parent_dashboard,
        name="parent_dashboard"
    ),

    path(
        "list/",
        views.parent_list,
        name="parent_list"
    ),

    path(
        "attendance/",
        views.parent_attendance,
        name="parent_attendance"
    ),
   
    path(
        "result/",
        views.parent_result,
        name="parent_result"
    ),

    path(
        "assignments/",
        views.parent_assignment,
        name="parent_assignment"
    ),

    path(
        "quizzes/",
        views.parent_quizzes,
        name="parent_quizzes"
    ),

    path(
        "diary/",
        views.parent_diary,
        name="parent_diary"
    ),


    path(
        "timetable/",
        views.parent_timetable,
        name="parent_timetable"
    ),

]