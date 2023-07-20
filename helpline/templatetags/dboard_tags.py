"""Tamplate tags that assist our application"""
from datetime import datetime

from django.template.defaulttags import register


@register.filter(name='timestamp')
def timestamp(value):
    """Return datetime object from epoch value"""
    try:
        return datetime.fromtimestamp(value)
    except AttributeError as e:
        return e


@register.filter(name='user_email_domain')
def user_email_domain(user):
    return user.email.split('@')[-1]
