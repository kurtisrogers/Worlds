from django import template

register = template.Library()


@register.filter
def cents_to_dollars(value):
    """Convert cents integer to dollar string like 2.99."""
    if value is None:
        return ""
    return f"${value / 100:.2f}"


@register.filter
def get_item(mapping, key):
    """Dict lookup in templates."""
    if mapping is None:
        return {}
    return mapping.get(key, {})
