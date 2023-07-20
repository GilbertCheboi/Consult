

# -*- coding: utf-8 -*-
"""Helpline views """

import os
import base64
import calendar
import urllib.parse
import time
from random import randint
import hashlib
import urllib
from itertools import tee

from pathlib import Path
import pickle

from datetime import timedelta, datetime, date, time as datetime_time

import json
import requests
import curlify

import pytz

from django.shortcuts import render, redirect, resolve_url
from django.template.defaulttags import register
from django.http import JsonResponse, Http404
from django.http import (HttpResponse, HttpResponseBadRequest,
                         HttpResponseForbidden, HttpResponseRedirect)
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import cache_page
from django.views.decorators.clickjacking import xframe_options_exempt

from django.core.cache import caches
from django.core.mail import send_mail
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.template.context_processors import csrf
from django.template.loader import render_to_string
from django.db.models import Avg
from django.contrib.auth import logout
from django.contrib.auth.views import redirect_to_login
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.db.models import Sum

from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.db.models.signals import post_save
from django.conf import settings
from django.utils.translation import gettext as _
from django.utils import timezone
from django import forms

from django.urls import reverse

from notifications.signals import notify

import django_tables2 as tables

from django_tables2.config import RequestConfig
from django_tables2.export.export import TableExport
from django_tables2.export.views import ExportMixin

from allauth.account.models import EmailAddress
from crispy_forms.utils import render_crispy_form
from jsonview.decorators import json_view
import pandas as pd
import numpy as np
from io import StringIO
from allauth.socialaccount.models import SocialToken, SocialAccount

from dateutil.relativedelta import relativedelta

from helpline.models import Report, HelplineUser,\
        Schedule, Case, Postcode,\
        Service, Hotdesk, Category, Clock,\
        MainCDR, Recorder, Address, Contact,\
        Messaging, SipServerConfig, Cdr, Break,\
        BackendServerManagerConfig, DID, RecordPlay
from helpline.forms import QueueLogForm,\
        ContactForm, DispositionForm, CaseSearchForm, MyAccountForm, \
        ReportFilterForm, QueuePauseForm, CaseActionForm, ContactSearchForm, \
        CaseDetailForm, InviteForm, ServiceForm, GetRecordsForm

from helpline.qpanel.config import QPanelConfig
from helpline.qpanel.utils import realname_queue_rename

from helpline.tasks import get_queues_data,\
        cache_outbound_caller_id, pbxapi_set_outbound_caller_id,\
        click_to_call, pbxapi_get_auth_token, pbxapi_get_extension,\
        get_data_campaign, process_campaign_webhook_data,\
        update_inactive_campaigns, pbx_auth_encode,\
        get_recording_file, update_finished_campaigns,\
        get_data_call_details, backend_get_eccp_credentials,\
        backend_agent_status, backend_agent_login

from helpline.qpanel.backend import Backend
if QPanelConfig().has_queuelog_config():
    from helpline.qpanel.model import queuelog_data_queue

from invitations.utils import get_invitation_model
import mysql.connector
from mysql.connector import Error

from two_factor.utils import default_device

from oauth2_provider.models import get_application_model
from oauth2_provider.views.generic import ProtectedResourceView

try:
    from django.utils.http import url_has_allowed_host_and_scheme
except ImportError:
    from django.utils.http import (
        is_safe_url as url_has_allowed_host_and_scheme,
    )

# import the logging library
import logging
# Get an instance of a logger
logger = logging.getLogger(__name__)
from calendly.models import AccessToken

def index(request):
    """Landing page"""

    if request.user.is_authenticated:
        return redirect("/helpline/")

    return render(
        request, "helpline/index.html", {}
    )


def features(request):
    """Features Landing page"""

    return render(
        request, "helpline/features.html", {}
    )


def calendly_auth(request):
    print('hello')
    params = {
        'response_type': 'code',
        'client_id': settings.CALENDLY_CLIENT_ID,
        'redirect_uri': settings.CALENDLY_REDIRECT_URI,
    }
    auth_url = f'https://auth.calendly.com/oauth/authorize?{"&".join(f"{key}={value}" for key, value in params.items())}'
    print(params)
    return redirect(auth_url)


def calendly_callback(request):
    code = request.GET.get('code')
    if code:
        params = {
            'grant_type': 'authorization_code',
            'client_id': settings.CALENDLY_CLIENT_ID,
            'client_secret': settings.CALENDLY_CLIENT_SECRET,
            'code': code,
            'redirect_uri': settings.CALENDLY_REDIRECT_URI,
        }
        response = requests.post('https://auth.calendly.com/oauth/token', data=params)
        if response.status_code == 200:
            data = response.json()
            access_token = data.get('access_token')
            if len(access_token) > 1000:
                 # Handle the error case, e.g., display a message to the user or log it
                return HttpResponse('Calendly access token is too long.')
            # Store the access token in the database for the logged-in user
            if request.user.is_authenticated:
                AccessToken.objects.update_or_create(user=request.user, defaults={'access_token': access_token})

            # Redirect the user to the success page or render a template with success message
            return redirect('get_user_events')  # Replace with your success view name
        else:
            # Handle the error case, redirect to an error view or render a template with error message
            return redirect('error_view')  # Replace with your error view name
    else:
        # Handle the case where 'code' parameter is missing in the request
        # Redirect to an error view or render a template with error message
        return redirect('success_view')  # Replace with your error view name

def get_user_events(request):
    user = request.user
    try:
        access_token = AccessToken.objects.get(user=user).access_token
    except AccessToken.DoesNotExist:
        # If the access token doesn't exist, obtain it from Calendly OAuth flow
        code = request.GET.get('code')
        if code:
            params = {
                'grant_type': 'authorization_code',
                'client_id': settings.CALENDLY_CLIENT_ID,
                'client_secret': settings.CALENDLY_CLIENT_SECRET,
                'code': code,
                'redirect_uri': settings.CALENDLY_REDIRECT_URI,
            }
            response = requests.post('https://auth.calendly.com/oauth/token', data=params)
            if response.status_code == 200:
                data = response.json()
                access_token = data.get('access_token')

                # Store the access token in the AccessToken model
                AccessToken.objects.create(user=user, access_token=access_token)

            else:
                # Handle the error case
                return HttpResponse('Something went wrong with Calendly OAuth.')

        else:
            # Handle the case where 'code' parameter is missing in the request

            return HttpResponse('Calendly OAuth code not found.')

    user_url = 'https://api.calendly.com/users/me'
    user_headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    user_response = requests.get(user_url, headers=user_headers)

    if user_response.status_code == 200:
        user_data = user_response.json()
        user_uri = user_data.get('resource', {}).get('uri', '')

        organization_uri = user_data.get('resource', {}).get('current_organization', '')


    else:
        return HttpResponse('Failed to fetch user ID from Calendly API.')

   # url = f'https://api.calendly.com/scheduled_events?user={user_id.strip()}'  # Include user ID in the URL
  # Using the user's scheduling URL to get events

    events_url = f'https://api.calendly.com/scheduled_events?user={user_uri}&organization={organization_uri}'


    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    response = requests.get(events_url, headers=headers)
    print(f"User ID: {user_uri}")

    print(user_response.status_code)
    print(user_response.text)
    print(headers)
    print(response.status_code)
    print(response.text)

    if response.status_code == 200:
        print("Hello World!")
        data = response.json()
        events = data.get('data', [])

        print(events)  # Print the contents of the 'events' variable to inspect the data

        # Process the events data as per your requirements
        logger.debug(events)
        return render(request, 'helpline/home_dashboard.html', {'events': events})
    else:
        # Handle the error case
        return HttpResponse('Something went wrong with Calendly API.')


def error_view(request):
    return render(request, 'error.html')


def success_view(request):
    return render(request, 'success.html')

@login_required
def home(request):
    "Dashboard home"

    try:
        helpline_user = request.user.HelplineUser
    except Exception as e:
        # If user does not have a helpline account
        # We initialize it here
        new = initialize_myaccount(request.user)
        return redirect("/@%s/#new=%s" % (request.user.username, new))

    case_search_form = CaseSearchForm()
    queue_form = QueueLogForm(request.POST)
    queue_pause_form = QueuePauseForm()
    page = request.GET.get("page", 1)
    try:
        user_email_domain = request.user.email.split('@')[-1]
    except:
        user_email_domain = None

    # Dashboard stats will be None for default values
    # These values will then be populated through async javascript
    dashboard_stats = {}

    return render(
        request,
        'helpline/home.html',
        {
            'case_search_form': case_search_form,
            'dashboard_stats': dashboard_stats,
            'queue_form': queue_form,
            'queue_pause_form': queue_pause_form,
            'user_email_domain': user_email_domain,
            'page': page
        }
    )


@json_view
@login_required
def home_dashboard(request):
    """Home dashboard stats"""

    CDR_TABLE_CACHE_TIMEOUT = 5  # How long to store CDR Table data in cache
    DASHBOARD_STATS_CACHE_TIMEOUT = 5  # How long to cache CDR Stats

    case_search_form = CaseSearchForm()
    queue_form = QueueLogForm(request.POST)
    queue_pause_form = QueuePauseForm()
    # Get dashboard stats from cache
    dashboard_stats = cache.get(
        'dashboard_stats_%s' % (request.user)
    )
    # Set dashboard stats to cache
    if not dashboard_stats:
        try:
            cache.set(
                'dashboard_stats_%s' % (request.user),
                get_dashboard_stats(request.user),
                DASHBOARD_STATS_CACHE_TIMEOUT
            )
            dashboard_stats = cache.get(
                'dashboard_stats_%s' % (request.user)
            )
        except Exception as e:
            dashboard_stats = None

    # Get the all available hot desks who's secret is not null
    hot_desks = cache.get_or_set(
        'user_hotdesks_%s' % (request.user),
        Hotdesk.objects.filter(
            user=request.user,
            status='Available',
            secret__isnull=False
        ),
        CDR_TABLE_CACHE_TIMEOUT
    )
    # Get call history from cache or set based on hot desk objects
    call_history_table = cache.get(
        '-'.join(str(hot_desk) for hot_desk in hot_desks)
    )
    if not call_history_table:
        try:
            extensions = [hotdesk.extension for hotdesk in hot_desks]
            cache.set(
                '-'.join(str(hot_desk) for hot_desk in hot_desks),
                get_call_history_table(extensions),
                DASHBOARD_STATS_CACHE_TIMEOUT
            )
            call_history_table = cache.get(
                '-'.join(str(hot_desk) for hot_desk in hot_desks)
            )
        except Exception as e:
            call_history_table = None

    if call_history_table:
        call_history_table.paginate(
            page=request.GET.get("page", 1), per_page=10
        )
    dashboard_html = render_to_string(
        'helpline/home_dashboard.html',
        {
            'case_search_form': case_search_form,
            'dashboard_stats': dashboard_stats,
            'queue_form': queue_form,
            'queue_pause_form': queue_pause_form,
            'call_history_table': call_history_table
        },
        request
    )
    return {
        'result': "Success",
        'data': dashboard_html,
        'dashboard_stats': dashboard_stats
    }


@login_required
@json_view
def leta(request):
    """Return the login duration and ready duration"""
    login_duration = request.user.HelplineUser.get_login_duration()
    ready_duration = request.user.HelplineUser.get_ready_duration()
    data = {
        'login_duration': login_duration,
        'ready_duration': ready_duration
    }
    return {'data': data}


@login_required
def check(request):
    """Show login duration. Returns blank template"""
    return render(request, 'helpline/leta.html')


def get_schedules(user):
    """Get schedules for a user, use cache"""
    SCHEDULE_LIST_CACHE_TIMEOUT = 5
    data = cache.get_or_set(
        'user_schedule_%s' % (user),
        Schedule.objects.filter(user=user).distinct('service'),
        SCHEDULE_LIST_CACHE_TIMEOUT
    )
    return data


@login_required
@json_view
def hotdesk_makeprimary(request):
    """Make hotdesk primary given exten"""
    sip_authuser = request.GET.get("sip_authuser")
    try:
        cache.delete(f'user_hotdesk_{request.user}')
    except:
        pass
    try:
        hotdesk = Hotdesk.objects.get(extension=sip_authuser, user=request.user)
    except Exception as e:
        return {"success": False, "error": str(e)}

    if not hotdesk.primary:
        hotdesk.primary = True
        hotdesk.save()
        return ({"success": True})
    else:
        return ({"success": False})


def get_active_hotdesks(schedules):
    """Get active user hotdesk objects from schedule list
    Active hotdesks means is assigned a hotdesk on their profile"""
    hotdesks = []
    for schedule in schedules:
        try:
            # We identify hotdesk's by the Extension number
            hotdesk = get_hotdesk(schedule.user)
            extension = hotdesk.extension
            extension_type = hotdesk.extension_type
        except Exception as e:
            extension = None

        if extension:
            full_name = schedule.user.get_full_name()
            hotdesks.append(
                {
                    'text': "%s (%s)" % (full_name, schedule.user.username),
                    'value': "%s/%s" % (extension_type, extension)
                }
            )
    return hotdesks


@login_required
@json_view
def get_team_schedule(request):
    """Get team list and their active softphones"""
    hotdesks = cache.get_or_set(
        'team_hotdesks_%s' % (request.user),
        get_team_hotdesks(request.user),
        7200
    )

    return hotdesks


def get_team_hotdesks(user):
    """Get current active hotdesks for team members"""
    schedules = get_schedules(user)
    user_services = schedules.values_list('service', flat=True)
    # Get other members who share a common schedule
    # Exclude DEMO users
    DEMO_SERVICE_ID = 1

    data = cache.get_or_set(
        'team_schedules_%s' % (user),
        Schedule.objects.exclude(
            service=DEMO_SERVICE_ID
        ).filter(
            service__in=user_services
        ).distinct('user'),
        7200
    )
    hotdesks = cache.get_or_set(
        'team_active_hotdesk_%s' % (user),
        get_active_hotdesks(data)
    )
    return hotdesks


@login_required
def check_call(request):
    """Check if there is a call for request user"""

    # Case ID is set by the PBX
    # When a call comes in a case object is created and assiend to the user
    # We use the sequence value in the database
    try:
        case_id = request.user.HelplineUser.case_id
    except:
        return JsonResponse({'my_case': None})

    # Unique ID is mostly for security
    # We don't want users to check every case id since it's sequential
    uniqueid = None

    # Quick hack for testing
    # Returns a case id for 45 when in dev mode
    if request.GET.get('dev_mode') == "1":
        case_id = 45

    # Get a case object from the case id
    # Case objects can then be manipulated
    if case_id:
        my_case = Case.objects.get(hl_case=case_id)
    else:
        my_case = request.user.HelplineUser.case

    if my_case:
        # If case object is found, set popup status as "Done"
        # This can only be called once
        my_case.hl_popup = 'Done'
        my_case.save()

        # Remove case object from user profile once popup is done an user is alerted
        request.user.HelplineUser.case = None
        request.user.HelplineUser.save()
        uniqueid = my_case.hl_unique

        # Case objects should have a coresponding "Report" object.
        # Report objects have more data, like cdr data
        # Using a try and asking for forgiveness if not found
        try:
            report = Report.objects.get(case=my_case)
        except:
            return JsonResponse({'my_case': None})

        # Call type should be, Inbound or Outbound
        call_type = report.calltype if report else 0
        # Report objects also have the phone number
        telephone = report.telephone
        user_email = request.user.email

        # Get or create contact by using the phone number
        # We should start processing this in E.164 here in future
        contact, contact_created = Contact.objects.get_or_create(
            hl_contact=telephone)

        if contact_created or not contact.address:
            # Address stores additional data about the contact
            # A separate address object allows us to have multiple people with same phone number (contact)
            # If it's a new Address, we set the creator in the user field for that address
            address = Address(user=request.user)
            contact.address = address
            address.save()
            contact.save()

        # Get and format External URL
        external_url = report.service.external_url
        if external_url:
            external_url_template = external_url.urltemplate
            external_url_opentype = external_url.opentype
            external_url_status = external_url.status
        else:
            external_url_template = None
            external_url_opentype = None
            external_url_status = None

    else:
        telephone = None
        my_case = None
        external_url = None
        external_url_template = None
        external_url_status = None
        external_url_opentype = None
        call_type = None
        user_email = None

    try:
        caller_name = contact.address.hl_names
        service_name = report.service.name
    except:
        caller_name = _("Unknown contact")
        service_name = None

    # This is 482 B of garbage if there is no case data
    # TODO: Optimize this
    response = JsonResponse(
        {
            'my_case': my_case.hl_case if my_case else None,
            'telephone': telephone,
            'uniqueid': uniqueid,
            'service': service_name,
            'name': caller_name,
            'agent_email':  user_email,
            'external_url_template': external_url_template,
            'external_url_opentype': external_url_opentype,
            'external_url_status': external_url_status,
            'calltype': call_type
        }
    )
    return response


@csrf_exempt
def get_districts(request):
    """Return option field with list of districts from Address table"""
    if request.method == 'POST':
        districts = Postcode.objects.values_list(
            'address3', flat=True).distinct()

    districts = Postcode.objects.values_list('address2', flat=True).distinct()
    return render(request, 'helpline/options.html', {
        'options': districts})


@login_required
def myaccount(request):
    """View request user account details page"""
    user = request.user
    form = MyAccountForm(request.POST or None, instance=request.user)
    tfa_enabled = True if default_device(user) else False
    return render(request, 'helpline/profile.html',
                  {'form': form,
                   'tfa_enabled': tfa_enabled})


@login_required
def profile(request, username):
    """User profiles view and edit."""
    form = MyAccountForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
    username = username.strip("@")
    content_user = get_object_or_404(User, username__iexact=username)

    tfa_enabled = True if default_device(content_user) else False
    data = {}
    data['applications'] = get_application_model().objects.filter(user=request.user)
    data['is_owner'] = request.user == content_user
    data['content_user'] = content_user
    data['form'] = form
    data['tfa_enabled'] = tfa_enabled
    data['email_verfied'] = EmailAddress.objects.filter(
        user=request.user, verified=True).exists()

    return render(request, 'helpline/profile.html', data)


@login_required
def manage_users(request):
    """View user management page"""
    return render(request, 'helpline/myaccount.html')


@login_required
@json_view
@csrf_exempt
def queue_log(request):
    """Join Asterisk queues."""
    if request.method == 'POST':
        queue_form = QueueLogForm(request.POST)
        agent = request.user.HelplineUser

        if queue_form.is_valid():
            extension = queue_form.cleaned_data.get('softphone')
            if not queue_form.cleaned_data.get('softphone'):
                request.session.get('extension')

            selected_queue = queue_form.cleaned_data.get('queue')
            try:
                # Get the hotline object from the extension.
                hotdesk = Hotdesk.objects.get(extension=extension)

                hotdesk.jabber = 'helpline@jabber'
                hotdesk.status = 'Available'
                hotdesk.agent = request.user.HelplineUser.hl_key
                hotdesk.user = request.user

                agent.hl_status = 'Available'
                agent.hl_exten = "%s/%s" % (hotdesk.extension_type,
                                            hotdesk.extension)

                hotdesk.save()
                agent.save()
                full_name = request.user.get_full_name()
                member_name = full_name if full_name else request.user.username

                backend = get_backend(request.user)
                message = backend.add_to_queue(
                    queue=selected_queue,
                    interface=agent.hl_exten,
                    member_name=member_name
                )

                request.session['queuejoin'] = 'join'
                request.session['queuestatus'] = 'queuepause'
                request.session['extension'] = extension

            except Exception as e:
                message = e

            return {
                'message': message,
                'selected_queue': selected_queue,
                'interface': agent.hl_exten,
                'backend': hotdesk.backend_manager_config.name,
                'extension': extension
            }

    message = "Only POST ALLOWED"
    return {'message': message}


@json_view
def queue_leave(request):
    """Leave Asterisk queues."""
    try:
        backend = get_backend(request.user)
        hotdesk = get_hotdesk(request.user)

        queue = request.POST.get('queue')
        agent = "SIP/%s" % (request.POST.get('extension'))

        queue = realname_queue_rename(queue)

        # Get service object by queue number
        service = Service.objects.get(
            queue=queue,
            backend_manager_config=hotdesk.backend_manager_config,
        )

        # Check if service is managed
        # Users cannot leave a managed Queue
        if service.managed:
            return {
                "success": False,
                "message": {
                    "Response": "failed",
                    "Message": "Managed Queue, contact your administrator",
                },
            }

        message = backend.remove_from_queue(
            agent=agent,
            queue=queue
        )
        clock = Clock()
        clock.user = request.user
        clock.hl_clock = "Queue Leave"
        clock.service = service
        clock.hl_time = int(time.time())
        clock.save()

        return {"success": True, "message": message}
    except Exception as e:
        return {"success": False, "message": str(e)}


@json_view
@csrf_exempt
def queue_remove(request, auth):
    """Remove a user from the Asterisk queue."""
    agent = HelplineUser.objects.get(hl_auth=auth)
    agent.hl_status = 'Idle'
    backend = get_backend(request.user)

    try:
        hotdesk = Hotdesk.objects.filter(agent__exact=agent.hl_key)
        hotdesk.update(agent=0)
        agent.hl_exten = ''
        agent.hl_jabber = ''
        schedules = Schedule.objects.filter(user=agent.user)
        if schedules:
            for schedule in schedules:
                data = backend.remove_from_queue(
                    agent="SIP/%s" % (request.session.get('extension')),
                    queue='%s' % (schedule.service.queue),
                )
        else:
            data = _("Agent does not have any assigned schedule")
        agent.save()

    except Exception as e:
        data = e

    return redirect("/helpline/status/web/presence/#%s" % (data))


