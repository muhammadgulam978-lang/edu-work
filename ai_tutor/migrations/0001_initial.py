from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("admin_panel", "0033_automationjob_feegenerationlog_feegenerationsettings_and_more"),
        ("student_profile", "0002_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AITutorSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("topic", models.CharField(blank=True, max_length=255)),
                ("session_type", models.CharField(choices=[("learn", "Learn"), ("revise", "Revise"), ("practice", "Practice"), ("homework_help", "Homework Help"), ("exam_prep", "Exam Preparation"), ("ask", "Ask a Question")], default="learn", max_length=30)),
                ("language", models.CharField(default="English", max_length=50)),
                ("status", models.CharField(choices=[("active", "Active"), ("closed", "Closed")], default="active", max_length=20)),
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                ("total_messages", models.PositiveIntegerField(default=0)),
                ("total_tokens", models.PositiveIntegerField(default=0)),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ai_tutor_sessions", to="student_profile.student")),
                ("subject", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ai_tutor_sessions", to="admin_panel.subject")),
            ],
            options={"ordering": ["-started_at"]},
        ),
        migrations.CreateModel(
            name="AIKnowledgeDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("content", models.TextField()),
                ("document_type", models.CharField(choices=[("curriculum", "Curriculum"), ("teacher_note", "Teacher Note"), ("book", "Book"), ("chapter", "Chapter"), ("topic", "Topic"), ("lesson_plan", "Lesson Plan"), ("worksheet", "Worksheet"), ("assignment", "Assignment"), ("quiz", "Quiz")], max_length=50)),
                ("chapter_title", models.CharField(blank=True, max_length=255)),
                ("topic", models.CharField(blank=True, max_length=255)),
                ("access_level", models.CharField(choices=[("student", "Student"), ("teacher", "Teacher"), ("admin", "Admin")], default="student", max_length=30)),
                ("approval_status", models.CharField(choices=[("approved", "Approved"), ("draft", "Draft"), ("archived", "Archived")], default="approved", max_length=30)),
                ("source_model", models.CharField(blank=True, max_length=100)),
                ("source_id", models.PositiveIntegerField(blank=True, null=True)),
                ("source_reference", models.CharField(blank=True, max_length=255)),
                ("vector_reference", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("class_fk", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ai_knowledge_documents", to="admin_panel.class")),
                ("section", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ai_knowledge_documents", to="admin_panel.section")),
                ("subject", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ai_knowledge_documents", to="admin_panel.subject")),
            ],
            options={"ordering": ["title"]},
        ),
        migrations.CreateModel(
            name="AITutorMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sender_type", models.CharField(choices=[("student", "Student"), ("assistant", "Assistant"), ("system", "System")], max_length=20)),
                ("message_text", models.TextField(blank=True)),
                ("response_text", models.TextField(blank=True)),
                ("intent", models.CharField(blank=True, max_length=50)),
                ("model_name", models.CharField(blank=True, max_length=100)),
                ("safety_status", models.CharField(choices=[("allowed", "Allowed"), ("blocked", "Blocked"), ("needs_review", "Needs Review"), ("error", "Error")], default="allowed", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="ai_tutor.aitutorsession")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ai_tutor_messages", to="student_profile.student")),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.CreateModel(
            name="AIPracticeAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("topic", models.CharField(blank=True, max_length=255)),
                ("question_text", models.TextField()),
                ("expected_answer", models.TextField(blank=True)),
                ("expected_concepts", models.JSONField(blank=True, default=list)),
                ("student_answer", models.TextField(blank=True)),
                ("is_correct", models.BooleanField(blank=True, null=True)),
                ("score", models.FloatField(blank=True, null=True)),
                ("hint_used", models.BooleanField(default=False)),
                ("attempt_number", models.PositiveIntegerField(default=1)),
                ("feedback", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("answered_at", models.DateTimeField(blank=True, null=True)),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="practice_attempts", to="ai_tutor.aitutorsession")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ai_practice_attempts", to="student_profile.student")),
                ("subject", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ai_practice_attempts", to="admin_panel.subject")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="StudentAIPreference",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("preferred_language", models.CharField(default="English", max_length=50)),
                ("explanation_style", models.CharField(default="simple", max_length=50)),
                ("default_difficulty", models.CharField(default="easy", max_length=50)),
                ("voice_enabled", models.BooleanField(default=False)),
                ("accessibility_preferences", models.JSONField(blank=True, default=dict)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("student", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="ai_preference", to="student_profile.student")),
            ],
        ),
        migrations.CreateModel(
            name="StudentTopicMastery",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("topic", models.CharField(max_length=255)),
                ("mastery_level", models.CharField(choices=[("not_started", "Not Started"), ("introduced", "Introduced"), ("developing", "Developing"), ("practicing", "Practicing"), ("mastered", "Mastered"), ("needs_revision", "Needs Revision")], default="introduced", max_length=30)),
                ("accuracy_percentage", models.FloatField(default=0)),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("last_practiced_at", models.DateTimeField(blank=True, null=True)),
                ("recommended_action", models.TextField(blank=True)),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ai_topic_mastery", to="student_profile.student")),
                ("subject", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ai_topic_mastery", to="admin_panel.subject")),
            ],
            options={"ordering": ["subject__name", "topic"], "unique_together": {("student", "subject", "topic")}},
        ),
        migrations.CreateModel(
            name="AIAuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action_type", models.CharField(max_length=100)),
                ("model_used", models.CharField(blank=True, max_length=100)),
                ("retrieved_document_ids", models.JSONField(blank=True, default=list)),
                ("safety_flags", models.JSONField(blank=True, default=list)),
                ("access_result", models.CharField(default="allowed", max_length=50)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("session", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="audit_logs", to="ai_tutor.aitutorsession")),
                ("student", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ai_audit_logs", to="student_profile.student")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="aiknowledgedocument",
            index=models.Index(fields=["class_fk", "section", "subject", "approval_status", "access_level"], name="ai_tutor_ai_class_f_a7a054_idx"),
        ),
        migrations.AddIndex(
            model_name="aiknowledgedocument",
            index=models.Index(fields=["document_type", "source_model", "source_id"], name="ai_tutor_ai_documen_b52f03_idx"),
        ),
    ]
