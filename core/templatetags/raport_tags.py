import builtins

from django import template

register = template.Library()


@register.filter
def zip(a, b):
    return list(builtins.zip(a, b))
