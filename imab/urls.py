# -*- coding: utf-8 -*-
"""IMAB App URLs"""

from django.conf.urls import include
from django.contrib.auth import views as auth_views
from django.urls import path, re_path

import notifications.urls
from organizations.backends import invitation_backend

from imab import views


urlpatterns = [
    re_path(
        r'^customer_accountdetails/(?P<scope>\w+)/$',
        views.customer_accountdetails, name='imab_customer_account_details',
    ),
    re_path(
        r'^customer_accountstatement/(?P<scope>\w+)/$',
        views.customer_accountstatement, name='imab_customer_account_statement'

    ),

]
