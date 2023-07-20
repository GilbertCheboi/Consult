# -*- coding: utf-8 -*-
"""Helpline views """

from django.conf.urls import include
from django.contrib.auth import views as auth_views
from django.urls import path, re_path

import notifications.urls
from organizations.backends import invitation_backend

from collection_crm import views

app_name = 'collection_crm'

urlpatterns = [
    re_path('^$', views.home, name='home'),
    re_path('^leads/$', views.leads, name='leads'),
    re_path('^search/$', views.search, name='search'),
    re_path(
        '^batch_history_download_loadcsv/$',
        views.batch_history_download_loadcsv,
        name='batch_history_download_loadcsv'
    ),
    re_path('^report/$', views.report, name='report'),
    re_path(
        '^batch_edit_loadcsv/$',
        views.batch_edit_loadcsv,
        name='batch_edit_loadcsv'
    ),
    re_path('^not_contacted/$', views.not_contacted, name='not_contacted'),
    re_path('^ptp_report/$', views.ptp_report, name='ptp_report'),
    re_path('^allocation/$', views.allocation, name='allocation'),
    re_path(
        '^allocation_summary/$',
        views.allocation_summary,
        name='allocation_summary'
    ),
    re_path('^audit_view/$', views.audit_view, name='audit_view'),
    re_path('^attempts/$', views.attempts, name='attempts'),
    re_path(
        '^delinquency_report/$',
        views.delinquency_report,
        name='delinquency_report'
    ),
    re_path(
        '^agent_productivity_report/$',
        views.agent_productivity_report,
        name='agent_productivity_report'
    ),
    re_path(
        '^agent_productivity_report_details/$',
        views.agent_productivity_report_details,
        name='agent_productivity_report_details'
    ),
    re_path('^loadcsv/$', views.loadcsv, name='loadcsv'),
    re_path(
        '^collection_summary/$',
        views.collection_summary,
        name='collection_summary'
    ),
    re_path(
        '^call_status_report/$',
        views.call_status_report,
        name='call_status_report'
    ),
    re_path('^users/$', views.users, name='users'),
    re_path('^create_new_user/$', views.create_new_user, name='create_new_user'),
    re_path(r'^user/@(?P<username>[^/]+)/$', views.user_profile,
            name='user_profile'),
    re_path('^notification/$', views.notification, name='notification'),
]
