from django.core.management.base import BaseCommand
from teacher_dashboard.models import LessonDay, LessonPlanRequest
from django.test import RequestFactory
from teacher_dashboard.views import generate_lesson_details
import json
from django.db.models import Q

class Command(BaseCommand):
    help = 'Backfill AI content for LessonDay entries with empty fields'

    def handle(self, *args, **kwargs):
        factory = RequestFactory()
        updated = 0
        
        missing = LessonDay.objects.filter(
            Q(objective__isnull=True) | Q(objective='') | Q(objective__iexact='N/A')
        ).count()
        self.stdout.write(f"Found {missing} lessons needing AI content.")
        for lesson in LessonDay.objects.filter(
            Q(objective__isnull=True) | Q(objective='') | Q(objective__iexact='N/A')
        ):
            plan = lesson.plan
            if not plan.chapter_title or not plan.topic_title:
                print(f"Skipping lesson {lesson.id} due to missing chapter or topic.")
                continue
            fake_request = factory.post(
                '/teacher/api/generate-lesson/',
                data=json.dumps({
                    'subject': plan.guide.subject,
                    'chapter': plan.chapter_title,
                    'topic': plan.topic_title
                }),
                content_type='application/json'
            )
            response = generate_lesson_details(fake_request)
            if response.status_code == 200:
                ai_data = json.loads(response.content)['data']
                lesson.objective = ai_data.get('objective', '')
                lesson.activities = ai_data.get('activities', '')
                lesson.materials = ai_data.get('materials', '')
                lesson.assessment = ai_data.get('assessment', '')
                lesson.homework = ai_data.get('homework', '')
                lesson.save()
                updated += 1
            else:
                print(f"Failed to generate for lesson {lesson.id}: status {response.status_code}, content: {response.content}")
        self.stdout.write(self.style.SUCCESS(f'Updated {updated} lessons with AI content.'))