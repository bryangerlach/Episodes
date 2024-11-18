# my_filters.py
from django import template

register = template.Library()

@register.filter
def order_by(queryset, attribute):
    return queryset.order_by(attribute)