from django.conf import settings
from django.core.paginator import Paginator


def use_paginator(request, post_list):
    paginator = Paginator(post_list, settings.COUNT_OF_POSTS)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)
