from django import template

register = template.Library()

@register.filter
def dict_key(d, key):
    """Get dict key safely"""
    if d is None:
        return None
    return d.get(str(key), None)

@register.filter
def mul(value, arg):
    """Multiply"""
    return int(value) * int(arg)

@register.filter
def add(value, arg):
    """Add"""
    return int(value) + int(arg)
