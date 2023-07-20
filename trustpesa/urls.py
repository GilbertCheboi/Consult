# -*- coding: utf-8 -*-
"""Trust Pesa App URLs"""

from django.conf.urls import include
from django.contrib.auth import views as auth_views
from django.urls import path, re_path

import notifications.urls
from organizations.backends import invitation_backend

from trustpesa import views

urlpatterns = [
    re_path('^$', views.phone_verification, name='trustpesa_home'),
    re_path(
        r'^phone/$',
        views.phone_verification,
        name='trustpesa_phone_verification',
    ),
    re_path(
        r'^customer_accountdetails/$',
        views.customer_accountdetails,
        name='trustpesa_customer_account_details',
    ),
    re_path(
        r'^customer_accountstatement/$',
        views.customer_accountstatement,
        name='trustpesa_customer_account_statement'

    ),

]
