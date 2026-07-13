from django import template

register = template.Library()

@register.filter
def dict_get(d, key):
    """Safely get key from dict, return '---' if not found."""
    if not isinstance(d, dict):
        return '---'
    return d.get(key, '---')

@register.filter
def period_label(value):
    """
    Extract short period label from full period name string.
    E.g. "Monday - 1st: 8:00 - 8:40" -> "1st"
    """
    try:
        # value expected format: "Monday - 1st: 8:00 - 8:40"
        part = value.split('-')[1]  # " 1st: 8:00 - 8:40"
        label = part.split(':')[0].strip()  # "1st"
        return label
    except Exception:
        return value  # fallback to original if parsing fails

@register.filter
def dict_sum(d):
    """Sum integer values of dict, ignoring non-ints."""
    if not isinstance(d, dict):
        return 0
    return sum(v for v in d.values() if isinstance(v, int))
