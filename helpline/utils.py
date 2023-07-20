# -*- coding: utf-8 -*-
"""Helpline utilities"""

import string
import random
from django.utils.text import slugify


def random_string_generator(
    size=10, chars=string.ascii_lowercase + string.digits
):
    """Create a random string"""
    return ''.join(random.choice(chars) for _ in range(size))


def unique_slug_generator(instance, new_slug=None):
    """Create a unique slug"""
    if new_slug is not None:
        slug = new_slug
    else:
        slug = slugify(instance.name)
    Klass = instance.__class__
    max_length = Klass._meta.get_field('slug').max_length
    slug = slug[:max_length]
    qs_exists = Klass.objects.filter(slug=slug).exists()

    if qs_exists:
        slug = slug[:max_length-5]
        randstr = random_string_generator(size=4)
        new_slug = f"{slug}-{randstr}"
        return unique_slug_generator(instance, new_slug=new_slug)
    return slug