@json_view
def queue_pause(request):
    """Pause Asterisk Queue member"""
    queue = request.POST.get('queue')
    reason = request.POST.get('reason')
    backend = get_backend(request.user)
    hotdesk = get_hotdesk(request.user)
    service = Service.objects.get(
        queue=queue,
        backend_manager_config=hotdesk.backend_manager_config,
    )
    queue = realname_queue_rename(queue)

    # Get break reason or create new break if not specifed by name
    try:
        break_reason = Break.objects.get(name=reason)
    except Break.DoesNotExist:
        break_reason = Break(name=reason, description=reason, status='A')
        break_reason.save()

    message = backend.pause_queue_member(
        queue='%s' % (queue),
        interface='%s' % (request.user.HelplineUser.hl_exten),
        paused=True,
        reason=reason
    )
    clock = Clock()
    clock.user = request.user
    clock.hl_clock = "Pause"
    clock.break_reason = break_reason
    clock.service = service
    clock.hl_time = int(time.time())
    clock.save()

    return {'message': message, 'reason': reason, 'queue': queue}


@json_view
@login_required
def send_invite(request):
    """Send invite to user"""
    emails = request.POST.get('email')
    emails = emails.split()
    for email in emails:
        Invitation = get_invitation_model()
        invite = Invitation.create(email.strip(), inviter=request.user)
        invite.send_invitation(request)
    return {'message': "Success"}


@login_required
def my_invitations(request):
    """Return table of sent invitations"""
    sort = request.GET.get('sort', 'sent')
    Invitation = get_invitation_model()
    invites = Invitation.objects.filter(inviter_id=request.user.id)
    invite_table = InvitationTable(
        invites,
        order_by=sort
    )
    return render(
        request, 'helpline/my_invitations.html', {
            'table': invite_table,
        }
    )


@json_view
def queue_unpause(request):
    """Unpause Asterisk Queue member"""
    queue_name = request.POST.get('queue')
    interface = "SIP/" + request.POST.get('extension')
    backend = get_backend(request.user)
    hotdesk = get_hotdesk(request.user)

    # Send request to backend
    # Errors like GoneAwayError could be returned
    try:
        message = backend.pause_queue_member(
            queue=queue_name,
            interface=interface,
            paused=False
        )
    except Exception as e:
        message = str(e)

    service = Service.objects.get(
        queue=queue_name,
        backend_manager_config=hotdesk.backend_manager_config,
    )
    clock = Clock()
    clock.hl_clock = "Unpause"
    clock.user = request.user
    clock.service = service
    clock.hl_time = int(time.time())
    clock.save()

    return {'message': message}


def walkin(request):
    """Render walkin  manualy."""
    form = ContactForm()

    return render(request, 'helpline/walkin.html',
                  {'form': form})


def callform(request):
    """Render call form"""
    return render(request, 'helpline/callform.html')


def faq(request):
    """Render FAQ app"""
    return render(request, 'helpline/callform.html')


@register.filter
def get_item(dictionary, key):
    """Template filter for dictionary manipulation"""
    return dictionary.get(key, "")


@login_required
def reports(request, report, casetype='Call'):
    """Report processing and rendering"""

    # Data view displays submission data.
    query = request.GET.get('q', '')
    datetime_range = request.GET.get("datetime_range")
    agent = request.GET.get("agent")
    category = request.GET.get("category", "")
    form = ReportFilterForm(request.GET)

    sort = request.GET.get('sort')
    report_title = {report: _(str(report).capitalize() + " Reports")}

    table = report_factory(report=report,
                           datetime_range=datetime_range,
                           agent=agent,
                           query=query, sort=sort,
                           category=category,
                           casetype=casetype,
                           user=request.user)

    # Export table to csv
    export_format = request.GET.get('_export', None)
    if TableExport.is_valid_format(export_format):
        exporter = TableExport(export_format, table)
        return exporter.response('table.{}'.format(export_format))
    table.paginate(page=request.GET.get('page', 1), per_page=10)

    data = {
        'title': report_title.get(report),
        'report': report,
        'form': form,
        'datetime_range': datetime_range,
        'table': table,
        'query': query,
    }

    htmltemplate = "helpline/reports.html"

    return render(request, htmltemplate, data)


def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


