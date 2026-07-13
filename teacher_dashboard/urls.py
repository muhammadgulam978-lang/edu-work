from django.urls import path, include
from . import views

urlpatterns = [
    # =========================
    # TEACHER DASHBOARD CORE
    # =========================
    path("teacher_dashboard/", views.teacher_dashboard_view, name="teacher_dashboard"),
    path('appraisal/submit/', views.teacher_appraisal_submit, name='teacher_appraisal_submit'),

    # ✅ TEACHER TIMETABLE — sirf login_required, 403 nahi ayega
    # path("my-timetable/", views.teacher_timetable_view, name="teacher_timetable"),
    path('timetable/', views.teacher_timetable_view, name='teacher_timetable'),

    path(
        "view-students/<int:class_id>/<int:section_id>/",
        views.view_students,
        name="view_students",
    ),

    # =========================
    # ATTENDANCE
    # =========================
    path(
        "attendance/mark/<int:assigned_period_id>/",
        views.mark_attendance,
        name="mark_attendance",
    ),
    path(
        "attendance/view/<int:assigned_period_id>/",
        views.view_attendance,
        name="view_attendance",
    ),
    path(
        "attendance/summary/<int:assigned_period_id>/",
        views.attendance_summary,
        name="attendance_summary",
    ),

    # =========================
    # RESULTS
    # =========================
    path(
        "upload-result/<int:class_id>/<int:section_id>/<int:subject_id>/",
        views.upload_result,
        name="upload_result",
    ),
    path(
        "merge-result/<int:class_id>/<int:section_id>/",
        views.merge_result,
        name="merge_result",
    ),

    # =========================
    # LMS DASHBOARD
    # =========================
    path("lms/", views.lms_dashboard, name="lms_dashboard"),

    path('lesson-plans/', views.lesson_plans_list, name='lesson_plans_list'),

    path(
        "lms/class/<int:class_id>/section/<int:section_id>/subject/<int:subject_id>/",
        views.lms_actions_menu,
        name="lms_actions_menu",
    ),

    # =========================
    # LMS CONTENT
    # =========================
    path(
        "lms/class/<int:class_id>/section/<int:section_id>/subject/<int:subject_id>/upload-lecture/",
        views.upload_lecture_note,
        name="upload_lecture_note",
    ),

    path(
        "upload-assignment/<int:class_id>/<int:section_id>/<int:subject_id>/",
        views.upload_assignment,
        name="upload_assignment",
    ),

    path(
        "assignments/<int:class_id>/<int:section_id>/<int:subject_id>/",
        views.view_assignments,
        name="view_assignments",
    ),

    path('view-submissions/<int:class_id>/<int:section_id>/<int:subject_id>/',
        views.view_assignment_submissions, name='view_assignment_submissions'),

    path('give-marks/<int:submission_id>/',
        views.give_assignment_marks, name='give_assignment_marks'),

    path(
        "upload_quiz/<int:class_id>/<int:section_id>/<int:subject_id>/",
        views.upload_quiz,
        name="upload_quiz",
    ),

    path(
        "quiz_submissions/<int:class_id>/<int:section_id>/<int:subject_id>/",
        views.view_quiz_submissions,
        name="view_quiz_submissions",
    ),

    path(
        "diary/submit/<int:class_id>/<int:section_id>/<int:subject_id>/",
        views.submit_diary,
        name="submit_diary",
    ),

    path(
        "diary/view/<int:class_id>/<int:section_id>/<int:subject_id>/",
        views.view_diary_student,
        name="view_diary_student",
    ),

    # =========================
    # LMS → BOOKS
    # =========================
    path(
        "teacher/lms/class/<int:class_id>/section/<int:section_id>/subject/<int:subject_id>/books/",
        views.lms_books_list,
        name="lms_books_list",
    ),

    path(
        "lms/class/<int:class_id>/section/<int:section_id>/subject/<int:subject_id>/books/create/",
        views.lms_create_book,
        name="lms_create_book",
    ),

    path(
        "teacher/lms/book/<int:book_id>/chapters/",
        views.lms_book_chapters,
        name="lms_book_chapters",
    ),

    # =========================
    # LESSON PLANNING (FINAL FLOW)
    # =========================
    path(
        "teacher/lesson-planning/upload/",
        views.lesson_upload_chapter,
        name="lesson_upload_chapter",
    ),

    path(
        "teacher/lesson-planning/chapter/<int:chapter_id>/topics/",
        views.lesson_select_topics,
        name="lesson_select_topics",
    ),

    path(
        "teacher/lms/chapter/<int:chapter_id>/lesson-plans/",
        views.lms_chapter_lesson_plans,
        name="lms_chapter_lesson_plans",
    ),

    # =========================
    # EXAM SYSTEM
    # =========================
    path('exam/question-banks/', views.question_bank_list, name='question_bank_list'),
    path('exam/plans/', views.exam_plan_list, name='exam_plan_list'),
    path('exam/plans/create/', views.create_exam_plan, name='create_exam_plan'),
    path('exam/analytics/', views.analytics_dashboard, name='analytics_dashboard'),

    path("appraisal/submit/", views.teacher_appraisal_submit, name="teacher_appraisal_submit"),
]