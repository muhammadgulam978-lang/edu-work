# teacher_dashboard/templatetags/result_filters.py

from django import template

register = template.Library()

@register.filter
def get_result(results_dict, student_id):
    return results_dict.get(student_id)

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, "-")