@login_required
def report_charts(request, report, casetype='Call'):
    """Return charts for the last 4 days based on the Call Summary Data"""
    # The ussual filters.
    query = request.GET.get('q', '')
    interval = request.GET.get('interval', 'daily')
    category = request.GET.get('category', '')
    if report == 'categorysummary':
        y_axis = 'category'
    elif report == 'dailysummary':
        y_axis = 'daily'
    else:
        y_axis = request.GET.get('y_axis', '')

    datetime_range = request.GET.get("datetime_range")
    agent = request.GET.get("agent")
    form = ReportFilterForm(request.GET)
    # Update the search url to chart based views.
    search_url = reverse('report_charts', kwargs={'report': report})

    # Convert date range string to datetime object
    if datetime_range:
        try:
            a, b = [datetime_range.split(" - ")[0],
                    datetime_range.split(" - ")[1]]
            from_date = datetime.strptime(a, '%m/%d/%Y %I:%M %p')
            to_date = datetime.strptime(b, '%m/%d/%Y %I:%M %p')

            current = from_date

            delta = to_date - from_date
            date_list = []
            if interval == 'hourly':
                for i in range(int(delta.total_seconds()//3600)):
                    date_list.append(from_date + timedelta(seconds=i*3600))
            elif interval == 'monthly':
                while current <= to_date:
                    current += relativedelta(months=1)
                    date_list.append(current)
            elif interval == 'weekly':
                while current <= to_date:
                    current += relativedelta(weeks=1)
                    date_list.append(current)
            else:
                while current <= to_date:
                    current += relativedelta(days=1)
                    date_list.append(current)

            epoch_list = [date_item.strftime('%m/%d/%Y %I:%M %p')
                          for date_item in date_list]

            # Add filter to ajax query string.
        except Exception as e:
            from_date = None
            to_date = None
    else:
        from_date = None
        to_date = None

        # Start date
        base = datetime.today()
        date_list = [base - timedelta(days=x) for x in range(0, 3)]
        epoch_list = [date_item.strftime('%m/%d/%Y %I:%M %p')
                      for date_item in date_list]
        epoch_list.reverse()
    e = None

    datetime_ranges = pairwise(epoch_list)
    callsummary_data = []
    total_calls = 0
    for datetime_range in datetime_ranges:
        # Date time list returns desending. We want assending.
        datetime_range_string = " - ".join(datetime_range)
        if y_axis == 'category':
            categories = [
                i[0] for i in Category.objects.values_list(
                    'hl_category').distinct()]
            for category in categories:
                report_data = report_factory(
                    report='chartreport',
                    datetime_range=datetime_range_string,
                    agent=agent,
                    query=query,
                    category=category,
                    casetype=casetype,
                    user=request.user
                )

                # Append data to tables list.
                callsummary_data.append(report_data)
                total_calls = total_calls + report_data.get(
                    'total_offered').get('count')
        else:
            report_data = report_factory(report='chartreport',
                                         datetime_range=datetime_range_string,
                                         agent=agent,
                                         query=query,
                                         category=category,
                                         casetype=casetype,
                                         user=request.user
                                        )

            # Append data to tables list.
            callsummary_data.append(report_data)
            total_calls = total_calls + report_data.get(
                'total_offered').get('count')

    # Multibar chart page.
    if y_axis != 'daily':
        summary_table = CallSummaryTable(callsummary_data)
    tooltip_date = "%d %b %Y %H:%M:%S %p"
    extra_serie = {"tooltip": {"y_start": "There are ", "y_end": " calls"},
                   "date_format": tooltip_date}

    if y_axis == 'category':
        categories = [i[0] for i in Category.objects.values_list('hl_category').distinct()]

        chartdata = {
            'x': epoch_list,
        }
        for i in range(len(categories)):
            chartdata['name%s' % str(i+1)] = categories[i]
            category_related = []
            for data in callsummary_data:
                if data.get('category') == categories[i]:
                    category_related.append(data)
            chartdata['y%s' % str(i+1)] = [d.get('total_offered').get('count')
                                           for d in category_related]
            chartdata['extra%s' % str(i+1)] = extra_serie
    elif y_axis == 'daily':
        daysummary_data = []
        month_names = []
        day_names = list(calendar.day_name)
        chartdata = {}
        day_related = {}
        for day_name in day_names:
            day_related[day_name] = []

        for i in range(len(day_names)):
            day_summary = {}
            chartdata['name%s' % str(i+1)] = day_names[i]
            day_total_offered = 0
            month_name = 'None'
            for data in callsummary_data:
                if data.get('day') == day_names[i]:
                    day_related[day_names[i]].append(data)
                    day_total_offered = day_total_offered + data.get(
                        'total_offered').get('count')
                    day_related[day_names[i]][-1][
                        'day_total_offered'] = day_total_offered
                    month_name = data.get('month')

            day_summary['month'] = month_name
            month_names.append(month_name)
            day_summary['%s' % (day_names[i].lower())] = day_total_offered
            chartdata['y%s' % str(i+1)] = [d.get('day_total_offered')
                                           for d in day_related[day_names[i]]]
            chartdata['extra%s' % str(i+1)] = extra_serie
            chartdata['x'] = month_names
            daysummary_data.append(day_summary)
    else:

        ydata = [d.get('total_offered').get('count') for d in callsummary_data]
        ydata2 = [d.get('total_answered') for d in callsummary_data]
        ydata3 = [d.get('total_abandoned') for d in callsummary_data]

        chartdata = {
            'x': epoch_list,
            'name1': 'Total Offered', 'y1': ydata, 'extra1': extra_serie,
            'name2': 'Total Answered', 'y2': ydata2, 'extra2': extra_serie,
            'name3': 'Total Abandoned', 'y3': ydata3, 'extra3': extra_serie,
        }

    charttype = "multiBarChart"
    chartcontainer = 'multibarchart_container'  # container name
    if y_axis == 'daily':
        summary_table = DaySummaryTable(daysummary_data)

    export_format = request.GET.get('_export', None)
    if TableExport.is_valid_format(export_format):
        exporter = TableExport(export_format, summary_table)
        return exporter.response('table.{}'.format(export_format))

    data = {
        'title': 'callsummary',
        'form': form,
        'summary_table': summary_table,
        'datetime_ranges_number': len(list(datetime_ranges)),
        'error': e,
        'y_axis': y_axis,
        'search_url': search_url,
        'total_calls': total_calls,
        'charttype': charttype,
        'casetype': casetype,
        'chartdata': chartdata,
        'chartcontainer': chartcontainer,
        'extra': {
            'name': 'Call data',
            'x_is_date': False,
            'x_axis_format': '',
            'tag_script_js': True,
            'jquery_on_ready': True,
        },
    }

    if report == 'ajax':
        return render(request, 'helpline/report_charts_factory.html', data)
    else:
        return render(request, 'helpline/report_charts.html', data)


def autolocation(request):
    """Get districts"""
    districts = request.GET['districts']
    return render(request, 'helpline/locations.html', {
        'districts': districts})


def queue_manager(user, extension, action, queue=None):
    """queuejoin:queueleave:queuepause:queueunpause:queuetrain"""
    backend = get_backend(user)
    full_name = user.get_full_name()
    member_name = full_name if full_name else user.username
    if action == 'queuejoin':
        data = backend.add_to_queue(
            interface="SIP/%s" % (extension),
            queue=queue,
            member_name=member_name
        )
    elif action == 'queueleave':
        data = backend.remove_from_queue(
            interface="SIP/%s" % (extension),
            queue=queue,
        )
    return data


@login_required
@json_view
def add_user_to_queue(request):
    """Add user to a queue
    Create a Schedule object for this user to allow them to join later"""
    backend = get_backend(request.user)
    queue_name = request.POST.get('queue')
    extension = request.POST.get('extension').split('/')[1]
    hotdesk = Hotdesk.objects.get(extension=extension)
    service = backend.get_service(queue_name)
    schedule_created = False

    if service:
        queue_name = service.queue if service.queue else queue_name
        try:
            schedule, schedule_created = Schedule.objects.get_or_create(
                user=hotdesk.user,
                service=service,
                hl_status="Added"  # Mark as Added by admin/Supervisor
            )
        except:
            schedule_created = False

        # If a schedule object is create, send a notification to user
        if schedule_created:
            description = f'{request.user} added you to {service.name}'
            verb = "added you to queue"
            notify.send(request.user, recipient=hotdesk.user, verb=verb,
                        description=description, level="info")

    data = queue_manager(
        hotdesk.user,
        extension=extension,
        action="queuejoin",
        queue=queue_name
    )

    return {
        'message': data,
        "schedule_created": schedule_created,
        'queue_name': queue_name,
    }


@login_required
def case_form(request, form_name):
    """Handle Walkin and CaseDetailForm POST and GET Requests"""
    data = {}

    if request.method == 'GET':
        case_number = request.GET.get('case')
        uniqueid = request.GET.get('uniqueid')
        data['contact_form'] = ContactForm()
        # Legacy call forms
        data['case_detail_form'] = CaseDetailForm()
        data['case_action_form'] = CaseActionForm()
        data['contact_search_form'] = ContactSearchForm()
        data['form_name'] = form_name
        data['uniqueid'] = uniqueid
        if case_number:
            try:
                my_case = int(case_number)
            except ValueError:
                raise Http404(_("Case not found"))
            my_case = get_object_or_404(Case, hl_case=case_number)

            # Check if Unique id in case is the same as GET uniquid
            # This is an extra layer of security case data
            if my_case.hl_unique != uniqueid:
                raise Http404(_("Case not found"))

            report, contact, address = get_case_info(case_number)
            user_schedule = Schedule.objects.filter(user=request.user, service=report.service)
            # Check if user is allowed to view case information
            if user_schedule:
                data['user_schedule'] = user_schedule
            else:
                data['user_schedule'] = False

            case_history = Report.objects.using('reportingdb').filter(
                telephone=contact.hl_contact).order_by('-hl_time')
            case_history_table = CaseHistoryTable(case_history)

            # Initial case data
            data['case'] = my_case
            data['report'] = report
            data['contact'] = contact
            data['address'] = address
            data['disposition_form'] = DispositionForm(
                initial={'case_number': case_number,
                         'disposition': my_case.hl_disposition})
            data['case_history_table'] = case_history_table
            data['contact_form'] = ContactForm(
                initial={
                    'caller_name': address.hl_names,
                    'gender': address.hl_gender,
                    'email': address.hl_email,
                    'company': address.hl_company,
                    'phone_number': contact.hl_contact,
                    'case_number': my_case,
                }
            )
            data['case_action_form'] = CaseActionForm(
                initial={
                    'case_number': my_case,
                    'case_status': report.casestatus
                }
            )
            # Append case number to case details json
            case_details = my_case.case_detail if my_case.case_detail else {}
            case_details['case_number'] = my_case

            data['case_detail_form'] = CaseDetailForm(initial=case_details)

            try:
                case_history_table.paginate(
                    page=request.GET.get('page', 1), per_page=10)
            except Exception as e:
                # Do not paginate if there is an error
                pass

        # GET request without Case ID
        # This could be a walkin form, so display contact search
        else:
            data['disposition_form'] = DispositionForm()

        return render(request, "helpline/case_form.html", data)


class DashboardTable(tables.Table):
    """Where most of the dashboard reporting happens"""
    casetype = tables.TemplateColumn("<b>{{ record.get_call_type }}</b>",
                                     verbose_name="Call Type")
    case_id = tables.TemplateColumn(
        '{% if record.case %}<a href="{{ record.get_absolute_url }}">\
        {{record.case }}</a>{% else %}-{% endif %}')
    telephone = tables.TemplateColumn(
        '<a href="sip:{{record.telephone}}">{{record.telephone}}</a>')
    user_id = tables.TemplateColumn("{{ record.user }}", verbose_name="Agent")
    callstart = tables.columns.DateTimeColumn(format="H:i:s")
    callend = tables.columns.DateTimeColumn(format="H:i:s")
    service_id = tables.TemplateColumn("{{ record.service }}",
                                       verbose_name="Service")
    disposition = tables.Column(accessor='case.hl_disposition',
                                verbose_name="Disposition")
    category = tables.Column(accessor='case.case_detail.category',
                                verbose_name="Category")
    sub_category = tables.Column(accessor='case.case_detail.sub_category',
                                verbose_name="Sub-Category")
    partner = tables.Column(accessor='case.case_detail.partner',
                                verbose_name="Partner")
    category = tables.Column(accessor='case.case_detail.category',
                                verbose_name="Category")
    sub_category = tables.Column(accessor='case.case_detail.sub_category',
                                verbose_name="Sub-Category")
    scheme = tables.Column(accessor='case.case_detail.scheme',
                                verbose_name="Scheme")
    comment = tables.Column(accessor='case.case_detail.comment',
                                verbose_name="Comment")

    export_formats = ['csv', 'xls']

    class Meta:
        model = Report
        attrs = {'class': 'table table-bordered table-striped dataTable',
                 'id': 'report_table example1'}
        unlocalise = ('holdtime', 'walkintime', 'talktime', 'callstart',
                      'callend')
        fields = {'casetype', 'case_id', 'telephone', 'calldate',
                  'service_id', 'user_id',
                  'calldate', 'callstart', 'callend', 'talktime', 'holdtime',
                  'calltype', 'disposition', 'casestatus',
                  'callernames', 'partner', 'comment'}

        sequence = ('casetype', 'case_id', 'callernames', 'calldate', 'callstart',
                    'callend', 'user_id', 'telephone',
                    'service_id', 'talktime', 'holdtime', 'calltype',
                    'category', 'sub_category',
                    'disposition', 'casestatus', 'partner', 'scheme', 'comment')


class WebPresenceTable(tables.Table):
    """Web presence table"""
    class Meta:
        model = HelplineUser
        attrs = {'class': 'table table-bordered table-striped dataTable'}


class ScheduleAssignmentTable(tables.Table):
    """ Easily assign users to a service"""
    class Meta:
        model = User
        attrs = {'class': 'table table-striped'}
        row_attrs = {
            "data-id": lambda record: record.pk
        }
        fields = ('id', 'username',)



class ScheduleTable(tables.Table):
    """Services list table"""
    service_template = """{{ record.service }}(<strong>{{ record.service.queue }}</strong>)
    <span id='queue_status_{{ record.service.queue }}'></span>"""
    queue_action_template = '''
    <div class="btn-group">
    <button onclick="unpause_agent('{{ record.service.queue }}');" type="button" class="btn btn-default btn-xs" title="Unpause Queue">
    <i class="fa fa-play"></i>
    </button>
    <button onclick="pause_agent('{{ record.service.queue }}');" type="button" class="btn btn-default btn-xs" title="Pause Queue">
    <i class="fa fa-pause"></i>
    </button>
    <button onclick="queue_join('{{ record.service.queue }}');" type="button" class="btn btn-default btn-xs" title="Join Queue">
    <i class="fa  fa-sign-in"></i>
    </button>
    <button onclick="queue_leave('{{ record.service.queue }}');" type="button" class="btn btn-default btn-xs" title="Leave Queue">
    <i class="fa fa-sign-out"></i>
    </button>
    </div>
                   '''
    service = tables.TemplateColumn(service_template)
    action = tables.TemplateColumn(queue_action_template,
                                   verbose_name="Queue Action")

    class Meta:
        model = Schedule
        attrs = {'class': 'table table-striped'}
        fields = {'service', 'action'}
        sequence = ('service', 'action')


class ContactTable(tables.Table):
    """Contact list table"""
    address = tables.Column(verbose_name='Name')
    hl_contact = tables.Column(verbose_name='Phone')
    action = tables.TemplateColumn('<button type="button" class="btn btn-default btn-xs" onClick="createCase(\'{{ record.hl_contact.strip }}\');"><i class="fa fa-plus"></i>Create Case</button>', verbose_name="Action")
    call = tables.TemplateColumn('<a type="button" class="btn btn-default btn-xs" onclick="$(\'#peer\').val({{ record.hl_contact.strip }});$(\'#call\').click();"><i class="fa fa-phone"></i>Call</a>', verbose_name="Call")
    class Meta:
        model = Contact
        fields = {'address', 'hl_contact'}
        attrs = {'class': 'table table-bordered table-striped dataTable'}


class CaseHistoryTable(tables.Table):
    """Show related Case form contact"""
    case = tables.TemplateColumn('{% if record.case %}<a href="{{ record.get_absolute_url }}">{{record.case }}</a>{% else %}-{% endif %}')
    class Meta:
        model = Report
        attrs = {'class': 'table table-bordered table-striped dataTable'}
        fields = {'case', 'user', 'calldate', 'calltype'}
        sequence = ('case', 'user', 'calldate', 'calltype')

        unlocalise = ('holdtime', 'walkintime', 'talktime', 'callstart')


class TimeSinceColumn(tables.Column):
    """Return time since formated as "00:00:00" """
    def render(self, value):
        time_since = float(time.time()) - float(value)
        idle_time = str(timedelta(seconds=time_since)) if value else "NA"
        return idle_time


class ConnectedAgentsTable(tables.Table):
    """Show connection information for agents"""
    login_duration = tables.TemplateColumn('''{% with login_duration=record.get_login_duration %}
                                            {{ login_duration.hours }}:{{ login_duration.min }}:{{ login_duration.seconds }}
                                            {% endwith %}''', orderable=False)
    hl_time = TimeSinceColumn(verbose_name='Idle Time')
    att = tables.TemplateColumn('''{% with att=record.get_average_talk_time %}
                                {{ att.hours }}:{{ att.min }}:{{ att.seconds }}
                                {% endwith %}
                               ''',orderable=False,verbose_name='Avg. Talk Time')

    aht = tables.TemplateColumn('''{% with aht=record.get_average_wait_time %}
                                {{ aht.hours }}:{{ aht.min }}:{{ aht.seconds }}
                                {% endwith %}
                               ''',orderable=False,verbose_name='Avg. Hold Time')
    ready = tables.TemplateColumn('''{% with rd=record.get_ready_duration %}
                                {{ rd.hours }}:{{ rd.min }}:{{ rd.seconds }}
                                {% endwith %}
                               ''',orderable=False,verbose_name='Ready')
    action = tables.TemplateColumn('''
                                   {% ifequal record.hl_status 'Available' %}
                                   <a href="{% url 'queue_remove' record.hl_auth %}">Remove from Queue</a>
                                   {% endifequal %}
                               ''',orderable=False,verbose_name='Action')
    class Meta:
        model = HelplineUser
        attrs = {'class' : 'table table-bordered table-striped', 'id':'report_table'}
        fields = {'hl_auth', 'hl_exten', 'hl_calls', 'hl_status', 'hl_names', 'hl_time'}
        sequence = ('hl_auth', 'hl_names', 'hl_calls', 'hl_exten', 'hl_time', 'hl_status')


class ReceievedColumn(tables.Column):
    """Return ctime from an epoch time stamp"""
    def render(self, value):
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(value))


class ServiceColumn(tables.Column):
    """Show service, customized template"""
    def render(self, value):
        return Service.objects.get(hl_key=value).hl_service


class AgentSessionTable(tables.Table):
    """Show agent activity"""
    hl_time = ReceievedColumn()

    class Meta:
        model = Clock
        fields = [
            'id', 'user', 'hl_clock', 'service', 'hl_time', 'break_reason'
        ]
        unlocalize = ['hl_time']
        attrs = {'class': 'table table-bordered table-striped dataTable',
                 'id': 'report_table'}

class ChatContactTable(tables.Table):
    """Show agent activity"""

    class Meta:
        model = Contact
        fields = {'hl_contact'}
        attrs = {'class': 'table table-bordered table-striped dataTable',
                 'id': 'chat-contacts-table'}


class InvitationTable(tables.Table):
    """Show intives sent"""
    sent = tables.DateTimeColumn(format ='M d Y, h:i A',
                                    verbose_name=_('Sent'))

    class Meta:
        model = get_invitation_model()
        fields = [
            'email', 'sent', 'accepted'
        ]
        attrs = {'class': 'table table-bordered table-striped dataTable',
                 'id': 'invitations-table'}


class CallSummaryTable(tables.Table):
    """Main call summary table"""
    service = tables.Column(orderable=False, verbose_name=_('Service(s)'))
    category = tables.Column(orderable=False, verbose_name=_('Category'))
    total_calls = tables.TemplateColumn(
        "<a href='{% url 'dashboardreports' 'totalcalls' record.total_offered.casetype %}?{{ record.total_offered.filter_query }}'>{{ record.total_offered.count }}</a>",
        orderable=False)
    total_answered = tables.TemplateColumn("<a href='{% url 'dashboardreports' 'answeredcalls' %}?{{ record.total_offered.filter_query }}'>{{ record.total_answered }}</a>",
                                           orderable=False)
    total_abandoned = tables.TemplateColumn("<a href='{% url 'dashboardreports' 'abandonedcalls' %}?{{ record.total_offered.filter_query }}'>{{ record.total_abandoned }}</a>",
                                            orderable=False)
    total_talktime = tables.Column(orderable=False)
    att = tables.Column(orderable=False, verbose_name=_('Average Talk Time'))
    aht = tables.Column(orderable=False, verbose_name=_('Average Hold Time'))
    sla_breached = tables.Column(orderable=False,
                                 verbose_name=_('SLA Breached'))
    sla_percentage = tables.Column(orderable=False,
                                   verbose_name=_('SLA Percentage'))
    answered_percentage = tables.Column(orderable=False,
                                        verbose_name=_('Answered Percentage'))
    abandoned_percentage = tables.Column(
        orderable=False,
        verbose_name=_('Abandoned Percentage'))
    export_formats = ['csv', 'xls']

    class Meta:
        attrs = {'class': 'table table-bordered table-striped dataTable',
                 'id': 'report_table'}


class CallHistoryTable(tables.Table):
    """Call History table from CDR Data"""
    src = tables.Column(verbose_name=_('Source'))
    dst = tables.Column(verbose_name=_('Destination'))
    calldate = tables.DateTimeColumn(format ='M d Y, h:i A',
                                    verbose_name=_('Date and Time'))
    duration = tables.Column()
    disposition = tables.TemplateColumn(
        """<span class='label \
        {% if record.disposition == 'ANSWERED' %}\
        label-success\
        {% elif record.disposition == 'NO ANSWER' %}\
        label-warning\
        {% else %}\
        label-danger\
        {% endif %}'>{{ record.disposition|title }}</span>\
        """,
        verbose_name=_('Status')
    )
    uniqueid = tables.TemplateColumn(
        """
        {% if record.disposition == 'ANSWERED' %}
        <a href="javascript:void(0);" onclick="javascript:audioPlayerLoad('{{ record.uniqueid }}');"><i class="fa fa-play-circle-o fa-lg" title="Play" type="button" data-toggle="modal" data-target="#modal-audio-player" id="play{{ record.uniqueid }}" style="float:left;"></i></a>&nbsp;<a class="downloadrecording" onclick="window.open('/helpline/get_recording/?uniqueid={{ record.uniqueid }}')" href="javascript:void(0);"><span class="helpleft"><i class="fa fa-download" style="margin-top:5px;"></i></span></a></td>
        {% endif %}
        """,
        verbose_name=_('Actions'))
    export_formats = ['csv', 'xls']

    def render_duration(self, value, record):
        return str(timedelta(seconds=value)) if value else "00:00:00"

    def render_actions(self, value, record):
        uniqueid = record.uniqueid

        return mark_safe('''
                         ''' % (record.uniqueid,uniqueid,uniqueid,uniqueid,value))

    class Meta:
        model = Cdr
        fields = ('src', 'dst', 'calldate', 'duration',
                  'disposition', 'uniqueid')
        attrs = {'class': 'table table-striped table-advance\
                 table-hover display nowrap dataTable dtr-inline collapsed',
                 'id': 'cdr_table'}


class DaySummaryTable(tables.Table):
    """Table to show call summary by day aggregate"""
    month = tables.Column(orderable=False, verbose_name='Month')
    monday = tables.Column(orderable=False, verbose_name='Monday')
    tuesday = tables.Column(orderable=False, verbose_name='Tuesday')
    wednesday = tables.Column(orderable=False, verbose_name='Wednesday')
    thursday = tables.Column(orderable=False, verbose_name='Thursday')
    friday = tables.Column(orderable=False, verbose_name='Friday')
    saturday = tables.Column(orderable=False, verbose_name='Saturday')
    sunday = tables.Column(orderable=False, verbose_name='Sunday')
    class Meta:
        attrs = {'class': 'table table-bordered table-striped dataTable',
                 'id': 'report_table'}


def get_case_info(case_number):
    """ Get related case information from a case number"""
    report = get_object_or_404(Report, case_id=case_number)
    contact, contact_created = Contact.objects.get_or_create(
        hl_contact=report.telephone
    )
    # Create a new address entry if new contact
    if contact_created:
        address = Address(user=report.user)
        address.save()
        contact.address = address
        contact.save()
    elif contact.address is None:
        address = Address(user=report.user)
        address.save()
        contact.address = address
        contact.save()
    else:
        address = contact.address

    return report, contact, address


@json_view
def save_contact_form(request):
    """Save contact/address form returns json status
    If there is no case number we create a case and contact"""
    contact_form = ContactForm(request.POST or None)
    if contact_form.is_valid():
        case_number = contact_form.cleaned_data.get('case_number')
        telephone = contact_form.cleaned_data.get('phone_number')
        gender = contact_form.cleaned_data.get('gender')
        if case_number:
            report, contact, address = get_case_info(case_number)
        else:
            default_service = Service.objects.all().first()
            address = Address(user=request.user)
            address.save()
            contact, created_new_contact  = Contact.objects.get_or_create(
                hl_contact=telephone
            )
            contact.address = address
            case = Case()
            case.save()
            report = Report(case=case, user=request.user)
            case.contact = contact
            case.user = request.user
            case.hl_popup = 'No'
            case.save()
            report.case = case
            report.callstart = timezone.now().strftime('%H:%M:%S.%f')
            report.callend = timezone.now().strftime('%H:%M:%S.%f')
            report.calldate = timezone.now().strftime('%d-%m-%Y')
            report.queuename = default_service.queue
            report.service = default_service
            report.telephone = contact.hl_contact
            report.casetype = 'Walkin'
            report.save()
            hl_user = request.user.HelplineUser
            hl_user.case = case
            hl_user.hl_status = 'Busy'
            hl_user.save()

        contact.save()
        contact.address.hl_names = contact_form.cleaned_data.get('caller_name')
        contact.address.hl_gender = gender
        contact.address.hl_email = contact_form.cleaned_data.get('email')
        contact.address.hl_company = contact_form.cleaned_data.get('company')
        contact.address.save()
        report.address = address
        report.callernames = contact_form.cleaned_data.get('caller_name')
        report.save()

        return {'success': True, 'case_number': case_number}

    ctx = {}
    ctx.update(csrf(request))
    form_html = render_crispy_form(contact_form, context=ctx)
    return {'success': False, 'form_html': form_html}


@json_view
def save_case_detail(request):
    """Legacy save case details  form returns json status
    If there is no case number we return an error"""
    case_detail_form = CaseDetailForm(request.POST or None)
    if case_detail_form.is_valid():
        case_number = case_detail_form.cleaned_data.get('case_number')
        case = Case.objects.get(hl_case=case_number)
        case.case_detail = case_detail_form.cleaned_data
        case.save()

        return {"success": True, "case_detail": case.case_detail}
    else:
        ctx = {}
        ctx.update(csrf(request))
        form_html = render_crispy_form(case_detail_form, context=ctx)
        return {'success': False, 'form_html': form_html}



@json_view
def contact_search_form(request):
    """Search contact/address and returns html contact list"""

    form = ContactSearchForm(request.POST or None)
    if form.is_valid():
        query = form.cleaned_data.get('query')
        contacts = Contact.objects.filter(
            Q(address__hl_names__icontains=query) |
            Q(hl_contact__icontains=query)
        )
        table = ContactTable(contacts)
        table_html = render_to_string(
            'helpline/contacts.html',
            {
                'table': table
            }, request
        )
        return {'success': True, 'table_html': table_html}

    ctx = {}
    ctx.update(csrf(request))
    form_html = render_crispy_form(form, context=ctx)
    return {'success': False, 'form_html': form_html}


@json_view
def save_case_action(request):
    """Save case action returns json status"""
    form = CaseActionForm(request.POST or None)
    try:
        if form.is_valid():
            case_number = form.cleaned_data.get('case_number')
            report = Report.objects.get(case=case_number)
            case_status = form.cleaned_data.get('case_status')
            previous_case_status = report.casestatus
            report.casestatus = case_status
            report.casestatus = case_status
            report.save(update_fields=['casestatus'])

            return {
                'success': True,
                'case_status': report.casestatus,
                'case_number': case_number,
                'previous_case_status': previous_case_status
            }

        ctx = {}
        ctx.update(csrf(request))
        form_html = render_crispy_form(form, context=ctx)
        return {'success': False, 'form_html': form_html}
    except Exception as e:
        ctx = {}
        ctx.update(csrf(request))
        form_html = render_crispy_form(form, context=ctx)
        return {'success': False, 'form_html': form_html}


@json_view
def save_disposition_form(request):
    """Save disposition, uses AJAX and returns json status"""
    disposition = request.POST.get("disposition")
    form = DispositionForm(request.POST or None)

    form.fields['disposition'].choices = [(disposition, disposition)]
    if form.is_valid():
        case = Case.objects.get(hl_case=form.cleaned_data['case_number'])
        case.hl_disposition = form.cleaned_data['disposition']
        case.save()
        request.user.HelplineUser.hl_status = 'Available'
        request.user.HelplineUser.save()
        return {'success': True}
    ctx = {}
    ctx.update(csrf(request))
    form_html = render_crispy_form(form, context=ctx)
    return {'success': False, 'form_html': form_html}


@json_view
def contact_create_case(request):
    """Create a case for a contact and return the case url"""
    contact_id = request.POST.get('contact_id', None)
    default_service = Service.objects.all().first()
    if contact_id:
        contact, contact_created = Contact.objects.get_or_create(
            hl_contact=contact_id
        )
        case = Case(
            contact=contact,
            user=request.user,
            hl_popup='No'
        )
        case.save()
        report = Report()
        report.user = request.user
        report.case = case
        report.callstart = timezone.now().strftime('%H:%M:%S.%f')
        report.callend = timezone.now().strftime('%H:%M:%S.%f')
        report.calldate = timezone.now().strftime('%d-%m-%Y')
        report.queuename = default_service.queue
        report.service = default_service
        report.telephone = contact.hl_contact
        report.casetype = 'Walkin'
        report.save()
        hl_user = request.user.HelplineUser
        hl_user.case = case
        hl_user.hl_status = 'Busy'
        hl_user.save()
        return {'success': True, 'my_case': case.hl_case}
    ctx = {}
    ctx.update(csrf(request))
    return {'success': False}


@json_view
def average_talk_time(request):
    """Return the average talk time for current user, in json"""
    att = request.user.HelplineUser.get_average_talk_time()
    return att


@json_view
def average_hold_time(request):
    """Return the average hold time for current user, in json"""
    awt = request.user.HelplineUser.get_average_wait_time()
    return awt


def initialize_myaccount(user):
    """Initialize user account to call helpline"""
    try:
        myaccount = HelplineUser()
        myaccount.user_id = user.pk
        myaccount.hl_names = user.username
        myaccount.hl_nick = user.username
        myaccount.hl_key = randint(123456789, 999999999)
        myaccount.hl_auth = randint(1000, 9999)
        myaccount.hl_exten = 0
        myaccount.hl_calls = 0
        myaccount.hl_email = ''
        myaccount.hl_avatar = ''
        myaccount.hl_area = ''
        myaccount.hl_phone = ''
        myaccount.hl_branch = ''
        myaccount.hl_case = 0
        myaccount.hl_clock = 0
        myaccount.hl_time = 0
        myaccount.hl_status = 'Idle'
        # TODO: Update this so site specific
        myaccount.hl_jabber = "%s@%s" % (user.username, 'im.helpline.co.ke')
        myaccount.hl_pass = hashlib.md5("1234".encode('utf-8')).hexdigest()

        myaccount.hl_role = "Supervisor" if user.is_superuser else "Counsellor"
        # Default Service, which is the first service
        default_service = Service.objects.all().first()
        myschedule = Schedule()
        myschedule.user = user
        myschedule.service = default_service

        myschedule.hl_status = 'Offline'

        myschedule.save()
        myaccount.save()
        # Monitor platform use by notifing super users
        super_users = User.objects.filter(is_superuser=True)
        for u in super_users:
            description = "New User Created %s %s" % (
                user.username,
                user.email,
            )
            verb = "New User"

            notify.send(
                user, recipient=u, verb=verb,
                description=description,
                level="info"
            )
            send_mail(
                '%s' % (verb),
                description,
                'robots@zerxis.co.ke',
                [u.email],
                fail_silently=True,
            )
        return True

    except Exception as e:
        return e


def edit_myaccount(request):
    """Edit profile"""
    form = MyAccountForm(request.POST or None, instance=request.user)
    message = ''
    if request.method == 'POST' and form.is_valid():
        message = "Success"
        form.save()

    return render(request, 'helpline/profile.html',
                  {'form': form,
                   'message': message})


def get_status_count():
    """ Get available, idle and busy agents stats"""
    available = HelplineUser.objects.filter(hl_status__exact='Available').count()
    idle = HelplineUser.objects.filter(hl_status__exact='Idle').count()
    busy_on_call = HelplineUser.objects.filter(hl_status__exact='OnCall').count()
    total = available + idle + busy_on_call
    status_count = {'available': available,
                    'idle': idle,
                    'total': total,
                    'busy_on_call': busy_on_call}
    return status_count

def get_midnight_in_timezone(timezone='Africa/Nairobi'):
    # Get the current datetime in the specified timezone
    tz = pytz.timezone(timezone)
    current_datetime = datetime.now(tz)

    # Set the time to midnight
    midnight = current_datetime.replace(hour=0, minute=0, second=0, microsecond=0)

    return midnight



def get_dashboard_stats(user, interval=None):
    """Stats which are displayed on the dashboard, returns a dict
    Get stats from last midnight
    """
    # Get the epoch time of the last midnight
    if interval == 'weekly':
        midnight_datetime = datetime.combine(
            date.today() - timedelta(days=date.today().weekday()),
            datetime_time.min)
        midnight = calendar.timegm(midnight_datetime.timetuple())
    else:
        midnight_datetime = datetime.combine(
            date.today(), datetime_time.min)
        midnight = calendar.timegm(midnight_datetime.timetuple())

    hot_desks = Hotdesk.objects.using('reportingdb').filter(
        user=user,
        status='Available',
        secret__isnull=False
    )
    user_extensions = [hot_desk.extension for hot_desk in hot_desks]

    # Filter by schedule assigned to current user
    user_services = [schedule.service for schedule in Schedule.objects.using('reportingdb').filter(user=user).distinct('service')]
    if not user_services:
        message = _("User does not have any assigned schedule")

    midnight_string = datetime.combine(
        date.today(), datetime_time.min).strftime('%m/%d/%Y %I:%M %p')
    now_string = datetime.combine(
        date.today(), datetime_time.max).strftime('%m/%d/%Y %I:%M %p')
    # Get the average seconds of hold time from last midnight.

    total_calls = Report.objects.using('reportingdb').filter(
        hl_time__gt=midnight).filter(casetype__exact='Call').filter(
            service__in=user_services
        )

    cdr = Cdr.objects.using('reportingdb').filter(
        calldate__gt=midnight_datetime).filter(src__in=user_extensions)

    answered_calls = Report.objects.using('reportingdb').filter(
        hl_time__gt=midnight).filter(
            calltype__exact='Answered',
            case__isnull=False).filter(
            service__in=user_services
        )
    abandoned_calls = Report.objects.using('reportingdb').filter(
        hl_time__gt=midnight).filter(
            calltype__exact='Abandoned',
        case__isnull=True).filter(
            service__in=user_services
        )

    missed_calls = Clock.objects.using('reportingdb').filter(
        hl_time__gt=midnight).filter(hl_clock="Missed Call").filter(
            service__in=user_services
        )
    voice_mails = Report.objects.using('reportingdb').filter(
        hl_time__gt=midnight).filter(calltype__exact='Voicemail').filter(
            service__in=user_services
        )
    total_walkin = Report.objects.using('reportingdb').filter(
        hl_time__gt=midnight).filter(casetype__exact='Walkin').filter(
            service__in=user_services
        )

    total_cases = Report.objects.using('reportingdb').filter(
        hl_time__gt=midnight).filter(case__isnull=False).filter(
            service__in=user_services
        )
    closed_cases = Report.objects.using('reportingdb').filter(
        hl_time__gt=midnight, casestatus__exact='Close').filter(
            service__in=user_services
        )
    open_cases = Report.objects.using('reportingdb').filter(
        hl_time__gt=midnight, casestatus__exact='Pending').filter(
            service__in=user_services
        )
    referred_cases = Report.objects.using('reportingdb').filter(
        hl_time__gt=midnight, casestatus__exact='Escalate').filter(
            service__in=user_services
        )
    transferred_cases = Report.objects.using('reportingdb').filter(
        hl_time__gt=midnight, casestatus__exact='Transferred').filter(
            service__in=user_services
        )

    total_sms = Messaging.objects.using('reportingdb').filter(hl_time__gt=midnight)

    # Count Answered, Abandoned and Voicemail calls for user
    total_cdr = cdr.count()
    total_answered_cdr = cdr.filter(
        disposition__exact='ANSWERED',
        ).count()
    total_no_answer_cdr = cdr.filter(
        disposition__exact='NO ANSWER',
        ).count()
    total_busy_cdr = cdr.filter(
        disposition__exact='BUSY').count()
    total_failed_cdr = cdr.filter(
        disposition__exact='FAILED').count()
    total_congestion_cdr = cdr.filter(
        disposition__exact='CONGESTION').count()

    # Filter out stats for non supervisor user.
    if user.HelplineUser.hl_role != 'Supervisor' or not user.is_staff:
        total_calls = total_calls.filter(user=user)
        missed_calls = missed_calls.filter(user=user)
        answered_calls = answered_calls.filter(user=user)
        total_cases = total_cases.filter(user=user)
        closed_cases = closed_cases.filter(user=user)
        open_cases = open_cases.filter(user=user)
        referred_cases = referred_cases.filter(user=user)
        transferred_cases = transferred_cases.filter(user=user)
        total_walkin = total_walkin.filter(user=user)

    att = user.HelplineUser.get_average_talk_time()
    awt = user.HelplineUser.get_average_wait_time()

    dashboard_stats = {
        'midnight': midnight,
        'midnight_string': midnight_string,
        'now_string': now_string,
        'att': att,
        'total_cdr': total_cdr,
        'total_answered_cdr': total_answered_cdr,
        'total_no_answer_cdr': total_no_answer_cdr,
        'total_busy_cdr': total_busy_cdr,
        'total_failed_cdr': total_failed_cdr,
        'total_congestion_cdr': total_congestion_cdr,
        'awt': awt,
        'total_calls': total_calls.count(),
        'total_walkin': total_walkin.count(),
        'answered_calls': answered_calls.count(),
        'abandoned_calls': abandoned_calls.count(),
        'missed_calls': missed_calls.count(),
        'voice_mails': voice_mails.count(),
        'total_cases': total_cases.count(),
        'closed_cases': closed_cases.count(),
        'open_cases': open_cases.count(),
        'total_sms': total_sms.count(),
        'referred_cases': referred_cases.count(),
        'transferred_cases': transferred_cases.count(),
    }

    return dashboard_stats


def web_presence(request):
    """Show presence information of agents"""
    available = HelplineUser.objects.filter(hl_status__exact='Available')
    busy_on_call = HelplineUser.objects.filter(hl_status__exact='OnCall')
    idle = HelplineUser.objects.filter(hl_status__exact='Idle')
    offline = HelplineUser.objects.filter(hl_status__exact='Offline')
    status_count = get_status_count()

    # Display all agents in the Connected Agents Table
    # Exclude Unavailable agents.
    agents = HelplineUser.objects.exclude(hl_status='Unavailable')
    connected_agents_table = ConnectedAgentsTable(agents,
                                                  order_by=(
                                                      request.GET.get('sort',
                                                                      'userid')))

    return render(request,
                  'helpline/presence.html',
                  {'connected_agents_table': connected_agents_table})


def report_factory(report='callsummary', datetime_range=None, agent=None,
                   queuename=None, queueid=None, query=None, sort=None,
                   casetype='all', category=None, user=None):
    """Create admin reports"""

    # Initialize the filter query dict
    filter_query = {}

    # Filter by schedule assigned to current user
    # Filter data to what schedule user is assigned
    schedules = get_schedules(user)
    user_services = [schedule.service for schedule in schedules]

    if not user_services:
        message = _("User does not have any assigned schedule")

    # Convert date range string to datetime object
    if datetime_range:
        try:
            a, b = [datetime_range.split(" - ")[0], datetime_range.split(" - ")[1]]
            from_date = datetime.strptime(a, '%m/%d/%Y %I:%M %p')
            to_date = datetime.strptime(b, '%m/%d/%Y %I:%M %p')

            # Add filter to ajax query string.
            filter_query['datetime_range'] = datetime_range
        except Exception as e:
            # Default to current date as date range 
            from_date = datetime.combine(date.today(), datetime.min.time())
            to_date = datetime.combine(date.today(), datetime.max.time())

    else:
        # If date time range is not defined return current date as range
        from_date = datetime.combine(date.today(), datetime.min.time())
        to_date = datetime.combine(date.today(), datetime.max.time())

    # Return agent session table for agent session report.
    if report == 'agentsessionreport':
        clock = Clock.objects.all()
        # Apply filters to queryset.
        if from_date and to_date:
            from_date_epoch = calendar.timegm(from_date.timetuple())
            to_date_epoch = calendar.timegm(to_date.timetuple())
            clock = clock.filter(hl_time__gt=from_date_epoch,hl_time__lt=to_date_epoch)
        if agent:
            clock = clock.filter(user=agent)
            filter_query['agent'] = agent
        # Filter actions. Queue Join etc.
        if query:
            clock = clock.filter(hl_clock__exact=query)
            filter_query['q'] = query

        return AgentSessionTable(clock)

    # Filter to current user services
    # Order by case number
    reports = Report.objects.using('reportingdb').filter(
        service__in=user_services
    ).order_by('-case')

    calltype = {'answeredcalls': 'Answered',
                'abandonedcalls': 'Abandoned',
                'voicemail': 'Voicemail'}

    casestatus = {'pendingcases': 'Pending',
                  'closedcases': 'Close',
                  'escalatedcases': 'Escalate'}

    if calltype.get(report):
        if calltype.get(report) == "Answered":
            reports = reports.filter(calltype__exact=calltype.get(report),
                case__isnull=False)
        elif calltype.get(report) == "Abandoned":
            reports = reports.filter(
                case__isnull=True)
        else:
            reports = reports.filter(calltype__exact=calltype.get(report))
    if casestatus.get(report):
        reports = reports.filter(casestatus__exact=casestatus.get(report))
    # Retrun all case types Inbound and outbount for the following reports.
    if report != 'totalcases' and report != 'search':
        if casetype != 'all':
            reports = reports.filter(casetype__iexact=casetype)
    if report == 'totalcases':
        reports = reports.filter(case__isnull=False)

    # Apply filters to queryset.
    if from_date and to_date and report != 'search':
        from_date_epoch = calendar.timegm(from_date.timetuple())
        to_date_epoch = calendar.timegm(to_date.timetuple())
        reports = reports.filter(hl_time__gt=from_date_epoch,
                                 hl_time__lt=to_date_epoch)

    if agent:
        reports = reports.filter(user__id=agent)
        filter_query['agent'] = agent

    if queueid:
        queue = Service.objects.using('reportingdb').filter(hl_key__exact=queueid)
    if queuename:
        reports = reports.filter(queuename__exact=queuename)

    if category:
        Case = Case.objects.using('reportingdb').filter(hl_acategory=category)
        filter_query['category'] = category
        reports = reports.filter(case_id__in=cases)

    # Search report data
    if query:
        qset = (
            Q(telephone__icontains=query) |
            Q(case__contact__address__hl_names__icontains=query) |
            Q(casestatus__icontains=query)
        )
        # Check if query is an integer for case id matching.
        # Ask for forgiveness if it's not.
        try:
            val = int(query)
            qset |= (Q(case_id__exact=query))
        except ValueError:
            # Ask for forgiveness.
            pass

        reports = reports.filter(qset)
        filter_query['q'] = query

    # Only compute aggregates for call summary report
    if report in ['callsummaryreport', 'chartreport']:
        # Create a link to the data.
        total_offered = {
            'count': reports.filter().count(),
            'filter_query': urllib.parse.urlencode(filter_query),
            'casetype': casetype
        }
        main_cdr = MainCDR.objects.using('reportingdb').all()
        cdr = Cdr.objects.using('reportingdb').all()
        main_cdr = main_cdr.filter(
            hl_time__gt=from_date_epoch,
            hl_time__lt=to_date_epoch
        )
        cdr = cdr.filter(
            calldate__gt=from_date,
            calldate__lt=to_date
        )
        if agent:
            # get agent hotdesk object
            hotdesk = Hotdesk.objects.filter(user=agent).first()
            main_cdr = main_cdr.filter(hl_agent__exact=hotdesk.user.id)
            cdr = cdr.filter(src__exact=hotdesk.extension)

        # Compute the average talk time from seconds returned.
        seconds = main_cdr.aggregate(
            Avg('hl_talktime')).get('hl_talktime__avg')
        cdr_seconds = cdr.aggregate(
            Avg('billsec')).get('billsec__avg')

        att = str(timedelta(seconds=seconds)) if seconds else "00:00:00"
        avg_talktime = str(
            timedelta(seconds=cdr_seconds)) if cdr_seconds else "00:00:00"

        # Compute the average hold time for seconds returned.
        seconds = main_cdr.aggregate(
            Avg('hl_holdtime')).get('hl_holdtime__avg')
        cdr_seconds = cdr.aggregate(Avg('duration')).get('duration __avg')

        aht = str(timedelta(seconds=seconds)) if seconds else "00:00:00"
        avg_call_duration = str(
            timedelta(seconds=cdr_seconds)) if cdr_seconds else "00:00:00"

        # Compute total talk time from seconds returned in h:m:s format
        seconds = main_cdr.aggregate(
            Sum('hl_talktime')).get('hl_talktime__sum')
        total_talktime = str(
            timedelta(seconds=seconds)) if seconds else "00:00:00"

        # Compute total call from seconds returned in h:m:s format
        cdr_seconds = cdr.aggregate(Sum('duration')).get('duration__sum')
        total_duration = str(
            timedelta(seconds=cdr_seconds)) if cdr_seconds else "00:00:00"

        # Count Answered, Abandoned and Voicemail calls for a specific queue.
        total_answered = reports.filter(
            calltype__exact='Answered',
            case__isnull=False).count()
        total_abandoned = reports.filter(
            calltype__exact='Abandoned',
            case__isnull=True).count()
        total_voicemail = reports.filter(
                                         calltype__exact='Voicemail').count()
        # Count Answered, Abandoned and Voicemail calls for user
        total_answered_cdr = cdr.filter(
            disposition__exact='ANSWERED',
            ).count()
        total_no_answer_cdr = cdr.filter(
            disposition__exact='NO ANSWER',
            ).count()
        total_busy_cdr = cdr.filter(
            disposition__exact='BUSY').count()


        # Count calls that breach the SLA.
        # Time in seconds that calls should be on hold.
        # Greater than that SLA is considered breached.
        SLA = 20
        sla_breached = reports.filter(
            holdtime__gt=timedelta(seconds=SLA)).count()

        if total_offered.get('count'):
            sla_percentage = "{0:.2f}%".format(100.0 * (
                float(total_offered.get('count')-sla_breached)/float(
                    total_offered.get('count'))))
            answered_percentage = "{0:.2f}%".format(
                100.0 * (float(total_answered)/float(total_offered.get('count'))))
            abandoned_percentage = "{0:.2f}%".format(
                100.0 * (float(total_abandoned)/float(total_offered.get('count'))))
        else:
            sla_percentage = "NA"
            answered_percentage = "NA"
            abandoned_percentage = "NA"

        # Call summary data.
        datetime_range = datetime_range if datetime_range else ""
        callsummary_data = {'service': '%s %s' % (', '.join([str(service) for service in user_services]), datetime_range),
                            'total_offered': total_offered,
                            'total_answered': total_answered,
                            'total_abandoned': total_abandoned,
                            'total_talktime': total_talktime,
                            'total_answered_cdr': total_answered_cdr,
                            'total_no_answer_cdr': total_no_answer_cdr,
                            'total_busy_cdr': total_busy_cdr,
                            'answered_percentage': answered_percentage,
                            'abandoned_percentage': abandoned_percentage,
                            'day': from_date.strftime("%A") if from_date else None,
                            'month': from_date.strftime(
                                "%B") if from_date else None,
                            'year': from_date.strftime(
                                "%Y") if from_date else None,
                            'att': att,
                            'aht': aht,
                            'category': category,
                            'sla_breached': sla_breached,
                            'sla_percentage': sla_percentage,
                            'total_voicemail': total_voicemail}

        if report == 'chartreport':
            # Return a dict of the call summary data for chartning.
            return callsummary_data
        # Return call summary table if we are not charting
        table = CallSummaryTable([callsummary_data])
        return table

    # Check if table is to be sorted.
    # Default to sorting by case_id if not
    sort = sort if sort else '-hl_time'

    table = DashboardTable(
        reports, order_by=sort
    ) if sort else DashboardTable(reports)

    return table


def ajax_admin_report(request, report, casetype='all'):
    """Returns table of admin reports"""
    form = ReportFilterForm(request.GET)
    datetime_range = request.GET.get("datetime_range")
    agent = request.GET.get("agent")
    query = request.GET.get('q', '')
    sort = request.GET.get('sort', '')
    category = request.GET.get('category', '')

    table = report_factory(report=report,
                           datetime_range=datetime_range,
                           agent=agent,
                           query=query, sort=sort,
                           category=category,
                           casetype=casetype,
                           user=request.user)

    RequestConfig(request).configure(table)
    export_format = request.GET.get('_export', None)
    if TableExport.is_valid_format(export_format):
        exporter = TableExport(export_format, table)
        return exporter.response('table.{}'.format(export_format))

    table.paginate(page=request.GET.get('page', 1), per_page=25)

    return render(request, 'helpline/report_factory.html', {
        'table': table,
        'datetime_range': datetime_range,
        'form': form})


def login(request, template_name="helpline/login.html"):
    """Helpline login handler"""
    request.user.HelplineUser.hl_status = "Idle"
    request.user.HelplineUser.save()
    return render(request, **{"template_name": template_name})


def helpline_logout(request, template_name="helpline/loggedout.html"):
    """Logout Helpline user and remove them from active queues"""
    try:
        message = ""
        logout(request)

    except Exception as e:
        message = e
        return render(request, template_name, {'message': message})

    return render(request, template_name, {'message': message})


def helpline_login(request, template_name="helpline/login.html"):
    """Logout Helpline user and remove them from active queues"""
    request.session['hl_org'] = None
    try:
        message = ""
        if request.method == 'POST':
            email = request.POST.get("email")
            user = User.objects.get(email=email)
            redirect_to = request.POST.get(
                REDIRECT_FIELD_NAME,
                request.GET.get(
                    REDIRECT_FIELD_NAME
                )
            )
            social_connect_url = None
            org = None

            if not redirect_to or not url_has_allowed_host_and_scheme(url=redirect_to, allowed_hosts=[request.get_host()]):
                redirect_to = resolve_url(settings.LOGIN_REDIRECT_URL)

            if user.email:
                if user.email.split("@")[1] == "mogo.co.ke":
                    message = "GO TO AD"
                    try:
                        social_account = SocialAccount.objects.get(user=user)
                        message = "Go to graph"
                        request.session['hl_org'] = 'mogo'
                        return redirect("/accounts/microsoft/login/")
                    except:
                        message = "Connect to Graph"
                        social_account = None
                    if not social_account:
                        request.session['hl_org'] = None
                        social_connect_url = "/accounts/microsoft/login/?process=connect"
                elif user.email.split("@")[1] == "4g-capital.com":
                    try:
                        social_account = SocialAccount.objects.get(user=user)
                        message = "Go to graph"
                        request.session['hl_org'] = '4g'
                        return redirect("/accounts/google/login/")
                    except:
                        message = "Connect to Google"
                        social_account = None
                        request.session['hl_org'] = None
                    if not social_account:
                        request.session['hl_org'] = None
                        social_connect_url = "/accounts/google/login/?process=connect"
                elif user.email.split("@")[1] == "zerxis.com":
                    try:
                        social_account = SocialAccount.objects.get(user=user)
                        message = "Go to graph"
                        request.session['hl_org'] = 'mogo'
                        return redirect("/accounts/google/login/")
                    except:
                        message = "Connect to Google"
                        social_account = None
                    if not social_account:
                        request.session['hl_org'] = None
                        social_connect_url = "/accounts/google/login/?process=connect"
                if social_connect_url:
                    return redirect_to_login(social_connect_url, login_url=redirect_to)
                else:
                    request.session['hl_org'] = 'Other'
                    return redirect_to_login(redirect_to)

    except User.DoesNotExist:
        message = "Please check your email address. Account not found"
        return render(request, template_name, {'message': message})

    return render(request, template_name, {'message': message})


def helpline_home(request):
    """Helpline home"""
    return redirect("/helpline/")


@json_view
def asterisk_alert(request, auth, dialstatus, case_id):
    """Accept user alerts from Asterisk"""
    agent = HelplineUser.objects.get(hl_auth=auth)
    user = agent.user
    case = Case.objects.get(hl_case=case_id)

    alert = {'CHANUNAVAIL': 'unavailable',
             'NOANSWER': 'missed',
             'BUSY': 'busy'}

    verb = "%s" % (alert[dialstatus])
    description = "Dial status is %s for case %s" % (
        alert[dialstatus], case_id)
    channel = agent.hl_exten.split('/')[1]
    notify.send(user, recipient=user, verb=verb,
                description=description, level="warning")
    message = 'Notification sent'
    return {'message': message,
            'auth': auth,
            'agent channel': channel}


@json_view
def ajax_get_subcategory(request, category):
    """Accept ajax request for subcategories"""
    hotdesk = get_hotdesk(request.user)
    results = Category.objects.filter(
        hl_category__iexact=category,
        backend_manager_config=hotdesk.backend_manager_config
    ).values('hl_category', 'hl_subcategory')
    data = {
        'data': list(results),
        'backend_id': hotdesk.backend_manager_config.pk
    }
    return data


@json_view
def ajax_get_sub_subcategory(request, category):
    """Accept ajax request for sub-subcategories"""
    results = Category.objects.filter(
        hl_subcategory=category).values('hl_subsubcat', 'hl_subsubcat')
    data = {'data': list(results)}
    return data


@login_required
def wall(request):
    """Display statistics for the wall board"""
    dashboard_stats = get_dashboard_stats(request.user)
    week_dashboard_stats = get_dashboard_stats(request.user, interval='weekly')
    return render(request, 'helpline/wall.html',
                  {'dashboard_stats': dashboard_stats,
                   'week_dashboard_stats': week_dashboard_stats})


@login_required
def sources(request, source=None):
    """Display data source"""
    template = 'helpline/%s.html' % (source)
    return render(request, template)


def get_hotdesk(user):
    """Get active hotdesk for a user
    Set first hotdesk as primary if none is set"""
    # User hotdesk CACHE timeout
    HOTDESK_CACHE_TIMEOUT = 10

    if cache.get(f'user_hotdesk_{user}'):
        return cache.get(f'user_hotdesk_{user}')

    # Get user primary hotdesk
    primary_hotdesk = Hotdesk.objects.filter(
        user=user,
        status='Available',
        secret__isnull=False,
        backend_manager_config__isnull=False,
        primary=True,
    ).first()

    if primary_hotdesk:
        cache.set(f'user_hotdesk_{user}', primary_hotdesk, HOTDESK_CACHE_TIMEOUT)
        return primary_hotdesk
    # If not primary hotdesk defined, return the first hotdesk
    # This hotdesk has to have SECRET and BACKEND set
    hotdesk = Hotdesk.objects.filter(
        user=user,
        status='Available',
        secret__isnull=False,
        backend_manager_config__isnull=False
    ).first()

    if hotdesk:
        # Make the first hotdesk primary for all users
        hotdesk.primary = True
        hotdesk.save()
        cache.set(f'user_hotdesk_{user}', hotdesk, HOTDESK_CACHE_TIMEOUT)

    return hotdesk


def get_backend(user=None):
    """Get backend server to talk to"""
    if user:
        hotdesk = get_hotdesk(user)
        if hotdesk:
            backend =  Backend(hotdesk.backend_manager_config) if hotdesk.backend_manager_config else Backend()
        else:
            backend = Backend()
    else:
        backend = Backend()
    return backend


def get_member_status(queue_data):
    """Get status of all members in queue"""
    members_status = {}
    for queue_id, queue_info in queue_data["data"].items():
        for member_id, member_info in queue_info["members"].items():
            state_interface = member_info["StateInterface"]
            name = member_info["Name"]
            member_status = member_info["Status"]
            last_call_ago = member_info["LastCallAgo"]
            members_status[state_interface] = {
                "Name": name,
                "Status": member_status,
                "LastCallAgo": last_call_ago
            }
    return members_status


def get_queue_state_interfaces(queue_data, queue_name):
    """Get Extension numbers from a queue"""
    if queue_data:
        try:
            queue = queue_data[queue_name]
        except:
            return []
        state_interfaces = []
        for member_id, member_info in queue["members"].items():
            state_interface = member_info["StateInterface"]
            state_interface = state_interface.replace("SIP/", "")
            state_interfaces.append(state_interface)
        return state_interfaces
    else:
        return []


def get_data_queues(queue=None, user=None):
    """Get Queue data from backend PBX"""
    SERVICE_CACHE_TIMEOUT = 28880
    hotdesk = get_hotdesk(user)
    try:
        backend_id = hotdesk.backend_manager_config.pk
    except:
        backend_id = None

    if cache.get(f'backend_queues_data_{backend_id}'):
        data = cache.get(f'backend_queues_data_{backend_id}')
    else:
        # Return empty dict
        data = None
        # Cache data using celery task
        get_queues_data.delay(backend_id)

    try:
        service = cache.get_or_set(
            f'{queue}_service_backend_{user}',
            Service.objects.get(
                slug=queue,
                backend_manager_config=backend_id
            ),
            SERVICE_CACHE_TIMEOUT
        )
    except Service.DoesNotExist:
        service = None

    if queue is not None and data is not None:
        try:
            if service:
                queue = service.queue
                data['slug'] = service.slug
            else:
                data['slug'] = queue

            data = data[queue]
        except:
            raise Http404(f"Queue not found {queue}")
    return data


@login_required
@json_view
def queues(request):
    """GET Queue data"""
    # Time mesurement
    start_time = time.time()
    hotdesk = get_hotdesk(request.user)
    try:
        backend_id = hotdesk.backend_manager_config.pk
    except:
        backend_id = None

    # Filter data to relevant schedules
    if backend_id:
        get_queues_data.delay(backend_id)
        queues_data = cache.get(
            f'backend_queues_data_{backend_id}'
        )
    else:
        queues_data = {}

    # Return relevant queues data based on Schedules assigned
    return {
        'data': queues_data,
        'id': backend_id,
        'execution_time': time.time() - start_time,
        'version': 3
    }


@login_required
def queue(request, name=None):
    # Time mesurement
    start_time = time.time()
    hotdesk = get_hotdesk(request.user)
    queues_data_error = None
    QUEUE_CACHE_TIMEOUT = 60

    try:
        backend_id = hotdesk.backend_manager_config.pk
    except:
        backend_id = None

    # Filter data to relevant schedules
    if backend_id:
        get_queues_data.delay(backend_id)
        queues_data = cache.get(f'backend_queues_data_{backend_id}')
    else:
        queues_data = {}

    service_queryset = Service.objects.filter(
        Q(slug__exact=name) | Q(extension__exact=name),
        backend_manager_config=backend_id,
    )
    if service_queryset:
        service = service_queryset.first()
    else:
        try:
            get_queues_data(backend_id)
            queues_data = cache.get(f'backend_queues_data_{backend_id}')
            queues_data = queues_data[name]
            queue_name = queues_data.get("name",name)

        except Exception as e:
            queue_name = name
            queues_data_error = {
                "success": False,
                "message": e,
            }
        service = Service(
            extension=name,
            name=queue_name,
            queue=name,
            sip_server=hotdesk.sip_server,
            backend_manager_config=hotdesk.backend_manager_config,
            status=True,
        )
        service.save()

    if service:
        form = ServiceForm(request.POST or None, instance=service)
        if request.method == 'POST' and form.is_valid():
            form.save()

    queue_name = service.queue if service else None

    # Get the all available hot desks who's secret is not null
    hot_desks = get_queue_state_interfaces(
        queues_data,
        queue_name
    )

    if queue_name is not None:
        # Filter out exact queue data using name as key
        try:
            queues_data = queues_data[name]
        except Exception as e:
            queues_data = {}

    # Get call history from cache or set based on hot desk objects
    call_history_table = cache.get(
        f'queue_call_history_table_{queue_name}'
    )
    e = None

    if not call_history_table:
        try:
            cache.set(
                f'queue_call_history_table_{queue_name}',
                get_call_history_table(hot_desk),
                QUEUE_CACHE_TIMEOUT
            )
            call_history_table = cache.get(
                f'queue_call_history_table_{queue_name}'
            )
        except Exception as e:
            call_history_table = None

    return render(request, 'helpline/queue.html',
                  {
                      'data': queues_data,
                      'name': queue_name,
                      'hot_desks': hot_desks,
                      'call_history_table': call_history_table,
                      'show_service_level': True,
                      'queues_data_error': queues_data_error,
                      'service': service,
                      'form': form,
                      'execution_time': time.time() - start_time
                  })


@login_required
def queue_wallboard(request, name=None):
    # Time mesurement
    start_time = time.time()
    QUEUE_DATA_CACHE_TIMEOUT = 15
    hotdesk = get_hotdesk(request.user)
    dashboard_stats = get_dashboard_stats(request.user)
    week_dashboard_stats = get_dashboard_stats(request.user, interval='weekly')

    try:
        backend_id = hotdesk.backend_manager_config.pk
    except:
        backend_id = None

    # Use backend server configs or use default Backend
    if cache.get(f'backend_queues_data_{backend_id}_{name}'):
        queue_data = cache.get(f'backend_queues_data_{backend_id}_{name}')
    else:
        try:
            backend_manager_config = BackendServerManagerConfig.objects.get(
                id=backend_id
            )
        except BackendServerManagerConfig.DoesNotExist:
            backend_manager_config = None
            return {
                'execution_time': time.time() - start_time,
                'backend_id': backend_id,
                'message': "Backend not found",
            }

        backend = Backend(
            backend_manager_config
        ) if backend_manager_config else Backend()
        try:
            queue_data = backend.get_data_queues()
            cache.set(
                f'backend_queues_data_{backend_id}_{name}',
                queue_data,
                QUEUE_DATA_CACHE_TIMEOUT
            )
        except Exception as e:
            return "ERROR %s %s %s" % (backend_id, traceback.format_exc(), e)


    try:
        service = Service.objects.get(
                slug=name,
                backend_manager_config=backend_id
            )
        slug = service.slug
        name = service.queue
        registered = True
        form = ServiceForm(request.POST or None, instance=service)
        if request.method == 'POST' and form.is_valid():
            form.save()
    except Service.DoesNotExist:
        form = None
        slug = name
        registered = False

    if name is not None:
        # Filter out exact queue data using name as key
        try:
            error_message = ""
            queues_data = queue_data[name]
            queue_members = queue_data[name].get("members", {})
            if queue_members:
                user_extensions = [f"'{user_extension}'" for user_extension in queue_members.keys()]
                selected_extensions = ",".join(user_extensions)
            else:
                selected_extensions = f"'{hotdesk.extension_type}/{hotdesk.extension}'"
        except Exception as e:
            queues_data = {}
            queue_members = {}
            selected_extensions = f"'{hotdesk.extension_type}/{hotdesk.extension}'"
            error_message = e

    start = datetime.combine(
        date.today(), datetime_time.min).strftime('%Y-%m-%d %H:%M:%S')
    end = datetime.combine(
        date.today(), datetime_time.max).strftime('%Y-%m-%d %H:%M:%S')

    outbound_calls = pbx_get_outbound_calls_from_database(
        backend_id, start, end, selected_extensions
    )

    # Pandas

    df = pd.DataFrame(outbound_calls[1:])
    try:
        pivot_table = pd.pivot_table(
            data=df,
            index=['chan1'],
            aggfunc={'billsec': np.sum}
        )
        pivot_table_html = pivot_table.to_html()
        outbound_call_count = len(outbound_calls)
    except:
        pivot_table = None
        pivot_table_html = None
        outbound_call_count = 0

    return render(request, 'helpline/queue_wallboard.html',
                  {
                      'data': queues_data,
                      'df': df,
                      'pivot_table_html': pivot_table_html,
                      'name': name,
                      'selected_extensions': selected_extensions,
                      'error_message': error_message,
                      'queue_members': queue_members,
                      'outbound_calls': outbound_calls,
                      'outbound_call_count': outbound_call_count,
                      'dashboard_stats': dashboard_stats,
                      'week_dashboard_stats': week_dashboard_stats,
                      'slug': slug,
                      'form': form,
                      'start': start,
                      'end': end,
                      'registered': registered,
                      'execution_time': time.time() - start_time
                  })



def minutes_ago(epoch_seconds):
    now_seconds = time.time()
    seconds_ago = now_seconds - epoch_seconds
    minutes_ago = round(seconds_ago / 60)
    return minutes_ago


@login_required
@json_view
def queue_wallboard_data(request, name=None):
    # Time mesurement
    start_time = time.time()
    QUEUE_DATA_CACHE_TIMEOUT = 10
    hotdesk = get_hotdesk(request.user)
    try:
        backend_id = hotdesk.backend_manager_config.pk
    except:
        backend_id = None

    if cache.get(f'backend_queue_wallboard_data_{backend_id}_{name}'):
        data = cache.get(f'backend_queue_wallboard_data_{backend_id}_{name}')
        data['cache'] = True
        data['cache_execution_time'] =  time.time() - start_time
        return data
    dashboard_stats = get_dashboard_stats(request.user)
    week_dashboard_stats = get_dashboard_stats(request.user, interval='weekly')
    data = {}


    # Use backend server configs or use default Backend
    if cache.get(f'backend_queues_data_{backend_id}_{name}'):
        queue_data = cache.get(f'backend_queues_data_{backend_id}_{name}')
    else:
        try:
            backend_manager_config = BackendServerManagerConfig.objects.get(
                id=backend_id
            )
        except BackendServerManagerConfig.DoesNotExist:
            backend_manager_config = None
            return {
                'execution_time': time.time() - start_time,
                'backend_id': backend_id,
                'message': "Backend not found",
            }

        backend = Backend(
            backend_manager_config
        ) if backend_manager_config else Backend()
        try:
            queue_data = backend.get_data_queues()
            cache.set(
                f'backend_queues_data_{backend_id}_{name}',
                queue_data,
                QUEUE_DATA_CACHE_TIMEOUT
            )
        except Exception as e:
            return "ERROR %s %s %s" % (backend_id, traceback.format_exc(), e)


    try:
        service = Service.objects.get(
                slug=name,
                backend_manager_config=backend_id
            )
        slug = service.slug
        name = service.queue
        registered = True
        form = ServiceForm(request.POST or None, instance=service)
        if request.method == 'POST' and form.is_valid():
            form.save()
    except Service.DoesNotExist:
        form = None
        slug = name
        registered = False

    if name is not None:
        # Filter out exact queue data using name as key
        try:
            error_message = ""
            queues_data = queue_data[name]
            queue_members = queue_data[name].get("members", {})
            if queue_members:
                user_extensions = [f"'{user_extension}'" for user_extension in queue_members.keys()]
                selected_extensions = ",".join(user_extensions)
            else:
                selected_extensions = f"'{hotdesk.extension_type}/{hotdesk.extension}'"
        except Exception as e:
            queues_data = {}
            queue_members = {}
            selected_extensions = f"'{hotdesk.extension_type}/{hotdesk.extension}'"
            error_message = e

    default_start = datetime.combine(
        date.today(), datetime_time.min).strftime('%Y-%m-%d %H:%M:%S')
    default_end = datetime.combine(
        date.today(), datetime_time.max).strftime('%Y-%m-%d %H:%M:%S')

    start = default_start
    end = default_end
    error_message = None

    outbound_calls = pbx_get_outbound_calls_from_database(
        backend_id, start, end, selected_extensions
    )
    chan_stats_count = {}
    total_talk_time = 0

    # Pandas

    try:
        df = pd.DataFrame(outbound_calls[1:])
        pivot_table = pd.pivot_table(
            data=df, index=['chan1'], aggfunc={'billsec': np.sum}
        )
        lastcall_pivot_table = pd.pivot_table(
            data=df, index=['chan1'], aggfunc={'calldate': np.max}
        )
        for stat in outbound_calls[1:]:
            chan_stats_count[stat.get("chan1")] = chan_stats_count.get(
                stat.get("chan1"), 0) + 1

        billsec_data = 0  # Inital bill sec data
        pivot_table_json = pivot_table.to_json()
        df_json = df.to_json()

        for member in queues_data.get("members"):
            billsec_data = pivot_table.get("billsec").get(member, 0)
            total_talk_time = total_talk_time + billsec_data
            last_call_data = lastcall_pivot_table.get(
                "calldate").get(member, 0)

            queues_data["members"][member]["billsec"] = int(billsec_data)
            last_call_timestamp = pd.Timestamp(last_call_data).strftime(
                '%Y-%m-%d %H:%M:%S')
            queues_data["members"][
                member]["last_outbound_call"] = last_call_timestamp
            queues_data["members"][
                member]["outbound_calls_count"] = chan_stats_count.get(member, 0)

    except Exception as e:
        billsec_data = 0
        pivot_table_json = None
        df_json = None
        error_message = str(e)

    data = {
        'data': queues_data,
        'name': name,
        'total_talk_time': int(total_talk_time),
        'billsec_data': int(billsec_data),
        #'df_json': df_json,
        'pivot_table_json': pivot_table_json,
        'selected_extensions': selected_extensions,
        'error_message': error_message,
        'queue_members': queue_members,
        #'outbound_calls': outbound_calls,
        'chan_stats_count': chan_stats_count,
        'dashboard_stats': dashboard_stats,
        'week_dashboard_stats': week_dashboard_stats,
        'slug': slug,
        'registered': registered,
        'execution_time': time.time() - start_time
    }
    cache.set(
        f'backend_queue_wallboard_data_{backend_id}_{name}',
        data,
        QUEUE_DATA_CACHE_TIMEOUT
    )
    return data

@login_required
def schedule_list(request, name=None):
    schedules = Schedule.objects.filter(user=request.user).distinct('service')
    if not schedules:
        message = _("Agent does not have any assigned schedule")

    schedule_table = ScheduleTable(schedules)
    queue_form = QueueLogForm()
    data = {}
    return render(request, 'helpline/schedule_list.html',
                  {'data': data,
                   'queue_form': queue_form,
                   'schedule_table': schedule_table})

@login_required
def schedule_assignment(request):
    sort = request.GET.get('sort')
    sort = sort if sort else 'id'
    users = User.objects.all()
    cols = [(k.name, tables.Column(orderable=False)) for k in Service.objects.all()]
    schedule_assignment_table = ScheduleAssignmentTable(
        users,
        order_by=sort,
        extra_columns=cols
    )
    return render(request, 'helpline/schedule_assignment_list.html',
                  {'schedule_assignment_table': schedule_assignment_table})


@login_required
@json_view
def queue_json(request, name=None):
    QUEUE_JSON_CACHE_TIMEOUT = 10
    if cache.get(f"queue_json_{name}"):
        data = cache.get(f"queue_json_{name}")
    else:
        data = get_data_queues(name, user=request.user)
        queue_name = data.get("name") if data else "CACHE MISS"
        logger.warning(
            timezone.now().strftime('%H:%M:%S.%f') +
            f' {queue_name} ' +
            f' USER {request.user}' +
            f' NAME {name}'
        )
        cache.set(
            f"queue_json_{name}",
            data,
            QUEUE_JSON_CACHE_TIMEOUT
        )

    return {'data': data}


@login_required
@json_view
def spy(request):
    channel = request.POST.get('channel', '')
    to_exten = request.POST.get('to_exten', '')
    backend = get_backend(request.user)
    r = backend.spy(channel, to_exten)
    return r


@login_required
@json_view
def whisper(request):
    channel = request.POST.get('channel', '')
    to_exten = request.POST.get('to_exten', '')
    backend = get_backend(request.user)
    r = backend.whisper(channel, to_exten)
    return r


@login_required
@json_view
def barge(request):
    channel = request.POST.get('channel', '')
    to_exten = request.POST.get('to_exten', '')
    backend = get_backend(request.user)
    r = backend.barge(channel, to_exten)
    return r


@login_required
@json_view
def call(request):
    channel = request.user.HelplineUser.hl_exten
    if channel:
        to_exten = request.POST.get('to_exten', '')
        backend = get_backend(request.user)
        r = backend.barge(channel, to_exten)
        form_html = "Calling %s" % (to_exten)
        return {'success': True, 'backend': r}
    else:
        return {'success': False}


@login_required
@json_view
def hangup_call(request):
    channel = request.POST.get('channel', '')
    backend = get_backend(request.user)
    r = backend.hangup(channel)
    return r


@login_required
@json_view
def remove_from_queue(request):
    queue = request.POST.get('queue', '')
    agent = request.POST.get('agent', '')
    backend = get_backend(request.user)
    hotdesk = get_hotdesk(request.user)
    queue = realname_queue_rename(queue)
    r = backend.remove_from_queue(agent, queue)
    r['queue'] = queue
    cache.delete(f'backend_queues_data_{hotdesk.backend_manager_config.id}')
    return r


def has_hotdesk(user):
    """Check if user has a Hotdesk object"""
    if not isinstance(user, get_user_model()):
        return False
    return Hotdesk.objects.filter(user=user, primary=True).exists()


@login_required
@json_view
def get_sip_details(request):
    """Get current users SIP Details from Hotdesk"""
    hotdesk_data = []
    data = {}
    full_name = request.user.get_full_name()
    # Get the first available hot desk who's secret is not null
    hot_desks = Hotdesk.objects.filter(
        user=request.user,
        status='Available',
        secret__isnull=False
    )
    # Use the default account if user has no Hot Desk
    if not hot_desks:
        d = settings.DEFAULT_SIP_ACCOUNT
        d['demo'] = True
        hotdesk_data.append(d)
        return hotdesk_data

    for hot_desk in hot_desks:
        d = {}
        sip_server_config = hot_desk.sip_server
        turn_server_config = hot_desk.turn_server

        # Check if the sip server has a webrtc gateway configured
        # Use default if not
        if sip_server_config.webrtc_gateway_url:
            webrtc_gateway_url = sip_server_config.webrtc_gateway_url
        else:
            # TODO: Move this to settings.py
            # Hard coded default webrtc gateway
            webrtc_gateway_url = "https://webrtc-gateway.callcenter.africa/janus"

        # Check if the sip server has a TURN server configured
        # Use default if not
        if turn_server_config:
            turn_server_uri = turn_server_config.turn_uri
            turn_server_username = turn_server_config.turn_username
            turn_server_password = turn_server_config.turn_password
        else:
            turn_server_uri = "stun:stun.l.google.com:19302"
            turn_server_username = None
            turn_server_password = None

        d['sip_proxy'] = "sip:%s:%s" % (
            sip_server_config.sip_host, sip_server_config.sip_port
        )
        d['sip_username'] = "sip:%s@%s" % (
            hot_desk.extension, sip_server_config.sip_host
        )
        d['sip_authuser'] = hot_desk.extension
        d['sip_domain'] = sip_server_config.sip_domain
        d['sip_secret'] = hot_desk.secret
        d['primary'] = hot_desk.primary
        d['sip_displayname'] = full_name if full_name else request.user.get_username()
        d['webrtc_gateway_url'] = webrtc_gateway_url

        #TURN Server settings
        d['turn_server_uri'] = turn_server_uri
        d['turn_server_username'] = turn_server_username
        d['turn_server_password'] = turn_server_password

        hotdesk_data.append(d)

    qs = RecordPlay.objects.filter(
        user=request.user).values_list('id', 'name', 'created_on')
    qs.query = pickle.loads(pickle.dumps(qs.query))

    data['record_play_list'] = list(qs)
    data['hotdesk_data'] = hotdesk_data

    return data


def get_call_history_table(hot_desks, query=None, limit=100):
    """Get call history from cdr table"""
    if hot_desks:
        cdr = Cdr.objects.using('reportingdb').filter(
            src__in=hot_desks).filter(duration__gt=0)
        if query:
            cdr = cdr.filter(dst=query)

        call_history_table = CallHistoryTable(cdr[:limit])
    else:
        call_history_table = None

    return call_history_table


@csrf_exempt
@json_view
def server_settings(request):
    """
    Organization based server settings.
    """
    current_site = get_current_site(request)
    data = {
        "result": "success",
        "msg": "",
        "authentication_methods": {"password": True, "dev": False},
        "myhelpline_version": "1.0.1",
        "myhelpline_feature_level": 30,
        "push_notifications_enabled": True,
        "is_incompatible": "false",
        "email_auth_enabled": "true",
        "require_email_format_usernames": False,
        "realm_uri": "https://%s" % (current_site),
        "realm_name": "Call Center Africa",
        "realm_icon": "/static/helpline/images/logo.png",
        "realm_description": "<p>Welcome to %s!</p>" % (current_site),
        "external_authentication_methods": [
        ]
    }
    return data


@csrf_exempt
@json_view
def get_events(request):
    """
    Queue events
    """
    current_site = get_current_site(request)
    data = {
	"result": "success",
	"msg": "",
	"events": [],
	"queue_id": "7dbf6275-ac6b-44ea-9922-5e05fe570c73"
    }

    return data


@csrf_exempt
@json_view
def get_messages(request):
    """
    get messages from backend server
    """

    data = {
        "result": "success",
        "msg": "",
        "messages": [
            {
                "id": 1408992,
                "sender_id": 19257,
                "content": "<p>I updated the issue to add a follow-up of using the \"View source\" UI we already have (shown when stream/topic are not editable) for the \"View message source\" option, with the caveat that I think we should fix <a href=\"https://github.com/zulip/zulip/pull/22566\">#22566</a> before making that UI more prominent.</p>",
                "recipient_id": 1815,
                "timestamp": 1658520883,
                "client": "ZulipElectron",
                "subject": "three-dot message menu",
                "topic_links": [],
                "is_me_message": False,
                "reactions": [],
                "submessages": [],
                "flags": [],
                "sender_full_name": "Alya Abbott",
                "sender_email": "user19257@chat.zulip.org",
                "sender_realm_str": "",
                "display_recipient": "design",
                "type": "stream",
                "stream_id": 101,
                "avatar_url": "/user_avatars/2/cc02503483622c520c28ba1637499b1ecefbf6bc.png?version=2",
                "content_type": "text/html"
            },
            {
                "id": 1409003,
                "sender_id": 2187,
                "content": "<p>Typically a font only comes in a handful of distinct weights, so when you request a particular weight you end up with whatever's the closest match.</p>\n<p>My guess is that 400 and 500 there are winding up with the exact same actual glyphs.</p>",
                "recipient_id": 1815,
                "timestamp": 1658523759,
                "client": "website",
                "subject": "Less bold font for modal titles",
                "topic_links": [],
                "is_me_message": False,
                "reactions": [],
                "submessages": [],
                "flags": [],
                "sender_full_name": "Greg Price",
                "sender_email": "user2187@chat.zulip.org",
                "sender_realm_str": "",
                "display_recipient": "design",
                "type": "stream",
                "stream_id": 101,
                "avatar_url": "/user_avatars/2/e35cdbc4771c5e4b94e705bf6ff7cca7fa1efcae.png?version=2",
                "content_type": "text/html"
            },
            {
                "id": 1409006,
                "sender_id": 2187,
                "content": "<p>Thanks <span class=\"user-mention silent\" data-user-id=\"24441\">Jonatan Lopez</span> for the feedback! Definitely agree this would be useful to have.</p>",
                "recipient_id": 421,
                "timestamp": 1658523951,
                "client": "website",
                "subject": "stream members",
                "topic_links": [],
                "is_me_message": False,
                "reactions": [],
                "submessages": [],
                "flags": [],
                "sender_full_name": "Greg Price",
                "sender_email": "user2187@chat.zulip.org",
                "sender_realm_str": "",
                "display_recipient": "mobile",
                "type": "stream",
                "stream_id": 48,
                "avatar_url": "/user_avatars/2/e35cdbc4771c5e4b94e705bf6ff7cca7fa1efcae.png?version=2",
                "content_type": "text/html"
            },
    ]
    }

    return data




@csrf_exempt
@json_view
def update_active_status_backend(request):
    """Update user presence"""
    status = request.POST.get("status")
    data = {
        "me": request.user.id,
        "email": "example@callcenter.africa",
        "presence": "Online",
        "zephyr_mirror_active": True,
        "server_time": time.time(),
        "status": status,
    }
    return data


@csrf_exempt
@json_view
def do_events_register(request):
    """Get or Update registration of user"""
    data = {
      # InitialDataBase
      "last_event_id": 34,
      "msg": '',
      "queue_id": '11',
      "zulip_feature_level": 30,
      "zulip_version": "1.1.1",

      # InitialDataAlertWords
      "alert_words": [],

      # InitialDataCustomProfileFields
      "custom_profile_fields": [],

      # InitialDataMessage
      "max_message_id": 100,

      # InitialDataMutedTopics
      "muted_topics": [],

      # InitialDataMutedUsers
      "muted_users": [],

      # InitialDataPresence
      "presences": {},

      # InitialDataRealm
      "development_environment": False,
      "event_queue_longpoll_timeout_seconds": 600,
      # jitsi_server_url omitted
      "max_avatar_file_size_mib": 3,
      "max_file_upload_size_mib": 3,
      "max_icon_file_size_mib": 3,
      "max_logo_file_size_mib": 3,
      "max_message_length": 10000,
      "max_stream_description_length": 500,
      "max_stream_name_length": 100,
      "max_topic_length": 50,
      "password_min_length": 8,
      "password_min_guesses": 3,
      "realm_add_custom_emoji_policy": 3,
      "realm_allow_edit_history": True,
      "realm_allow_message_editing": True,
      "realm_authentication_methods": { "GitHub": True, "Email": True, "Google": True },
      "realm_available_video_chat_providers": {},
      "realm_avatar_changes_disabled": False,
      "realm_bot_creation_policy": 3,
      "realm_bot_domain": 'example.com',
      "realm_community_topic_editing_limit_seconds": 600,
      "realm_create_private_stream_policy": 3,
      "realm_create_public_stream_policy": 3,
      "realm_create_web_public_stream_policy": True,
      "realm_default_code_block_language": 'python',
      "realm_default_external_accounts": {
        "github": {
          "name": 'GitHub',
          "text": 'GitHub',
          "hint": 'Enter your GitHub username',
          "url_pattern": 'https://github.com/%(username)s',
        },
      },
      "realm_default_language": 'en',
      "realm_delete_own_message_policy": 3,
      "realm_description": 'description',
      "realm_digest_emails_enabled": True,
      "realm_digest_weekday": 2,
      "realm_disallow_disposable_email_addresses": True,
      "realm_edit_topic_policy": 3,
      "realm_email_address_visibility": False,
      "realm_email_auth_enabled": True,
      "realm_email_changes_disabled": True,
      "realm_emails_restricted_to_domains": False,
      "realm_enable_read_receipts": False,
      "realm_enable_spectator_access": True,
      "realm_giphy_rating": 3,
      "realm_icon_source": 'U',
      "realm_icon_url": 'example.com/some/path',
      "realm_inline_image_preview": True,
      "realm_inline_url_embed_preview": True,
      "realm_invite_required": True,
      "realm_invite_to_realm_policy": 3,
      "realm_invite_to_stream_policy": 3,
      "realm_is_zephyr_mirror_realm": True,
      "realm_logo_source": 'D',
      "realm_logo_url": '',
      "realm_mandatory_topics": True,
      "realm_message_content_allowed_in_email_notifications": True,
      "realm_message_content_delete_limit_seconds": 3,
      "realm_message_content_edit_limit_seconds": 3,
      "realm_message_retention_days": 3,
      "realm_move_messages_between_streams_policy": 3,
      "realm_name": 'Test',
      "realm_name_changes_disabled": True,
      "realm_night_logo_source": 'D',
      "realm_night_logo_url": '',
      "realm_notifications_stream_id": 3,
      "realm_org_type": 0,
      "realm_password_auth_enabled": True,
      "realm_plan_type": 3,
      "realm_presence_disabled": True,
      "realm_private_message_policy": 3,
      "realm_push_notifications_enabled": True,
      "realm_send_welcome_emails": True,
      "realm_signup_notifications_stream_id": 3,
      "realm_upload_quota_mib": 10,
      "realm_user_group_edit_policy": 3,
      "realm_uri": "https://callcenter.africa",
      "realm_video_chat_provider": 1,
      "realm_waiting_period_threshold": 3,
      "realm_want_advertise_in_communities_directory": False,
      "realm_wildcard_mention_policy": 3,
      "server_avatar_changes_disabled": False,
      "server_emoji_data_url":  'https://callcenter.africa/static/generated/emoji/emoji_api.7820ba9750aa.json',
      "server_generation": 3,
      "server_inline_image_preview": True,
      "server_inline_url_embed_preview": True,
      "server_name_changes_disabled": False,
      "server_needs_upgrade": False,
      "server_web_public_streams_enabled": True,
      "settings_send_digest_emails": True,
      "upgrade_text_for_wide_organization_logo": '',
      "zulip_plan_is_not_limited": False,

      # InitialDataRealmEmoji
      "realm_emoji": {},

      # InitialDataRealmFilters
      "realm_filters": [],

      # InitialDataRealmUser
      "realm_users": [],
      "realm_non_active_users": [],
      "avatar_source": 'G',
      "avatar_url_medium": 'url',
      "avatar_url": None, # ideally would agree with selfUser.avatar_url
      "can_create_streams": False, # new servers don't send, but we fill in
      "can_create_public_streams": False,
      "can_create_private_streams": False,
      "can_create_web_public_streams": False,
      "can_subscribe_other_users": False,
      "can_invite_others_to_realm": False,

      # $FlowIgnore[cannot-read]: Faithfully representing what servers send
      "is_admin": True,

      "is_owner": False,
      "is_billing_admin": True,
      "is_moderator": False,
      "is_guest": False,
      "user_id:": 3,
      "email": "example@callcenter.africa", # aka selfUser.email
      "delivery_email": "example@callcenter.africa",
      "full_name": "John Appleseed",
      "cross_realm_bots": [],

      # InitialDataRealmUserGroups
      "realm_user_groups": [],

      # InitialDataRecentPmConversations
      "recent_private_conversations": [],

      # InitialDataStream
      "streams": [],

      # InitialDataSubscription
      "never_subscribed": [],
      "subscriptions": [],
      "unsubscribed": [],

      # InitialDataUpdateMessageFlags
      "unread_msgs": {
        "streams": [],
        "huddles": [],
        "pms": [],
        "mentions": [],
        "count": 0,
      },

      # InitialDataUserSettings
      "user_settings": {
        "twenty_four_hour_time": True,
        "dense_mode": True,
        "starred_message_counts": True,
        "fluid_layout_width": False,
        "high_contrast_mode": False,
        "color_scheme": 3,
        "translate_emoticons": True,
        "display_emoji_reaction_users": True,
        "default_language": 'en',
        "default_view": 'recent_topics',
        "escape_navigates_to_default_view": True,
        "left_side_userlist": False,
        "emojiset": 'google',
        "demote_inactive_streams": 2,
        "user_list_style": 1,
        "timezone": "UTC",
        "enter_sends": False,
        "enable_drafts_synchronization": True,
        "enable_stream_desktop_notifications": False,
        "enable_stream_email_notifications": False,
        "enable_stream_push_notifications": False,
        "enable_stream_audible_notifications": False,
        "notification_sound": 'zulip',
        "enable_desktop_notifications": True,
        "enable_sounds": True,
        "email_notifications_batching_period_seconds": 120,
        "enable_offline_email_notifications": True,
        "enable_offline_push_notifications": True,
        "enable_online_push_notifications": True,
        "enable_digest_emails": True,
        "enable_marketing_emails": True,
        "enable_login_emails": False,
        "message_content_in_email_notifications": True,
        "pm_content_in_desktop_notifications": True,
        "wildcard_mentions_notify": True,
        "desktop_icon_count_display": 1,
        "realm_name_in_notifications": False,
        "presence_enabled": True,
        "available_notification_sounds": ['zulip'],
        "emojiset_choices": [{ "key": 'google', "text": 'Google modern' }],
        "send_private_typing_notifications": True,
        "send_stream_typing_notifications": True,
        "send_read_receipts": True,
      },

      # InitialDataUserStatus
      "user_status": {},
    }

    return data


@login_required
@json_view
def web_phone(request):
    """WebRTC Based Phone view"""
    data = {}
    queue_form = QueueLogForm(request.POST)
    queue_pause_form = QueuePauseForm()
    invite_form = InviteForm()
    schedules = get_schedules(user=request.user)
    schedule_table = ScheduleTable(schedules)
    if schedules:
        schedule_message = _("Join or leave a queue")
    else:
        schedule_message = _("You are not assigned to any service")

    #Get the first available hot desk where secret is not null
    hot_desk = get_hotdesk(request.user)
    data = {
        'schedule_message': schedule_message,
        'schedule_table': schedule_table,
        'hot_desk': hot_desk,
        'queue_form': queue_form,
        'schedules': schedules,
        'invite_form': invite_form,
        'queue_pause_form': queue_pause_form,
    }
    phone_html = cache.get_or_set(
        "%s_phone_html" % (request.user.username), render_to_string(
            'helpline/web_phone.html',
            data, request
        ),
        3
    )

    return {'phone_html': phone_html}


@login_required
def phone(request):
    """WebRTC Based Phone view"""
    data = {}
    queue_form = QueueLogForm(request.POST)
    queue_pause_form = QueuePauseForm()
    schedules = Schedule.objects.filter(user=request.user).distinct('service')
    schedule_table = ScheduleTable(schedules)
    if schedules:
        schedule_message = _("Join or leave a queue")
    else:
        schedule_message = _("You are not assigned to any service")

    #Get the first available hot desk where secret is not null
    hot_desk = Hotdesk.objects.filter(
        user=request.user,
        status='Available',
        secret__isnull=False
    ).first()
    sip_server_config = SipServerConfig.objects.all().first()
    data = {
        'schedule_table': schedule_table,
        'hot_desk': hot_desk,
        'queue_form': queue_form,
        'queue_pause_form': queue_pause_form,
        'sip_server_config': sip_server_config
    }
    return render(
        request,
        'helpline/phone.html',
        {'data': data}
    )


@login_required
def voice_phone_numbers(request):
    """Manage Voice Phone numbers"""
    return render(
        request,
        'helpline/voice_phone_numbers.html',
        {}
    )


@login_required
def chat(request):
    """Manage Voice Phone numbers"""
    contacts = Contact.objects.all().order_by('hl_time')
    chat_contact_table = ChatContactTable(contacts)
    data = {'chat_contact_table': chat_contact_table}
    return render(
        request,
        'helpline/chat.html',
        data
    )


@json_view
@login_required
def ajax_get_breaks(request):
    """Accept ajax request for subcategories"""
    dynamic_breaks = list(Break.objects.values_list(
        'name', 'name'
    ).distinct())
    # Check if there are values in the Break model
    # If not use the default Breaks in settings.py
    if dynamic_breaks:
        breaks = settings.BREAK_REASONS + dynamic_breaks
    else:
        breaks = settings.BREAK_REASONS
    # Format this for bootbox.promt inputOptions
    data = [{'text': b[0], 'value': b[0]}for b in breaks]
    return data



class ServiceTable(tables.Table):
    """Services list table"""

    class Meta:
        model = Service
        attrs = {'class': 'table table-striped'}
        fields = {'name', 'queue', 'extension', 'status'}
        sequence = ('name', 'queue', 'extension', 'status')


@login_required
def services(request):
    """Service managemnt view"""
    data ={}
    services = Service.objects.all()
    data['services_table'] = ServiceTable(services)

    return render(
        request,
        'helpline/services.html',
        data
    )


@login_required
def panel_home(request):
    """Service panel home"""
    queues = get_data_queues(user=request.user)
    data = {'queues': queues}
    return render(
        request,
        'helpline/panel_home.html',
        data
    )


@login_required
def queue_list(request):
    """Queue list home"""
    queues = get_data_queues(user=request.user)
    data = {'queues': queues}
    return render(
        request,
        'helpline/queue_list.html',
        data
    )


@json_view
@login_required
def outbound_create_case(request):
    """Create case for a service using a call"""
    service_id = request.GET.get('service')
    telephone = request.GET.get('telephone')
    if telephone:
        try:
            cdr = Cdr.objects.get(dst=telephone)
        except:
            success = False
            return {'success': success, 'message': "Call not found in CDR"}

        timestamp = int(cdr.calldate.timestamp())
        service = Service.objects.get(id=service_id)
        contact, contact_created = Contact.objects.get_or_create(
            hl_contact=telephone
        )

        case = Case(
            hl_unique=cdr.uniqueid,
            user=request.user,
            hl_popup='No',
        )
        case.save()

        report = Report(
            case=case,
            service=service,
            telephone=telephone,
            hl_unique=cdr.uniqueid,
            calldate=cdr.calldate,
            casetype="Out",
            calltype="Call",
            queuename=service.name,
            user=request.user,
            callstart=cdr.calldate,
            hl_time=timestamp
        )
        report.save()
        request.user.HelplineUser.case = case
        request.user.HelplineUser.save()
        success = True
        message = "%s %s %s" % (cdr, case, report)
    else:
        success = False
        message = "Not found TELEPHONE:" + telephone + "Service : " + service_id
    return {'success': success, 'message': message}


@json_view
@login_required
@csrf_exempt
def set_outbound_caller_id(request):
    """Set the outbound caller ID for user hotdesk"""
    outbound_caller_id = request.POST.get('outbound_caller_id')
    pbxapi_set_outbound_caller_id.delay(
        request.user.id,
        outbound_caller_id.strip()
    )
    return {'success': True}


@json_view
@login_required
def get_outbound_caller_id(request):
    """Get list of outbound caller ids for a given hotdesk"""
    user_id = request.user.id
    outbound_caller_id = cache.get(
        'outbound_caller_id_%s' % (user_id)
    )
    if outbound_caller_id:
        extension = outbound_caller_id.get('extension')
    else:
        extension = None
        #cache_outbound_caller_id.delay(user_id)

    # Remove "text" key and value from dict
    # "text" is basically the json data
    if extension:
        outbound_caller_id.get('extension').pop('text')

    return outbound_caller_id


@json_view
@login_required
def set_unreachable_destination(request):
    """Get list of outbound caller ids for a given hotdesk"""
    # For now we will use the static get_hotdesk function
    chanunavail_dest = request.POST.get('chanunavail_dest')
    return {"success": False, "dest": chanunavail_dest}


@login_required
def c2c(request):
    """ Initate Click to Call Asynchronously"""
    user_id = request.user.id
    phone_number = str(request.GET.get('phone'))
    try:
        res = click_to_call(user_id, "%s" % (phone_number))
    except Exception as e:
        res = e

    return render(
        request, 'helpline/c2c.html',
        {
            'phone_number': phone_number,
            'user_id': user_id,
            "res": res
        }
    )


@login_required
def manage_hotdesks(request):
    pass


@login_required
def manage_server(request):
    pass

@login_required
def applications(request):
    """Developer App management"""
    pass


@xframe_options_exempt
def embeddable(request):
    """Dev WebRTC Based Phone view"""
    data = {}
    if not request.user.is_authenticated:
        auth_query = {}
        auth_query['client_id'] = request.GET.get('client_id')
        auth_query['response_type'] = request.GET.get('response_type')
        auth_query['redirect_uri'] = request.GET.get('redirect_uri')
        data['auth_query'] = urllib.parse.urlencode(auth_query)

        return render(
            request,
            'helpline/login_panel.html',
            data
        )

    queue_form = QueueLogForm(request.POST)
    hotdesk = get_hotdesk(request.user)
    queue_pause_form = QueuePauseForm()
    invite_form = InviteForm()
    schedules = get_schedules(user=hotdesk.user)
    schedule_table = ScheduleTable(schedules)
    if schedules:
        schedule_message = _("Join or leave a queue")
    else:
        schedule_message = _("You are not assigned to any service")

    data = {
        'schedule_message': schedule_message,
        'schedule_table': schedule_table,
        'hot_desk': hotdesk,
        'queue_form': queue_form,
        'schedules': schedules,
        'invite_form': invite_form,
        'queue_pause_form': queue_pause_form,
    }
    return render(
        request,
        'helpline/embeddable_web_phone.html',
        data
    )


def widget(request, client_id=None, widget_id=None):
    """Return Helpline Embeddable Widget
    Client ID -- oAuth Application ID
    Widget ID -- Redirect URI index from oAuth Application"""

    data = {
        'client_id': client_id,
        'widget_id': widget_id,
        'platform': 'dev',
    }

    try:
        redirect_uris = get_application_model().objects.get(client_id=client_id).redirect_uris
    except:
        data["error"] = "Application ID does not exist"
        resp = render(
            request,
            'helpline/widget.js',
            data
        )
        resp['Content-Type'] = "application/javascript";
        return resp

    try:
        redirect_uri_index = int(widget_id)
        data['redirect_uris'] = redirect_uris.split()[
            redirect_uri_index-1
        ]
    except ValueError:
        data['redirect_uris'] = redirect_uris.split()[0]

    resp = render(
        request,
        'helpline/widget.js',
        data
    )
    resp['Content-Type'] = "application/javascript";

    return resp


def get_pbx_auth_base64(clientid, clientscret):
    """Return base64 encoding of clientid:clientsecret"""

    auth_basic = f"{clientid}:{clientsecret}"
    auth_basic_bytes = auth_basic.encode("ascii")

    auth_base64_bytes = base64.b64encode(auth_basic_bytes)
    auth_base64_string = auth_base64_bytes.decode("ascii")
    return auth_base64_string


@json_view
@csrf_exempt
def ajax_campaigns(request):
    """Return list of campaigns"""
    if request.user.is_authenticated:
        api_key = None
        hotdesk = get_hotdesk(request.user)
        data = get_data_campaign(backend_id=hotdesk.backend_manager_config.id)
    else:
        api_key = request.POST.get("key")
        if api_key == 'WYH87QsyoK3bNSJfjX7gigqBe8obEu':
            data = get_data_campaign(backend_id=3)
        else:
            return {"error": True, "message": f"API Key missing"}

    try:
        api_key = data.pop("api_key")
    except Exception as e:
        return {"error": True, "message": f"API Key missing {e}"}

    return {
        'data': data,
        'version': 2
    }


@login_required
def campaigns(request):
    """Return list of campaigns"""
    hotdesk = get_hotdesk(request.user)
    if not hotdesk:
        raise Http404(_("Page not found"))

    campaigns_data = get_data_campaign(backend_id=hotdesk.backend_manager_config.id)
    queues = get_data_queues(user=request.user)
    campaigns_json = campaigns_data.get("campaigns")
    campaigns_host = campaigns_data.get("host")

    data = {
        'campaigns': campaigns_json,
        'campaigns_data': campaigns_data,
        'campaigns_host': campaigns_host,
        'queues': queues,
        'version': 2,
    }
    return render(
        request,
        'helpline/campaigns.html',
        data
    )



@login_required
@json_view
def campaign(request, key=None):
    """ View individual campaign"""
    # Time mesurement
    start_time = time.time()
    CAMPAIGN_JSON_CACHE_TIMEOUT = 10
    calls_chart_data = {}
    if cache.get(f"campaign_json_{key}"):
        campaign_data = cache.get(f"campaign_json_{key}")
    else:
        key = decode_campaign_key(key)
        backend_id = key.get("backend_id")
        campaign_id = key.get("campaign_id")
        hotdesks = Hotdesk.objects.filter(
            user=request.user,
            backend_manager_config=backend_id,
        )
        if not hotdesks:
            raise Http404(_("Campaign not found. Could be deleted."))

        try:
            campaign_data = get_data_campaign(backend_id=backend_id, campaign_id=campaign_id)
        except:
            raise Http404(_("Campaign not found. Could be deleted."))
        campaign = campaign_data.get("campaign") if campaign_data else "CACHE MISS"
        campaign_key = campaign.get("key")
        campaign_id = campaign.get("id")
        campaign_host = campaign_data.get("host")
        api_key = campaign_data.get("api_key")
        if campaign_host:
            url = f"https://{campaign_host}/index.php?menu=campaign_out&action=csv_data&id_campaign={campaign_id}&rawmode=yes&apiKey={api_key}"
            try:
                res = requests.get(url)
                campaign_csv = res.text
            except Exception as e:
                campaign_csv = ""

            campaign_data['campaign_csv'] = campaign_csv
            calls_data = campaign.get("calls")
            if calls_data:
                if calls_data.get("None"):
                    calls_data['Not Placed'] = calls_data.get("None")
                    del(calls_data['None'])
                calls_xdata = [k for k in calls_data.keys()]
                calls_ydata = [calls_data[k] for k in calls_data]
                calls_chartdata = {'x': calls_xdata, 'y': calls_ydata}
                calls_charttype = "pieChart"
                calls_chartcontainer = 'piechart_container'
                calls_chart_data = {
                    'charttype': calls_charttype,
                    'chartdata': calls_chartdata,
                    'chartcontainer': calls_chartcontainer,
                    'extra': {
                        'x_is_date': False,
                        'x_axis_format': '',
                        'tag_script_js': True,
                        'jquery_on_ready': False,
                    }
                }

            else:
                calls_chart_data = None

            try:
                columns = campaign_csv.splitlines()[1].split(",")
            except:
                columns = ['NO DATA']
            try:
                campaign_csv = "\n".join(campaign_csv.split("\n")[2:])
            except:
                campaign_csv = res.text

            csvStringIO = StringIO(campaign_csv)
            column_names = []
            i = 1
            for column in columns:
                column_names.append(f"{column}_{i}")
                i += 1

            df = pd.read_csv(
                csvStringIO,
                names=column_names,
                encoding='latin-1'
            )
            campaign_data['campaign_html'] = df.to_html(
                index=False,
                table_id='campaign_data_table',
                classes="table table-hover display nowrap dataTable dtr-inline collapsed",
            )
            campaign_data['columns'] = columns
            #campaign_data['campaign_html'] = columns

        cache.set(
            f"campaign_json_{campaign_key}",
            campaign_data,
            CAMPAIGN_JSON_CACHE_TIMEOUT
        )

    hotdesk = get_hotdesk(request.user)
    name = campaign_data.get("campaign").get("queue")

    try:
        backend_id = hotdesk.backend_manager_config.pk
    except:
        backend_id = None

    # Filter data to relevant schedules
    if backend_id:
        get_queues_data.delay(backend_id)
        queues_data = cache.get(f'backend_queues_data_{backend_id}')
    else:
        queues_data = {}

    form = None
    registered = False

    if name is not None:
        # Filter out exact queue data using name as key
        try:
            queues_data = queues_data[name]
        except Exception as e:
            queues_data = {}

    return render(request, 'helpline/campaign.html',
                  {
                      'data': queues_data,
                      'name': name,
                      'key': key,
                      'campaign_data': campaign_data,
                      'calls_chart_data': calls_chart_data,
                      'form': form,
                      'registered': registered,
                      'execution_time': time.time() - start_time
                  })


def decode_campaign_key(key):
    """ Decode base64 campaign key backend_id:campaign_id"""
    key_basic_bytes = key.encode('ascii')
    key_bytes = base64.b64decode(key_basic_bytes)
    key = key_bytes.decode('ascii')

    data = {}
    data['backend_id'] = key.split(":")[0]
    data['campaign_id'] = key.split(":")[1]
    data['version'] = 2

    return data


@login_required
@json_view
def ajax_campaign_json(request):
    """Return json data of a campaign"""
    CAMPAIGN_JSON_CACHE_TIMEOUT = 10
    key = request.GET.get("key")
    if not key:
        return {}
    if cache.get(f"campaign_json_{key}"):
        data = cache.get(f"campaign_json_{key}")
    else:
        key = decode_campaign_key(key)
        backend_id = key.get("backend_id")
        campaign_id = key.get("campaign_id")

        data = get_data_campaign(backend_id=backend_id, campaign_id=campaign_id)
        campaign = data.get("campaign") if data else "CACHE MISS"
        campaign_key = campaign.get("key")
        campaign_id = campaign.get("id")
        campaign_host = data.get("host")
        api_key = data.get("api_key")
        if campaign_host:
            url = f"https://{campaign_host}/index.php?menu=campaign_out&action=csv_data&id_campaign={campaign_id}&rawmode=yes&apiKey={api_key}"
            res = requests.get(url)
            campaign_csv = res.text
            data['campaign_csv'] = campaign_csv

        cache.set(
            f"campaign_json_{campaign_key}",
            data,
            CAMPAIGN_JSON_CACHE_TIMEOUT
        )

    api_key = data.pop("api_key", None)

    return {'data': data}


@csrf_exempt
@json_view
def campaign_webhook(request):
    """Process campaign data sent from webhooks"""
    body = request.body
    if body:
        data = json.loads(body)
    else:
        # Test data
        body = b'{"id":"4571","name":"ApiTestPatrickDev2","trunk":"SIP\\/NBO4Trunk","context":"from-internal","queue":"661","max_canales":"0","num_completadas":"0","promedio":"0","desviacion":"3","retries":"3","datetime_init":"2022-07-02","datetime_end":"2022-07-02","daytime_init":"01:00:00","daytime_end":"18:00:00","auth":"MzphZG1pbjpLbjN0Wk4wMDc="}'
        data = json.loads(body)

    process_campaign_webhook_data.delay(data)
    auth = data.pop('auth')
    return {"data": data}


@csrf_exempt
@json_view
def campaign_update_inactive(request):
    """Process campaign data sent from webhooks"""
    body = request.body
    if body:
        data = json.loads(body)
    else:
        body = b'{"auth": "MzphZG1pbjpLbjN0Wk4wMDc="}'
        data = json.loads(body)

    update_task_res = update_inactive_campaigns(data)
    auth = data.pop('auth')
    return {"data": data, 'update_tasks': update_task_res}


@csrf_exempt
@json_view
def campaign_update_finished(request):
    """Process campaign data sent from webhooks"""
    body = request.body
    if body:
        data = json.loads(body)
    else:
        body = '{"auth": "MzphZG1pbjpLbjN0Wk4wMDc="}'
        data = json.loads(body)

    update_task_res = update_finished_campaigns(data)
    auth = data.pop('auth')
    return {"data": data, 'update_tasks': update_task_res}


@json_view
def campaign_calls(request):
    """List calls added to call center auto dial
    for a given campaign"""
    data = {}
    return {"data": data}


@json_view
@login_required
def agent_console(request):
    """Embeded agent console for helpline app"""
    user = request.user
    hotdesk = get_hotdesk(user)
    data = {}
    if hotdesk:
        api_key = pbx_auth_encode(
            hotdesk.backend_manager_config.id,
            user.username,
            f"{user.username}007",
            hotdesk.extension,
        )

        backend_server = hotdesk.backend_manager_config
        if not backend_server:
            return {'meessage': 'No backend server defined'}

        pbxapi_url = backend_server.pbxapi_url
        helpline_agent_console_url = f"{pbxapi_url}helpline.php?menu=helpline_agent_console&apiKey={api_key}#login=True"
        data = {
            "helpline_agent_console_url": helpline_agent_console_url,

        }
    return render(request, 'helpline/agent_console.html',
                  data
                 )


def recording_file_path_decode(key):
    """Decode base64 encoded recoridng path
    backend_id:uniqueid:recordingfilepath"""
    key_basic_bytes = key.encode('ascii')
    key_bytes = base64.b64decode(key_basic_bytes)
    key = key_bytes.decode('ascii')

    data = {}
    data['backend_id'] = key.split(":")[0]
    data['uniqueid'] = key.split(":")[1]

    return data



@json_view
def recording_file(request, key=None):
    """Get a recording file from remote server"""
    data = recording_file_path_decode(key)
    backend_id = data.get("backend_id")
    uniqueid = data.get("uniqueid")

    recording_file = get_recording_file(backend_id, uniqueid)
    try:
        namefile = recording_file.get('recordingfile')[0].get("recordingfile")
    except:
        return({"success": False, "message": "Recording not found"})

    api_key = recording_file.get('api_key')
    params = {'id': uniqueid, 'namefile': namefile, 'apiKey': api_key}
    host = recording_file.get("host")
    pbxapi_url = recording_file.get("pbxapi_url")
    url_params = urllib.parse.urlencode(params)

    file_url = f"{pbxapi_url}helpline.php?{url_params}"
    filename = f"{settings.MEDIA_ROOT}audio_recording/{backend_id}/{uniqueid}/{namefile}"
    audio_file = Path("{filename}")
    if not audio_file.is_file():
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        r = requests.get(file_url, stream = True, verify=False)
        with open(f"{filename}","wb") as audio_file:
            for chunk in r.iter_content(chunk_size=1024):
                # writing one chunk at a time to pdf file
                if chunk:
                    audio_file.write(chunk)
    ## For DEBUG
    ## return {"data": recording_file, "file_url": file_url, "media_url": f"{settings.MEDIA_URL}{backend_id}/{uniqueid}/{namefile}"}

    media_url = f"{settings.MEDIA_URL}audio_recording/{backend_id}/{uniqueid}/{namefile}"
    return redirect(media_url)


@json_view
def recordings(request):
    """Manage audio recordings"""
    return {}


@login_required
def record(request):
    """ record a WebRTC session, and replay it later."""

    return render(
        request, "helpline/record.html", {}
    )


@json_view
@csrf_exempt
@login_required
def record_play_create(request):
    """Create a WebRTC recording session"""
    data = {}
    if request.method == 'POST':
        name = request.POST.get("name")
        user = request.user
        record_play = RecordPlay(
            user=user,
            name=name,
            audio=True,
            audio_codec='opus',
            video=False,
        )
        record_play.save()
        data["id"] = record_play.pk
        data["name"] = f"{record_play.pk}-{user.id}-{user.username}-"+name
        return data
    return data


@json_view
@login_required
def get_recording(request):
    """Searve recording file based on unique id"""
    hotdesk = get_hotdesk(request.user)
    backend_id = hotdesk.backend_manager_config.id
    uniqueid = request.GET.get("uniqueid")

    recording_file = get_recording_file(backend_id, uniqueid)
    try:
        namefile = recording_file.get('recordingfile')[0].get("recordingfile")
    except:
        return {"error": _("Not Found"), "hotdesk": hotdesk.extension}
    api_key = recording_file.get('api_key')
    params = {'id': uniqueid, 'namefile': namefile, 'apiKey': api_key}
    host = recording_file.get("host")
    pbxapi_url = recording_file.get("pbxapi_url")
    url_params = urllib.parse.urlencode(params)

    file_url = f"{pbxapi_url}helpline.php?{url_params}"
    filename = f"{settings.MEDIA_ROOT}audio_recording/{backend_id}/{uniqueid}/{namefile}"
    audio_file = Path("{filename}")
    if not audio_file.is_file():
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        r = requests.get(file_url, stream = True, verify=False)
        with open(f"{filename}","wb") as audio_file:
            for chunk in r.iter_content(chunk_size=1024):
                # writing one chunk at a time to pdf file
                if chunk:
                    audio_file.write(chunk)
    ## For DEBUG
    ## return {"data": recording_file, "file_url": file_url, "media_url": f"{settings.MEDIA_URL}{backend_id}/{uniqueid}/{namefile}"}

    media_url = f"{settings.MEDIA_URL}audio_recording/{backend_id}/{uniqueid}/{namefile}"
    return redirect(media_url)


def report_cybersecurity_issue(request):
    """Report cyber security issues page and hall of fame"""
    data = {}
    return render(
        request,
        'helpline/report_cybersecurity_issue.html',
        data
    )


def pbx_get_extensions_from_database(backend_id):
    extension_list = []
    try:
        backend_manager_config = BackendServerManagerConfig.objects.get(
            id=backend_id
        )
    except BackendServerManagerConfig.DoesNotExist:
        backend_manager_config = None
        return []
    username = backend_manager_config.mysql_user
    password = backend_manager_config.mysql_password
    host = backend_manager_config.host
    if backend_manager_config.mysql_host:
        database_host = backend_manager_config.mysql_host
    else:
        database_host = backend_manager_config.host
    try:
        mydb = mysql.connector.connect(
            host=database_host,
            user=username,
            password=password,
            database="asterisk"
        )
    except Error as e:
        return(f"Error while connecting to MySQL {e}")

    mycursor = mydb.cursor()
    extensions_list_sql = f"""SELECT extension,
    if(dial is null,concat('USER/',extension),dial) AS dial,
    name FROM users
    LEFT JOIN devices ON users.extension=devices.id"""

    mycursor.execute(
       extensions_list_sql
    )
    # this will extract row headers
    row_headers = [x[0] for x in mycursor.description]
    myresult = mycursor.fetchall()
    for result in myresult:
        json_result = dict(zip(row_headers, result))
        extension_list.append(json_result)
    mycursor.close()
    mydb.close()

    return extension_list


@login_required
@json_view
def get_backend_extensions(request):
    """Get list of extensions from Backend server PBX API
    Cache the results and return list of extensions"""
    user = request.user
    user_id = request.user.id
    hotdesk = get_hotdesk(request.user)

    EXTENSION_LIST_CACHE_TIMEOUT = 30
    backend_id = hotdesk.backend_manager_config.id


    if not hotdesk:
        return {'message': 'No hotdesk', 'user_id': user_id}

    backend_extension_list = pbx_get_extensions_from_database(backend_id)

    cache.set(
        f"backend_extension_list_{backend_id}",
        backend_extension_list,
        EXTENSION_LIST_CACHE_TIMEOUT
    )

    extension_list = []
    try:
        for extension in backend_extension_list:
            extension_list.append(
                {
                    "value": extension["dial"],
                    "text": "%s (%s)" % (extension["name"], extension["dial"])
                }
            )
    except:
        extension_list = backend_extension_list

    return {
        "extension_list": extension_list,
        "success": True,
        "message": "Success",
        "version": "2"
    }




def pbx_get_outbound_calls_from_database(backend_id, start, end, extensions):
    """ Get outbound calls from mysql database """
    outbound_calls = []
    outbound_query = f"SELECT substring(channel,1,locate(\"-\",channel,1)-1)\
            AS chan1, billsec, calldate,\
            (time_to_sec(calldate)-(hour(calldate)*3600)+billsec)-3600 AS minute, hour(calldate) AS hour,date_format(calldate,'%Y%m%d') AS fulldate \
            FROM asteriskcdrdb.cdr WHERE  substring(channel,1,locate(\"-\",channel,1)-1)<>'' \
            AND calldate >= '{start}' AND calldate <= '{end}' AND (duration-billsec) >=0 \
            HAVING chan1 IN ({extensions}) ORDER BY calldate"
    outbound_calls.append(outbound_query)
    try:
        backend_manager_config = BackendServerManagerConfig.objects.get(
            id=backend_id
        )
    except BackendServerManagerConfig.DoesNotExist:
        backend_manager_config = None
        return []
    username = backend_manager_config.mysql_user
    password = backend_manager_config.mysql_password
    host = backend_manager_config.host
    if backend_manager_config.mysql_host:
        database_host = backend_manager_config.mysql_host
    else:
        database_host = backend_manager_config.host
    try:
        mydb = mysql.connector.connect(
            host=database_host,
            user=username,
            password=password,
            database="asterisk"
        )
    except Error as e:
        return(f"Error while connecting to MySQL {e}")

    mycursor = mydb.cursor()

    mycursor.execute(
      outbound_query
    )
    # this will extract row headers
    row_headers = [x[0] for x in mycursor.description]
    myresult = mycursor.fetchall()

    for result in myresult:
        json_result = dict(zip(row_headers, result))
        outbound_calls.append(json_result)

    mycursor.close()
    mydb.close()

    return outbound_calls


def pbx_get_home_dashboard(backend_id):
    """ Get todays stats from PBX """
    data_list = []
    dashboard_sql= "SELECT src,dst,lastapp,substring(channel,1,locate(\"-\",channel,1)-1) AS chan1, ";
    dashboard_sql+="substring(dstchannel,1,locate(\"-\",dstchannel,1)-1) AS chan2, ";
    dashboard_sql+="billsec, calldate,j1.dial,j2.dial,if(j1.dial is not null and j2.dial is null,'outbound','') as outbound, ";
    dashboard_sql+="if(j1.dial is null and j2.dial is not null,'inbound','') ";
    dashboard_sql+="AS inbound FROM asteriskcdrdb.cdr LEFT JOIN asterisk.devices as j2 on substring(dstchannel,1,locate(\"-\",dstchannel,1)-1) = j2.dial ";
    dashboard_sql+="LEFT JOIN asterisk.devices as j1 on substring(channel,1,locate(\"-\",channel,1)-1) = j1.dial WHERE calldate>curdate() AND billsec>0 AND disposition='ANSWERED' ";
    dashboard_sql+="HAVING outbound<>'' OR inbound<>'' AND chan2<>'' ORDER BY calldate DESC";

    try:
        backend_manager_config = BackendServerManagerConfig.objects.get(
            id=backend_id
        )
    except BackendServerManagerConfig.DoesNotExist:
        backend_manager_config = None
        return []
    username = backend_manager_config.mysql_user
    password = backend_manager_config.mysql_password
    host = backend_manager_config.host
    if backend_manager_config.mysql_host:
        database_host = backend_manager_config.mysql_host
    else:
        database_host = backend_manager_config.host
    try:
        mydb = mysql.connector.connect(
            host=database_host,
            user=username,
            password=password,
            database="asterisk"
        )
    except Error as e:
        return(f"Error while connecting to MySQL {e}")

    mycursor = mydb.cursor()
    mycursor.execute(
       dashboard_sql
    )
    # this will extract row headers
    row_headers = [x[0] for x in mycursor.description]
    myresult = mycursor.fetchall()
    for result in myresult:
        json_result = dict(zip(row_headers, result))
        data_list.append(json_result)

    mycursor.close()
    mydb.close()
    return data_list



@csrf_exempt
@login_required
def stats(request):
    """Outbound and inbound stats from PBX"""
    data = {}

    inbound   = 0
    outbound  = 0
    totaltime = 0
    totalinboundtime = 0
    totaloutboundtime = 0
    totalcall = 0
    avgtime   = 0
    avgtimeout = 0
    callsfrom = {}
    hotdesk = get_hotdesk(request.user)
    try:
        backend_id = hotdesk.backend_manager_config.pk
    except:
        backend_id = 11

    data['months_choices'] = list(calendar.month_name)[1:]
    data['extension_list'] = pbx_get_extensions_from_database(backend_id)
    today = date.today()
    monday = today + timedelta(days=-today.weekday(), weeks=1)
    data['monday'] = monday
    data['sunday'] = monday + timedelta(days=6)
    data['today'] = today
    data['start_of_month'] = datetime.today().replace(day=1)
    data['end_of_month'] = datetime.today().replace(day=calendar.monthrange(today.year, today.month)[1])
    data['three_months_ago'] = today - timedelta(weeks=8)
    dashboard_home_data = pbx_get_home_dashboard(backend_id)

    for dashboard_data in dashboard_home_data:
        totalcall += 1
        if dashboard_data.get("inbound"):
            inbound += 1
            totalinboundtime+=dashboard_data['billsec'];
        elif dashboard_data.get("outbound"):
            outbound += 1
            totaloutboundtime+=dashboard_data['billsec']
        try:
            callsfrom[dashboard_data.get("src")] += 1
        except:
            callsfrom[dashboard_data.get("src")] = 1

    totalinboundtime = round(totalinboundtime/60,0)
    totaloutboundtime = round(totaloutboundtime/60,0)
    totaltime = totalinboundtime + totaloutboundtime

    if inbound:
        avgtimein  = round(totalinboundtime / inbound,2)
    else:
        avgtimein = 0

    if outbound:
        avgtimeout = round(totaloutboundtime / outbound,2)
    else:
        avgtimein = 0

    data['inbound'] = inbound
    data['outbound'] = outbound
    data['totalinboundtime'] = totalinboundtime
    data['totaloutboundtime'] = totaloutboundtime
    data['totaltime'] = totaltime
    data['totalcall'] = totalcall
    data['callsfrom'] = callsfrom
    data['avgtimeout'] = avgtimeout
    data['avgtimein'] = avgtimein

    if request.POST.get("List_Extensions[]", False):
        request.session['day1'] = int(request.POST.get("day1"))
        request.session['day2'] = int(request.POST.get("day2"))
        request.session['month1'] = request.POST.get("month1")
        request.session['month2'] = request.POST.get("month2")
        request.session['year1'] = request.POST.get("year1")
        request.session['year2'] = request.POST.get("year2")
        request.session['selected_extensions'] = request.POST.getlist("List_Extensions[]")
        data['selected_extensions'] = [x.strip("'") for x in request.POST.getlist("List_Extensions[]", [])]
    else:
        data['selected_extensions'] = [x.strip("'") for x in request.session.get('selected_extensions', [])]

    if request.method == 'POST':
        data['post_data'] = request.POST
        data['day1_data'] = request.POST.get("day1")
        start  = request.POST.get("start")
        end = request.POST.get("end")

    # We identify hotdesk's by the Extension number
    hotdesk = get_hotdesk(request.user)
    extension = hotdesk.extension
    extension_type = hotdesk.extension_type

    user_extension = f"'{hotdesk.extension_type}/{hotdesk.extension}'"
    extensions = ",".join(request.session.get('selected_extensions', [user_extension]))

    start = "2022-11-21 00:00:00"
    end = "2022-11-21 23:59:59"
    data['outbound_calls'] = pbx_get_outbound_calls_from_database(backend_id, start, end, extensions)

    return render(
        request, "helpline/stats.html",
        data
    )


def incoming_calls_summary(backend_id, report_config):
    """Get summary of incoming calls from backend pbx"""
    # Counts incoming calls for graph
    otherchanfield = "channel"

    incoming_calls_query = f"SELECT substring({otherchanfield},1,locate(\"-\",{otherchanfield},length({otherchanfield})-8)-1) AS chan1,"
    incoming_calls_query+= "billsec,duration,duration-billsec as ringtime,accountcode FROM asteriskcdrdb.cdr "
    incoming_calls_query+= f"WHERE calldate >= '{report_config['start']}' AND calldate <= '{report_config['end']}' AND (duration-billsec) >=0 {report_config['condicionextra']} "
    incoming_calls_query+= f"HAVING chan1 in ({report_config['extension']}) order by null"

    number_in_calls = {}
    report_config['departments']     = {}
    departments = {}
    billsec         = {}
    total_ring      = 0
    total_calls     = 0
    inbound_stats = []
    try:
        backend_manager_config = BackendServerManagerConfig.objects.get(
            id=backend_id
        )
    except BackendServerManagerConfig.DoesNotExist:
        backend_manager_config = None
        return []
    username = backend_manager_config.mysql_user
    password = backend_manager_config.mysql_password
    host = backend_manager_config.host
    if backend_manager_config.mysql_host:
        database_host = backend_manager_config.mysql_host
    else:
        database_host = backend_manager_config.host
    try:
        mydb = mysql.connector.connect(
            host=database_host,
            user=username,
            password=password,
            database="asterisk"
        )
    except Error as e:
        return(f"Error while connecting to MySQL {e}")

    mycursor = mydb.cursor()

    mycursor.execute(
     incoming_calls_query
    )
    # this will extract row headers
    row_headers = [x[0] for x in mycursor.description]
    myresult = mycursor.fetchall()

    for result in myresult:
        json_result = dict(zip(row_headers, result))
        json_result['accountcode'] = 'Default'
        if not number_in_calls["Default"].get(json_results['chan1'], False):
            number_in_calls["Default"][json_results['chan1']] = 0
        else:
            number_in_calls["Default"][json_results['chan1']] += 1

        inbound_stats.append(json_result)

    return inbound_stats


def get_records_factory(backend_id, report_config):
    """Get outbound stats summary from backend pbx"""
    # Then outbound
    start_time = time.time()
    cdr_records = []
    chanfield = "channel"
    try:
        backend_manager_config = BackendServerManagerConfig.objects.get(
            id=backend_id
        )
    except BackendServerManagerConfig.DoesNotExist:
        backend_manager_config = None
        return []
    username = backend_manager_config.mysql_user
    password = backend_manager_config.mysql_password
    host = backend_manager_config.mysql_host
    if backend_manager_config.mysql_host:
        database_host = backend_manager_config.mysql_host
    else:
        database_host = backend_manager_config.host
    try:
        mydb = mysql.connector.connect(
            host=database_host,
            user=username,
            password=password,
            database="asteriskcdrdb"
        )
    except Error as e:
        return(f"Error while connecting to MySQL {e}")

    mycursor = mydb.cursor()

    if report_config['direction'] == 'outgoing':
        query = f"SELECT substring({chanfield},1,locate(\"-\",{chanfield},length({chanfield})-8)-1) AS chan1,"
        query+= f"billsec,duration,duration-billsec as ringtime,src,dst,calldate,disposition,accountcode FROM asteriskcdrdb.cdr "
        query+= f"WHERE calldate >= '{report_config['start']}' AND calldate <= '{report_config['end']}' AND (duration-billsec) >=0 {report_config['condicionextra']} "
        query+= f"HAVING chan1 in ({report_config['extension']}) order by null;"
    elif report_config['direction'] == 'incoming':
        query = "SELECT substring(dstchannel,1,locate(\"-\",dstchannel,1)-1) AS chan1, billsec, calldate,"
        query+= "billsec, calldate,"
        query+= "(time_to_sec(calldate)-(hour(calldate)*3600)+billsec)-3600 AS minute, hour(calldate) AS hour,date_format(calldate,'%Y%m%d') AS fulldate "
        query+= "FROM asteriskcdrdb.cdr WHERE  substring(dstchannel,1,locate(\"-\",dstchannel,1)-1)<>'' "
        query+= f"AND calldate >= '{report_config['start']}' AND calldate <= '{report_config['end']}' AND (duration-billsec) >=0 "
        query+= f"HAVING chan1 IN ({report_config['extension']}) ORDER BY calldate"
    elif report_config['direction'] == 'calldistributionperhour':
        query = "SELECT hour(calldate) AS hour, count(*) AS count, SUM(billsec) AS seconds FROM asteriskcdrdb.cdr ";
        query+= "WHERE  substring(dstchannel,1,locate(\"-\",dstchannel,1)-1)<>'' ";
        query+= f"AND calldate >= '{report_config['start']}' AND calldate <= '{report_config['end']}' AND (duration-billsec) >=0 ";
        query+= f"AND ( substring(dstchannel,1,locate(\"-\",dstchannel,1)-1) IN ({report_config['extension']}) OR substring(channel,1,locate(\"-\",channel,1)-1) IN ({report_config['extension']})) ";
        query+= "GROUP BY 1 ORDER BY calldate";
    elif report_config['direction'] == 'outbound':
        chanfield      = "channel"
        query = f"SELECT substring({chanfield},1,locate(\"-\",{chanfield},length({chanfield})-8)-1) AS chan1,";
        query+= "billsec,duration,duration-billsec as ringtime,src,dst,calldate,disposition,accountcode FROM asteriskcdrdb.cdr "
        query+= f"WHERE calldate >= '{report_config['start']}' AND calldate <= '{report_config['end']}' AND (duration-billsec) >=0 {report_config['condicionextra']} ";
        query+= f"HAVING chan1 in ({report_config['extension']}) order by null"
    else:
        query = f"SELECT substring({chanfield},1,locate(\"-\",{chanfield},length({chanfield})-8)-1) AS chan1,"
        query+= f"billsec,duration,duration-billsec as ringtime,src,dst,calldate,disposition,accountcode FROM asteriskcdrdb.cdr "
        query+= f"WHERE calldate >= '{report_config['start']}' AND calldate <= '{report_config['end']}' AND (duration-billsec) >=0 {report_config['condicionextra']} "
        query+= f"HAVING chan1 in ({report_config['extension']}) order by null;"

    mycursor.execute(
        query
    )

    # this will extract row headers
    row_headers = [x[0] for x in mycursor.description]
    myresult = mycursor.fetchall()
    json_data = []

    # Get list of departments from reports config, use default if not set
    departments = report_config.get("departments",  {'Default': 0})
    group_bill_outbound = {}
    group_ring_outbound = {}
    group_calls_outbound = {}

    # default totals
    total_calls = 0
    total_bill = 0
    total_ring = 0

    billsec = {}
    number_calls_outbound = {}
    number_calls_inbound = {}
    number_calls = {}
    duration = {}
    missed_outbound = {}
    missed = {}
    ringing = {}
    ringing_outbound = {}
    total_bill_outbound = {}
    total_ring_outbound = {}
    total_calls_outbound = 0

    for result in myresult:
        json_result = dict(zip(row_headers, result))
        json_result['accountcode'] = 'Default'
        if not departments.get(json_result['accountcode'], False):
            departments[json_result['accountcode']] = {}
        if not billsec.get(json_result['accountcode'], False):
            billsec[json_result['accountcode']] = {}
            billsec[json_result['accountcode']][json_result['chan1']] = 0
        if not number_calls_outbound.get(json_result['accountcode'], False):
            number_calls_outbound[json_result['accountcode']] = {}
            number_calls_outbound[json_result['accountcode']][json_result['chan1']] = 0
        if not number_calls_inbound.get(json_result['accountcode'], False):
            number_calls_inbound[json_result['accountcode']] = {}
            number_calls_inbound[json_result['accountcode']][json_result['chan1']] = 0
        if not number_calls.get(json_result['accountcode'], False):
            number_calls[json_result['accountcode']] = {}
            number_calls[json_result['accountcode']][json_result['chan1']] = 0
        if not duration.get(json_result['accountcode'], False):
            duration[json_result['accountcode']] = {}
            duration[json_result['accountcode']][json_result['chan1']] = 0
        if not ringing.get(json_result['accountcode'], False):
            ringing[json_result['accountcode']] = {}
            ringing[json_result['accountcode']][json_result['chan1']] = 0
        if not ringing_outbound.get(json_result['accountcode'], False):
            ringing_outbound[json_result['accountcode']] = {}
            ringing_outbound[json_result['accountcode']][json_result['chan1']] = 0
        if not total_bill_outbound.get(json_result['accountcode'], False):
            total_bill_outbound[json_result['accountcode']] = {}
            total_bill_outbound[json_result['accountcode']][json_result['chan1']] = 0
        if not total_ring_outbound.get(json_result['accountcode'], False):
            total_ring_outbound[json_result['accountcode']] = {}
            total_ring_outbound[json_result['accountcode']][json_result['chan1']] = 0
        if not group_bill_outbound.get(json_result['accountcode'], False):
            group_bill_outbound[json_result['accountcode']] = 0
        if not group_calls_outbound.get(json_result['accountcode'], False):
            group_calls_outbound[json_result['accountcode']] = 0


        billsec[json_result['accountcode']][json_result['chan1']]+=json_result['billsec']
        duration[json_result['accountcode']][json_result['chan1']] +=json_result['duration']
        number_calls_outbound[json_result['accountcode']][json_result['chan1']] +=1
        number_calls[json_result['accountcode']][json_result['chan1']] += 1
        if not missed_outbound.get(json_result['accountcode'], False):
            missed_outbound[json_result['accountcode']] = {}
            missed_outbound[json_result['accountcode']][json_result['chan1']]=0
        if not group_ring_outbound.get(json_result['accountcode'], False):
            group_ring_outbound[json_result['accountcode']] = 0

        ringing[json_result['accountcode']][json_result['chan1']]+=json_result['ringtime']
        ringing_outbound[json_result['accountcode']][json_result['chan1']]+=json_result['ringtime']
        total_bill_outbound[json_result['accountcode']][json_result['chan1']]+=json_result['billsec']
        total_ring_outbound[json_result['accountcode']][json_result['chan1']]+=json_result['ringtime']
        total_calls_outbound+=1

        group_bill_outbound[json_result['accountcode']] +=json_result['billsec']

        group_ring_outbound[json_result['accountcode']]  += json_result['ringtime']
        group_calls_outbound[json_result['accountcode']] += 1

        disposition = json_result['disposition']

        if not missed.get(json_result['accountcode'], False):
            missed[json_result['accountcode']] = {}
            missed[json_result['accountcode']][json_result['chan1']] = 0

        if disposition != "ANSWERED":
            missed_outbound[json_result['accountcode']][json_result['chan1']]+=1
            missed[json_result['accountcode']][json_result['chan1']]+=1

        json_result['accountcode'] = 0
        json_data.append(json_result)

    mycursor.close()
    mydb.close()
    summary_data = {
        'group_calls_outbound': group_calls_outbound,
        'group_bill_outbound': group_bill_outbound,
        'group_ring_outbound': group_ring_outbound,
        'total_calls_outbound': total_calls_outbound,
        'total_bill_outbound': total_bill_outbound,
        'total_ring_outbound': total_ring_outbound,
        'departments': departments,
    }

    if not report_config.get('summary', False):
        return {
            'records': json_data,
            'summary': summary_data,
            'query': query,
            'execution_time': time.time() - start_time,
        }
    else:
        return {
            'summary': summary_data,
            'query': query,
            'execution_time': time.time() - start_time,
        }


def outbound_stats_summary(backend_id, report_config):
    """Get outbound stats summary from backend pbx"""
    # Then outbound
    outbound_stats_summary_data = []
    data = {}
    chanfield = "channel"
    try:
        backend_manager_config = BackendServerManagerConfig.objects.get(
            id=backend_id
        )
    except BackendServerManagerConfig.DoesNotExist:
        backend_manager_config = None
        return []
    username = backend_manager_config.mysql_user
    password = backend_manager_config.mysql_password
    host = backend_manager_config.mysql_host
    if backend_manager_config.mysql_host:
        database_host = backend_manager_config.mysql_host
    else:
        database_host = backend_manager_config.host
    try:
        mydb = mysql.connector.connect(
            host=database_host,
            user=username,
            password=password,
            database="asteriskcdrdb"
        )
    except Error as e:
        return(f"Error while connecting to MySQL {e}")

    mycursor = mydb.cursor()

    outbound_query = f"SELECT substring({chanfield},1,locate(\"-\",{chanfield},length({chanfield})-8)-1) AS chan1,"
    outbound_query+= f"billsec,duration,duration-billsec as ringtime,src,dst,calldate,disposition,accountcode FROM asteriskcdrdb.cdr "
    outbound_query+= f"WHERE calldate >= '{report_config['start']}' AND calldate <= '{report_config['end']}' AND (duration-billsec) >=0 {report_config['condicionextra']} "
    outbound_query+= f"HAVING chan1 in ({report_config['extension']}) order by null;"

    mycursor.execute(
        outbound_query
    )

    total_calls = 0
    total_bill  = 0
    total_ring  = 0
    billsec = {}
    departments = {}
    group_ring_outbound = {}
    group_calls_outbound = {}
    duration = {}
    ringing_outbound = {}
    ringing = {}
    number_calls_outbound = {}
    missed_outbound = {}
    number_calls_inbound = {}
    number_calls = {}

    # this will extract row headers
    row_headers = [x[0] for x in mycursor.description]
    myresult = mycursor.fetchall()
    json_data = []
    group_bill_outbound = {}
    report_results = {}
    c = 1
    row_count = len(myresult)

    for result in myresult:
        c += 1

        json_result = dict(zip(row_headers, result))
        json_result['accountcode'] = 'Default'
        report_results[c] = json_result
        billsec[json_result['accountcode']] = {}

        if not departments.get(json_result['accountcode'], False):
            departments[json_result['accountcode']] = ""
            group_bill_outbound[json_result['accountcode']] = 0
            group_ring_outbound[json_result['accountcode']] = 0
            group_calls_outbound[json_result['accountcode']] = 0
            billsec[json_result['accountcode']] = {}
            duration[json_result['accountcode']] = {}
            ringing_outbound[json_result['accountcode']] = {}
            ringing[json_result['accountcode']] = {}
            number_calls_outbound[json_result['accountcode']] = {}
            missed_outbound[json_result['accountcode']] = {}


        if not billsec[json_result['accountcode']].get(json_result['chan1'], False):
            billsec[json_result['accountcode']][json_result['chan1']] = 0
            duration[json_result['accountcode']][json_result['chan1']] = 0
            ringing_outbound[json_result['accountcode']][json_result['chan1']] = 0
            ringing[json_result['accountcode']][json_result['chan1']] = 0
            number_calls_outbound[json_result['accountcode']][json_result['chan1']] = 0
            missed_outbound[json_result['accountcode']][json_result['chan1']] = 0

        if not number_calls_outbound[json_result['accountcode']].get(json_result['chan1'], False):
            number_calls_outbound[json_result['accountcode']][json_result['chan1']]=0
        number_calls_inbound.setdefault(json_result['accountcode'], 0)
        number_calls.setdefault(json_result['accountcode'], json_result['chan1'])

        billsec[json_result['accountcode']][json_result['chan1']]  += json_result['billsec']
        duration[json_result['accountcode']][json_result['chan1']] += json_result['duration']
        number_calls_outbound[json_result['accountcode']][json_result['chan1']] += 1
        #number_calls[json_result['accountcode']][json_result['chan1']] += 1

        ##if not number_in_calls["Default"].get(json_results['chan1'], False):
        ##    number_in_calls["Default"][json_results['chan1']] = 0
        ##else:
        ##    number_in_calls["Default"][json_results['chan1']] += 1

        json_data.append(json_result)

    mycursor.close()
    mydb.close()

    data['report_data'] = json_data
    data['report_query'] = outbound_query
    data['row_headers'] = row_headers
    data['row_count'] = row_count
    data['count'] = c
    return data


def stats_report_factory(backend_id, typereport, report_config):
    """ Return data for outgoing and ingoing stats"""
    graphcolor  = "&bgcolor=0xfffdf3&bgcolorchart=0xdfedf3&fade1=ff6600&fade2=ff6314&colorbase=0xfff3b3&reverse=1";
    graphcolorstack = "&bgcolor=0xfffdf3&bgcolorchart=0xdfedf3&fade1=ff6600&colorbase=fff3b3&reverse=1&fade2=0x528252";
    data = {}

    if typereport == "outgoing":
        otherchanfield = "dstchannel"
        typerecord="outgoing"
        rep_title = "Outgoing Calls"
        tagA=_("Outgoing")
        tagB=_("Incoming")
        data['typereport'] = typereport
        data['report'] = outbound_stats_summary(backend_id, report_config)

    else:
        chanfield = "dstchannel"
        otherchanfield = "channel"
        typerecord="incoming"
        rep_title = _('Incoming Calls')
        tagB=_("Outgoing")
        tagA=_("Incoming")
        # Get inbount stats
        data['typereport'] = typereport
        data['report'] = incoming_calls_summary(backend_id, report_config)

    return data


@json_view
def get_records(request):
    """ Request data """
    # config.php?type=tool&display=asternic_cdr&tab=home&action=getrecords&channel=SIP/1901&direction=outgoing&start=2022-11-08%2000%3A00%3A00&end=2022-11-08%2023%3A59%3A59
    report_config = {}
    get_records_form = GetRecordsForm(request.GET)
    report_config['summary'] = request.GET.get("summary", False)
    if not get_records_form.is_valid():
        return {'success': False, 'message': 'Not valid'}
    report_config['channel'] = get_records_form.cleaned_data.get('channel')
    report_config['extension'] = "'"+get_records_form.cleaned_data.get('channel')+"'"
    report_config['direction'] = get_records_form.cleaned_data.get('direction')
    report_config['start'] = get_records_form.cleaned_data.get('start')
    report_config['end'] = get_records_form.cleaned_data.get('end')
    report_config['condicionextra'] = ''
    # report config = channel, direction, start, end
    backend_id = 3
    data = get_records_factory(backend_id, report_config)
    return {'data': data, 'report_config': report_config}



@csrf_exempt
@login_required
def stats_report(request, report='outbound'):
    """Outbound and inbound stats from PBX"""
    if not request.session.get('selected_extensions', False):
        return redirect("/helpline/stats/")

    report_config = {}

    year1 = request.session.get("year1", 2022)
    month1 = request.session.get("month1", 11)
    day1 = request.session.get("day1", 7)
    year2 = request.session.get("year2", 2022)
    month2 = request.session.get("month2", 11)
    day2 = request.session.get("day2", 7)

    report_config['start'] = f'{year1}-{month1}-{day1} 00:00:00'
    report_config['end'] = f'{year2}-{month2}-{day2} 23:59:59'
    report_config['condicionextra'] = ''
    backend_id = 3
    report_config['direction'] = 'outbound'
    report_data = []
    data = {}
    for extension in request.session.get('selected_extensions'):
        report_config['extension'] = extension
        records = get_records_factory(backend_id, report_config)
        report_data.append(records)

    data['report_data'] =  report_data

    return render(
        request, "helpline/stats_report.html",
        data
    )


@json_view
@login_required
def hourly_call_distribution(request, report='outbound'):
    """Get call distribution per hour"""
    default_start = datetime.combine(
        date.today(), datetime_time.min).strftime('%Y-%m-%d %H:%M:%S')
    default_end = datetime.combine(
        date.today(), datetime_time.max).strftime('%Y-%m-%d %H:%M:%S')

    start = request.GET.get("start", default_start)
    end = request.GET.get("end", default_end)

    data = {}
    query = f"""SELECT hour(calldate) AS hour, count(*) AS count, SUM(billsec) AS seconds FROM asteriskcdrdb.cdr WHERE dstchannel='' AND calldate >= '{start}' AND calldate <= '{end}' AND (duration-billsec) >=0 GROUP BY 1 ORDER BY calldate"""
    hotdesk = get_hotdesk(request.user)
    backend_manager_config = hotdesk.backend_manager_config

    username = backend_manager_config.mysql_user
    password = backend_manager_config.mysql_password
    host = backend_manager_config.host
    if backend_manager_config.mysql_host:
        database_host = backend_manager_config.mysql_host
    else:
        database_host = backend_manager_config.host
    try:
        mydb = mysql.connector.connect(
            host=database_host,
            user=username,
            password=password,
            database="asteriskcdrdb"
        )
    except Error as e:
        return(f"Error while connecting to MySQL {e}")

    mycursor = mydb.cursor()

    mycursor.execute(
    query
    )
    # this will extract row headers
    row_headers = [x[0] for x in mycursor.description]
    myresult = mycursor.fetchall()
    hourly_call_distribution_stats = []

    for result in myresult:
        json_result = dict(zip(row_headers, result))
        hourly_call_distribution_stats.append(json_result)

    data['hourly_call_distribution'] = hourly_call_distribution_stats
    data['start'] = start
    data['end'] = end

    return data


@json_view
def load_campiagn_csv(request):
    data = {}
    return data

# username=foralice&password=alice%2B007&email=alice%40callcenter.africa&phoneNumber=&display_name=Alice
@json_view
@csrf_exempt
def enrollment_mobile(request):
    data = {
        "success": True,
        "sip_address": "foralice@callcenter.africa",
        "email": "alice@callcenter.africa",
        "settings_url": "https://blink.sipthor.net/settings.phtml",
        "outbound_proxy": None,
        "ldap_hostname": "ldap.sipthor.net",
        "ldap_dn": "ou=addressbook, dc=sylk.link, dc=info",
        "msrp_relay": "msrprelay.sipthor.net",
        "xcap_root": "https://xcap.sipthor.net/xcap-root/",
        "conference_server": "conference.sip2sip.info",
    }
    return data


@login_required
def qa_form(request):
    """ QA Form view"""

    return render(
        request, "helpline/qaform.html", {}
    )


@login_required
def monitoring(request):
    """Return list of campaigns"""
    hotdesk = get_hotdesk(request.user)
    if not hotdesk:
        raise Http404(_("Page not found"))

    cdr_data = get_data_call_details(backend_id=hotdesk.backend_manager_config.id)

    data = {
        'cdr_data': cdr_data,
        'version': 2,
    }
    return render(
        request,
        'helpline/monitoring.html',
        data
    )


def get_related_extensions(user):
    """ Get a list of extensions related to a user"""
    users = []
    services = []
    for schedule in get_schedules(user):
        if schedule.service.pk != 1:
            services.append(schedule.service)
    related_schedules = Schedule.objects.filter(service__in=set(services))
    for schedule in related_schedules:
        users.append(schedule.user)

    team_hot_desks = []
    for user in set(users):
        hotdesk = get_hotdesk(user)
        if hotdesk:
            team_hot_desks.append(hotdesk.extension)

    return team_hot_desks

@login_required
def cdr_report(request):
    # Time mesurement
    start_time = time.time()
    CDR_REPORT_CACHE_TIMEOUT = 10
    if request.user.is_staff:
        hot_desks = []
        hot_desks = cache.get_or_set(
            f"user_related_extensions_{request.user}",
            get_related_extensions(request.user),
            CDR_REPORT_CACHE_TIMEOUT
        )
    else:
        hotdesk = get_hotdesk(request.user)
        hot_desks = [hotdesk]

    test_execution_time = time.time() - start_time

    # Data view displays submission data.
    query = request.GET.get('q', '')
    datetime_range = request.GET.get("datetime_range")
    agent = request.GET.get("agent")
    category = request.GET.get("category", "")
    form = ReportFilterForm(request.GET)
    error = None
    from_cache = None
    cache_key = hashlib.md5("f{query}".encode('utf-8')).hexdigest()

    try:
        backend_id = hotdesk.backend_manager_config.pk
    except:
        backend_id = None

    call_history_table = cache.get(
        f'call_history_table_{backend_id}_{cache_key}'
    )

    if not call_history_table:
        try:
            cache.set(
                f'call_history_table_{backend_id}_{cache_key}',
                get_call_history_table(hot_desks, query),
                CDR_REPORT_CACHE_TIMEOUT
            )
            call_history_table = cache.get(
                f'call_history_table_{backend_id}_{cache_key}'
            )
            from_cache = False
        except Exception as e:
            call_history_table = None
            error = e

    if call_history_table:
        call_history_table.paginate(
            page=request.GET.get("page", 1), per_page=10
        )

    return render(request, 'helpline/cdr_report.html',
                  {
                      'hot_desks': hot_desks,
                      'form': form,
                      'error': error,
                      'from_cache': from_cache,
                      'query': query,
                      'call_history_table': call_history_table,
                      'test_execution_time': test_execution_time,
                      'execution_time': time.time() - start_time
                  })

@login_required
@json_view
@csrf_exempt
def agent_login(request):
    """ECCP agent login."""
    hotdesk = get_hotdesk(request.user)
    eccp_credentials = backend_get_eccp_credentials(hotdesk)
    agent_status = backend_agent_status(eccp_credentials)
    try:
        status = json.loads(agent_status.get('agent_status')[0]).get('status')
    except:
        status = None


    if 'online' == status:
        data =  {
            'eccp_credentials': eccp_credentials,
            'result': agent_status,
            'online': True,
        }
    elif 'offline' == status:
        try:
            backend_agent_login(eccp_credentials)
        except Exception as e:
            return {
                'error_message': str(e),
                'eccp_credentials': eccp_credentials,
                'agent_status': agent_status,
                'status': status,
            }
        data =  {
            'eccp_credentials': eccp_credentials,
            'result': agent_status,
            'status': status,
            'online': False,
        }
    else:
        data =  {
            'eccp_credentials': eccp_credentials,
            'result': agent_status.get('agent_status')[0],
            'status': status,
            'online': False,
        }
    return data


@login_required
def stomp(request):
    """Event handling using Stomp page"""
    hotdesk = get_hotdesk(request.user)

    return render(
        request, "helpline/stomp.html",
        {
            'hotdesk': hotdesk,
        }
    )
