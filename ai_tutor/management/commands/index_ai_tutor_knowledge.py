from django.core.management.base import BaseCommand

from admin_panel.models import ContentBlock, LessonDay
from teacher_dashboard.models import Assignment, LectureNote, Quiz

from ai_tutor.models import AIKnowledgeDocument


class Command(BaseCommand):
    help = "Index approved curriculum and teacher content for AI Tutor retrieval."

    def handle(self, *args, **options):
        created, updated = 0, 0

        for note in LectureNote.objects.select_related("class_fk", "section", "subject"):
            count = self._upsert(
                source_model="teacher_dashboard.LectureNote",
                source_id=note.id,
                title=note.title,
                content=f"{note.title}\n{note.description or ''}",
                document_type="teacher_note",
                class_fk=note.class_fk,
                section=note.section,
                subject=note.subject,
                source_reference=f"Lecture note #{note.id}",
            )
            created += count[0]
            updated += count[1]

        for assignment in Assignment.objects.select_related("class_fk", "section", "subject"):
            count = self._upsert(
                source_model="teacher_dashboard.Assignment",
                source_id=assignment.id,
                title=assignment.title,
                content=f"{assignment.title}\n{assignment.description or ''}",
                document_type="assignment",
                class_fk=assignment.class_fk,
                section=assignment.section,
                subject=assignment.subject,
                source_reference=f"Assignment #{assignment.id}",
            )
            created += count[0]
            updated += count[1]

        for quiz in Quiz.objects.select_related("class_fk", "section", "subject"):
            count = self._upsert(
                source_model="teacher_dashboard.Quiz",
                source_id=quiz.id,
                title=quiz.title,
                content=quiz.title,
                document_type="quiz",
                class_fk=quiz.class_fk,
                section=quiz.section,
                subject=quiz.subject,
                source_reference=f"Quiz #{quiz.id}",
            )
            created += count[0]
            updated += count[1]

        for block in ContentBlock.objects.select_related(
            "topic__chapter__class_for",
            "topic__chapter__subject",
            "subtopic__topic__chapter__class_for",
            "subtopic__topic__chapter__subject",
        ):
            topic = block.topic or (block.subtopic.topic if block.subtopic_id else None)
            chapter = topic.chapter if topic else None
            if not topic or not chapter:
                continue
            count = self._upsert(
                source_model="admin_panel.ContentBlock",
                source_id=block.id,
                title=topic.title,
                content=block.text,
                document_type="curriculum",
                class_fk=chapter.class_for,
                section=None,
                subject=chapter.subject,
                chapter_title=chapter.title,
                topic=topic.title,
                source_reference=f"Content block #{block.id}",
            )
            created += count[0]
            updated += count[1]

        for lesson in LessonDay.objects.select_related(
            "plan__chapter__class_for",
            "plan__chapter__subject",
        ).prefetch_related("plan__topics"):
            plan = lesson.plan
            if not plan or not plan.chapter:
                continue
            topics = ", ".join(topic.title for topic in plan.topics.all())
            content = "\n".join(
                [
                    lesson.learning_objectives,
                    lesson.teaching_content,
                    lesson.practice_work,
                    lesson.assessment_tasks,
                    lesson.homework_tasks,
                ]
            )
            count = self._upsert(
                source_model="admin_panel.LessonDay",
                source_id=lesson.id,
                title=f"Lesson Day {lesson.day_number}: {topics or plan.chapter.title}",
                content=content,
                document_type="lesson_plan",
                class_fk=plan.chapter.class_for,
                section=None,
                subject=plan.chapter.subject,
                chapter_title=plan.chapter.title,
                topic=topics,
                source_reference=f"Lesson day #{lesson.id}",
            )
            created += count[0]
            updated += count[1]

        self.stdout.write(self.style.SUCCESS(f"AI Tutor knowledge indexed. Created: {created}, Updated: {updated}"))

    def _upsert(self, **kwargs):
        if not (kwargs.get("content") or "").strip():
            return 0, 0
        obj, was_created = AIKnowledgeDocument.objects.update_or_create(
            source_model=kwargs.pop("source_model"),
            source_id=kwargs.pop("source_id"),
            defaults={
                **kwargs,
                "access_level": "student",
                "approval_status": "approved",
            },
        )
        return (1, 0) if was_created else (0, 1)
