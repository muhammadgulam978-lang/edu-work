from django.shortcuts import get_object_or_404
from admin_panel.models import Class, Section, Subject

def lms_sidebar_context(request):
    """
    Add class_obj, section_obj, subject_obj to context automatically
    if URL me class_id, section_id, subject_id present ho.
    """
    class_obj = section_obj = subject_obj = None

    # Agar URL ke kwargs available hain (resolver match karega)
    if hasattr(request, 'resolver_match') and request.resolver_match:
        kwargs = request.resolver_match.kwargs
        class_id = kwargs.get('class_id')
        section_id = kwargs.get('section_id')
        subject_id = kwargs.get('subject_id')

        if class_id and section_id and subject_id:
            try:
                class_obj = Class.objects.get(id=class_id)
                section_obj = Section.objects.get(id=section_id)
                subject_obj = Subject.objects.get(id=subject_id)
            except (Class.DoesNotExist, Section.DoesNotExist, Subject.DoesNotExist):
                pass

    return {
        'class_obj': class_obj,
        'section_obj': section_obj,
        'subject_obj': subject_obj,
    }
