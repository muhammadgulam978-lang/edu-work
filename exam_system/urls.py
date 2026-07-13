# exam_system/urls.py
from django.urls import path
from exam_system import views

urlpatterns = [

    # ── QUESTION BANK ─────────────────────────────────────────────────────
    path('question-banks/',
         views.question_bank_list,
         name='question_bank_list'),
    
    path('question-banks/<int:bank_id>/delete/', views.delete_question_bank, name='delete_question_bank'),

    path('question-banks/<int:bank_id>/',
         views.question_bank_detail,
         name='question_bank_detail'),

    path('question-banks/<int:bank_id>/add-question/',
         views.add_question_to_bank,
         name='add_question_to_bank'),

    path('question-banks/<int:bank_id>/bulk-approve/',
         views.bulk_approve_questions,
         name='bulk_approve_questions'),

    path('question-banks/<int:bank_id>/ai-generate/',
         views.ai_generate_questions,
         name='ai_generate_questions'),

    # Book upload → AI generate (purana 'generate_questions_from_pdf' bhi yahi karta tha)
    path('question-banks/<int:bank_id>/upload-book/',
         views.upload_book_for_bank,
         name='upload_book_for_bank'),

    # backward-compat alias — purani URLs toot na jayen
    path('question-banks/<int:bank_id>/generate-from-pdf/',
         views.upload_book_for_bank,
         name='generate_questions_from_pdf'),

    # ── SINGLE QUESTION ACTIONS ────────────────────────────────────────────
    path('questions/<int:question_id>/approve/',
         views.approve_question,
         name='approve_question'),

    path('questions/<int:question_id>/edit/',
         views.edit_question,
         name='edit_question'),

    path('questions/<int:question_id>/toggle-approve/',
         views.toggle_approve_question,
         name='toggle_approve_question'),

    # ── EXAM PLANS ────────────────────────────────────────────────────────
    path('plans/',
         views.exam_plan_list,
         name='exam_plan_list'),

    path('plans/create/',
         views.create_exam_plan,
         name='create_exam_plan'),

    path('plans/<int:plan_id>/',
         views.exam_plan_detail,
         name='exam_plan_detail'),

    path('plans/<int:plan_id>/add-schedule/',
         views.add_exam_schedule,
         name='add_exam_schedule'),

    path('plans/<int:plan_id>/blueprint/<int:subject_id>/',
         views.create_blueprint,
         name='create_blueprint'),

    # ── PAPER GENERATION + APPROVAL ───────────────────────────────────────
    path('papers/queue/',
         views.admin_paper_queue,
         name='admin_paper_queue'),

    path('blueprint/<int:blueprint_id>/generate-paper/',
         views.generate_paper_view,
         name='generate_paper_view'),

    path('papers/<int:paper_id>/approval/',
         views.paper_approval_detail,
         name='paper_approval_detail'),
    
    

    path('papers/<int:paper_id>/upload-pdf/',
         views.upload_pdf_for_paper,
         name='upload_pdf_for_paper'),

    path('papers/<int:paper_id>/download/',
         views.download_paper,
         name='download_paper'),

    # ── EXAM CONDUCT ──────────────────────────────────────────────────────
    path('conduct/<int:schedule_id>/',
         views.exam_conduct_dashboard,
         name='exam_conduct_dashboard'),

    path('conduct/<int:schedule_id>/attendance/',
         views.mark_exam_attendance,
         name='mark_exam_attendance'),

    path('conduct/<int:schedule_id>/seating/',
         views.auto_generate_seating,
         name='auto_generate_seating'),

    path('conduct/<int:schedule_id>/sheets/',
         views.answer_sheet_list,
         name='answer_sheet_list'),

    path('sheets/<int:sheet_id>/mark/',
         views.mark_answer_sheet,
         name='mark_answer_sheet'),

    path('conduct/<int:schedule_id>/compile/',
         views.compile_exam_results,
         name='compile_exam_results'),

    path('conduct/<int:schedule_id>/results/',
         views.exam_results_list,
         name='exam_results_list'),

    # ── ANALYTICS ─────────────────────────────────────────────────────────
    path('analytics/',
         views.analytics_dashboard,
         name='analytics_dashboard'),
]