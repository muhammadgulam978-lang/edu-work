
from django import forms
from admin_panel.models import ExamFormat, Question

class ExamFormatForm(forms.ModelForm):
    class Meta:
        model = ExamFormat
        fields = ['class_obj', 'subject', 'format_name', 'num_mcqs', 'num_short', 'num_long']


class AddQuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['question_type', 'text', 'section']




# teacher_dashboard/forms.py

from django import forms
from admin_panel.models import LessonPlanRequest, Topic

class LessonPlanForm(forms.ModelForm):
    topics = forms.ModelMultipleChoiceField(
        queryset=Topic.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = LessonPlanRequest
        fields = "__all__"   # ✅ IMPORTANT: unknown field error khatam

class WorksheetGenerationForm(forms.Form):
    topic_ids = forms.CharField(widget=forms.HiddenInput)
    num_mcq = forms.IntegerField(min_value=0, max_value=50, initial=5)
    num_short = forms.IntegerField(min_value=0, max_value=50, initial=5)
