from django import template
register = template.Library()

@register.filter
def dictget(dict_data, key):
    if dict_data is None:
        return None
    return dict_data.get(key)
