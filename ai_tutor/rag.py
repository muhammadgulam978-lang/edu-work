from django.db.models import Q

from .models import AIKnowledgeDocument


def retrieve_documents(*, student, subject=None, query="", limit=5):
    queryset = AIKnowledgeDocument.objects.filter(
        approval_status="approved",
        access_level="student",
    )

    if student.class_fk_id:
        queryset = queryset.filter(Q(class_fk=student.class_fk) | Q(class_fk__isnull=True))
    if student.section_id:
        queryset = queryset.filter(Q(section=student.section) | Q(section__isnull=True))
    if subject:
        queryset = queryset.filter(Q(subject=subject) | Q(subject__isnull=True))

    terms = [term for term in (query or "").split() if len(term) > 2][:6]
    if terms:
        search_q = Q()
        for term in terms:
            search_q |= Q(title__icontains=term) | Q(content__icontains=term) | Q(topic__icontains=term)
        queryset = queryset.filter(search_q)

    return list(queryset.order_by("-updated_at")[:limit])
