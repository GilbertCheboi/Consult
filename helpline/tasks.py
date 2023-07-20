# -*- coding: utf-8 -*-
"""Helpline celery tasks"""

import time
import urllib
from django.utils import timezone

import os
import base64
from pathlib import Path
import hashlib

import traceback

import json
import requests
from requests.exceptions import ConnectionError
import curlify
import subprocess
import pika

import calendar
from datetime import timedelta, datetime, date, time as datetime_time
from dateutil.relativedelta import relativedelta

from django.conf import settings

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.mail import send_mail
from django.core.mail import EmailMessage
from django.utils.translation import gettext as _

from celery import shared_task
from notifications.signals import notify
import mysql.connector
from mysql.connector import Error

import django_tables2 as tables
from django_tables2.config import RequestConfig
from django_tables2.export.export import TableExport
from django_tables2.export.views import ExportMixin

from helpline.models import BackendServerManagerConfig,\
        DID, Clock, Hotdesk, Schedule, Report, Clock
from helpline.qpanel.backend import Backend
from helpline.eccp import ECCP

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
    partner = tables.Column(accessor='case.case_detail.partner',
                                verbose_name="Partner")
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
                    'disposition', 'casestatus')

def get_schedules(user):
    """Get schedules for a user, use cache"""
    SCHEDULE_LIST_CACHE_TIMEOUT = 5
    data = cache.get_or_set(
        'user_schedule_%s' % (user),
        Schedule.objects.filter(user=user).distinct('service'),
        SCHEDULE_LIST_CACHE_TIMEOUT
    )
    return data

def report_factory_task(report='callsummary', datetime_range=None, agent=None,
                   queuename=None, queueid=None, query=None, sort=None,
                   casetype='all', category=None, user=None):
    """Create admin reports task"""

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


@shared_task(time_limit=300)
def get_report_file(user, report=None, casetype='Call', query=None,
                    datetime_range=None, agent=None, category=None, export_format='csv'):
    """Get a CSV report to be emailed or downloaded"""

    file_name_str = time.strftime("%Y%m%d-%H%M%S.") + export_format
    file_dir = os.path.join(settings.MEDIA_ROOT,
                             user.username,
                             "report_export",
                             export_format)

    # Create directory for report export
    Path(file_dir).mkdir(parents=True, exist_ok=True)

    file_name = os.path.join(file_dir,
                             file_name_str)

    report_title = {report: _(str(report).capitalize() + " Reports")}

    table = report_factory_task(report=report,
                           datetime_range=datetime_range,
                           agent=agent,
                           query=query,
                           category=category,
                           casetype=casetype,
                           user=user)

    # Export table to csv
    if TableExport.is_valid_format(export_format):
        exporter = TableExport(export_format, table)
        exporter_response = exporter.response('table.{}'.format(export_format))

    with open(file_name, 'wb') as f:
        f.write(exporter_response.content)

    msg = EmailMessage('Export Data %s' % (file_name_str), 'Please find attached.', 'robots@zerxis.co.ke', [user.email])
    msg.content_subtype = "html"
    msg.attach_file(file_name)
    msg.send()

    return file_name


@shared_task(ignore_result=True, time_limit=13)
def get_queues_data(backend_id):
    """Get queue data from backend server
    Customize results based on user
    """

    # How long to cache backend queue data in seconds
    QUEUE_DATA_CACHE_TIMEOUT = 6

    start_time = time.time()
    # Use backend server configs or use default Backend
    if not cache.get(f'backend_queues_data_{backend_id}'):
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
                f'backend_queues_data_{backend_id}',
                queue_data,
                QUEUE_DATA_CACHE_TIMEOUT
            )
        except Exception as e:
            return "ERROR %s %s %s" % (backend_id, traceback.format_exc(), e)

    # Return execution time for future debuging
    # i.e slow servers can be identified
    return {
        'execution_time': time.time() - start_time,
        'backend_id': backend_id,
    }


def pbxapi_get_auth_token(url, username, password):
    """Get JWT Auth Token from PBX API
    Return from cache if token is found"""
    data = {'user': username, 'password': password}
    response = requests.post(url, data, verify=False, timeout=120)
    try:
        json_data = response.json()
    except:
        json_data = {
            "json": "Error",
            "curl": curlify.to_curl(response.request),
        }

    return {
        'status_code': response.status_code,
        'text': response.text,
        'json': json_data
    }


def pbxapi_update_extension(url, auth_token, data):
    """Update or create extension object in PBX"""
    headers = {
        "Authorization": "Bearer " + auth_token,
        "Content-Type": "application/json"
    }
    response = requests.put(
        url,
        data="%s" % json.dumps(data),
        headers=headers,
        verify=False
    )
    return {
        'status_code': response.status_code,
        'text': response.text,
        'data': data,
        'headers': headers,
        'curl': curlify.to_curl(response.request),
    }


def pbxapi_get_extension(url, auth_token):
    """Get list of extensions from PBX API"""
    try:
        headers = {'Authorization': 'Bearer ' + auth_token}
        response = requests.get(url, headers=headers, verify=False, timeout=3600)
    except Exception as e:
        return {
            'status_code': 500,
            'json': {},
            'text': e
        }
    try:
        json_data = response.json()
    except:
        json_data = {"json": "Error"}
    return {
        'status_code': response.status_code,
        'json': json_data,
        'text': response.text
    }


def get_hotdesk(user_id):
    hotdesk = cache.get_or_set('%s_active_hotdesk' % (user_id),
    Hotdesk.objects.filter(
        user=User.objects.get(id=user_id),
        status='Available',
        secret__isnull=False,
        backend_manager_config__isnull=False
        ).first(),
                               7200
    )
    return hotdesk


def pbxapi_get_outbound_caller_id(user_id):
    """Get list of outbound caller ids for a given hotdesk"""
    # For now we will use the static get_hotdesk function
    user = User.objects.get(id=user_id)
    hotdesk = cache.get_or_set('%s_active_hotdesk' % (user.username),
    Hotdesk.objects.filter(
        user=user,
        status='Available',
        secret__isnull=False,
        backend_manager_config__isnull=False
        ).first(),
                               7200
    )

    if not hotdesk:
        return {'message': 'No hotdesk', 'user_id': user_id}
    backend_server = hotdesk.backend_manager_config
    if not backend_server:
        return {'meessage': 'No backend server defined'}

    pbxapi_url = backend_server.pbxapi_url
    pbxapi_user = backend_server.pbxapi_user
    pbxapi_password = backend_server.pbxapi_password
    if not pbxapi_url or pbxapi_user is None:
        return {
            "message": "Backend PBX API Not Set",
            "success": False,
            "did": []
        }

    auth_endpoint_url = urllib.parse.urljoin(
        pbxapi_url, "pbxapi/authenticate"
    )
    endpoint_url = urllib.parse.urljoin(
        pbxapi_url, "pbxapi/extensions/%s" % (hotdesk.extension)
    )
    auth_token = pbxapi_get_auth_token(
        auth_endpoint_url,
        pbxapi_user,
        pbxapi_password,
    )
    if auth_token.get('status_code') == 403:
        return {
            'message': 'Error 403',
            'hotdesk': hotdesk.extension,
            'success': False
        }

    if auth_token:
        access_token = auth_token.get('json').get('access_token')
        extension = pbxapi_get_extension(
            endpoint_url,
            access_token,
        )
        dids = list(DID.objects.filter(hotdesk=hotdesk).values_list('number'))
        return {
            'message': 'Success',
            'endpoint_url': endpoint_url,
            'extension': extension,
            'success': True,
            'did': dids,
        }
    else:
        access_token = auth_token
        return {
            'message': 'Error',
            'success': False,
        }


def set_inbound_route(url, access_token, outbound_caller_id, hotdesk):
    """Set an inbound route and forward calls to extension"""
    headers = {
        "Authorization": "Bearer " + access_token,
        "Content-Type": "application/json"
    }
    data = {
        "cidnum": "",
        "destination": "from-did-direct,%s,1" % (hotdesk.extension),
        "extension": outbound_caller_id,
        "description": "DirectTo%s" % (hotdesk.extension)
    }
    response = requests.post(
        url,
        data="%s" % json.dumps(data),
        headers=headers,
        verify=False,
        timeout=30
    )
    return {
        'status_code': response.status_code,
        'text': response.text,
        'data': data,
    }


@shared_task
def pbxapi_set_outbound_caller_id(user_id, outbound_caller_id):
    """Send request to PBX API to change Outbound Caller ID"""
    user = User.objects.get(id=user_id)
    hotdesk = cache.get_or_set('%s_active_hotdesk' % (user.username),
    Hotdesk.objects.filter(
        user=user,
        status='Available',
        secret__isnull=False,
        backend_manager_config__isnull=False
        ).first(),
                               7200
    )
    backend_server = hotdesk.backend_manager_config
    pbxapi_url = backend_server.pbxapi_url
    pbxapi_user = backend_server.pbxapi_user
    pbxapi_password = backend_server.pbxapi_password
    auth_endpoint_url = urllib.parse.urljoin(
        pbxapi_url, "pbxapi/authenticate"
    )
    endpoint_url = urllib.parse.urljoin(
        pbxapi_url, "pbxapi/extensions/%s" % (hotdesk.extension)
    )
    inboundroute_url = urllib.parse.urljoin(
        pbxapi_url, "pbxapi/inboundroutes"
    )
    auth_token = pbxapi_get_auth_token(
        auth_endpoint_url,
        pbxapi_user,
        pbxapi_password,
    )
    if auth_token.get('status_code') == 403:
        return {
            'message': 'Error 403',
            'hotdesk': hotdesk.extension,
            'success': False
        }

    if auth_token:
        access_token = auth_token.get('json').get('access_token')
        data = {
            "outboundcid": outbound_caller_id,
        }
        update_extension = pbxapi_update_extension(
            endpoint_url,
            access_token,
            data
        )

        # Delete Cached Outbound Caller ID
        cache.delete('outbound_caller_id_%s' % (user_id))

        # Only set inbound route for specific backends
        # List of IDs used is below
        INBOUND_ROUTE_BACKENDS = [8, 11]

        # Only set inbound route if outbound CID is set
        if outbound_caller_id and backend_server.id in INBOUND_ROUTE_BACKENDS:
            inbound_route_set = set_inbound_route(
                inboundroute_url,
                access_token,
                outbound_caller_id,
                hotdesk
            )
        else:
            inbound_route_set = {"message": "Inbound route not set"}

        # Monitor feature use by notifing super users
        super_users = User.objects.filter(is_superuser=True)
        for u in super_users:
            description = "%s changed DID to %s %sconfig.php?type=setup&display=extensions&extdisplay=%s" % (
                hotdesk,
                outbound_caller_id,
                pbxapi_url,
                hotdesk
            )
            verb = "DID changed"

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

        return {
            'message': 'Success',
            'endpoint_url': endpoint_url,
            'update_extension': update_extension,
            'outbound_caller_id': outbound_caller_id,
            'inbound_route_set': inbound_route_set,
            'success': True,
        }
    else:
        access_token = auth_token
        return {
            'message': 'Error',
            'outbound_caller_id': outbound_caller_id,
            'success': False,
        }


@shared_task(ignore_result=True)
def cache_outbound_caller_id(user_id):
    """Store Outbound Caller ID in Cache"""
    try:
        data = pbxapi_get_outbound_caller_id(user_id)
    except ConnectionError as e:
        data = {}
        return e

    cache.set("outbound_caller_id_%s" % (user_id), data, 7200)


def click_to_call(user_id, phone):
    """Get list of outbound caller ids for a given hotdesk"""
    # For now we will use the static get_hotdesk function
    start_time = time.time()
    hotdesk = get_hotdesk(user_id)
    if not hotdesk:
        return {
            "message": "No hotdesk found for User " + user_id,
            "execution_time": time.time() - start_time,
        }

    try:
        backend_id = hotdesk.backend_manager_config.pk
    except:
        backend_id = None

    if backend_id and phone:
        try:
            backend_manager_config = BackendServerManagerConfig.objects.get(
                id=backend_id
            )
        except BackendServerManagerConfig.DoesNotExist:
            backend_manager_config = None
            return {
                'execution_time': time.time() - start_time,
                'backend_id': backend_id,
            }

        backend = Backend(
            backend_manager_config
        ) if backend_manager_config else Backend()
        extension = "%s/%s" % (hotdesk.extension_type, hotdesk.extension)

        res = backend.originate_call(
            extension,
            phone,
        )
        return res
    else:
        return {
            'execution_time': time.time() - start_time,
            'backend_id': backend_id,
        }


def pbxapi_get_extensions(backend_id):
    """Get list of extensions from backend PBX"""
    start_time = time.time()
    if backend_id:
        try:
            backend_manager_config = BackendServerManagerConfig.objects.get(
                id=backend_id
            )
        except BackendServerManagerConfig.DoesNotExist:
            backend_manager_config = None
            return {
                'execution_time': time.time() - start_time,
                'backend_id': backend_id,
                'message': "Backend Server Not Found",
            }

    backend_server = backend_manager_config
    if not backend_server:
        return {'meessage': 'No backend server defined'}

    pbxapi_url = backend_server.pbxapi_url
    pbxapi_user = backend_server.pbxapi_user
    pbxapi_password = backend_server.pbxapi_password
    if not pbxapi_url or pbxapi_user is None:
        return {
            "message": "Backend PBX API Not Set",
            "success": False,
            "did": []
        }

    auth_endpoint_url = urllib.parse.urljoin(
        pbxapi_url, "pbxapi/authenticate"
    )
    endpoint_url = urllib.parse.urljoin(
        pbxapi_url, "pbxapi/extensions/"
    )
    auth_token = pbxapi_get_auth_token(
        auth_endpoint_url,
        pbxapi_user,
        pbxapi_password,
    )
    if auth_token.get('status_code') == 403:
        return {
            'message': 'Error 403',
            'backend_id': backend_id,
            'success': False
        }

    if auth_token:
        access_token = auth_token.get('json').get('access_token')
        extension = pbxapi_get_extension(
            endpoint_url,
            access_token,
        )
        return {
            'message': 'Success',
            'endpoint_url': endpoint_url,
            'extension': extension,
            'success': True,
        }


@shared_task(ignore_result=True)
def get_login_durations(midnight):
    """Get all agent session items from last midnight
    Calculate the login duration
    """
    start_time = time.time()

    # Get all users that have clocked in today
    clock_users = Clock.objects.filter(
        hl_time__gte=midnight).values("user").distinct()
    print("Clock QUERY Execution time: %s " % (time.time() - start_time))

    # Update each user cache with login duration
    for clock_user in clock_users:
        user_id = clock_user.get("user")
        if not cache.get('login_duration_%s' % (user_id)):
            if user_id:
                login_time = logout_time = Clock.objects.filter(
                    user__id=user_id, hl_time__gte=midnight, hl_clock="Login").first()
                logout_time = Clock.objects.filter(
                    user__id=user_id, hl_time__gte=midnight, hl_clock="Logout").last()
                if logout_time and login_time:
                    seconds = logout_time.hl_time - login_time.hl_time
                    login_duration = str(timedelta(seconds=seconds))
                    try:
                        hotdesk = get_hotdesk(user_id)
                        if hotdesk and seconds > 0:
                            cache.set(
                                "login_duration_%s" % (user_id),
                                login_duration,
                                30
                            )
                            cache.set(
                                "hotdesk_login_duration_%s" % (hotdesk.extension),
                                login_duration,
                                30
                            )
                    except Exception as e:
                        print(str(e))
    print("Login Duration Execution time: %s " % (time.time() - start_time))


def pbx_auth_encode(backend_id, username, password, extension=None):
    """Encode base64 auth code"""
    if extension:
        auth_basic = f"{backend_id}:{username}:{password}:{extension}"
    else:
        auth_basic = f"{backend_id}:{username}:{password}"

    auth_basic_bytes = auth_basic.encode("ascii")

    auth_base64_bytes = base64.b64encode(auth_basic_bytes)
    auth_base64_string = auth_base64_bytes.decode("ascii")
    return auth_base64_string


def get_data_campaign(backend_id=None, campaign_id=None, status=None, limit=None):
    """ Get data about a campaign"""
    start_time = time.time()
    try:
        backend_manager_config = BackendServerManagerConfig.objects.get(
            id=backend_id
        )
    except BackendServerManagerConfig.DoesNotExist:
        backend_manager_config = None
        return {
            'backend_id': backend_id,
            'message': "Backend not found",
        }

    username = backend_manager_config.mysql_user
    password = backend_manager_config.mysql_password
    host = backend_manager_config.host
    if backend_manager_config.mysql_host:
        database_host = backend_manager_config.mysql_host
    else:
        database_host = backend_manager_config.host
    webhook_url = backend_manager_config.webhook_url if backend_manager_config.webhook_url else None
    api_key = pbx_auth_encode(
        backend_manager_config.id,
        backend_manager_config.pbxapi_user,
        backend_manager_config.pbxapi_password
    )


    try:
        mydb = mysql.connector.connect(
            host=database_host,
            user=username,
            password=password,
            database="call_center"
        )
    except Error as e:
        return(
            {
                "error": True,
                "message": f"Error while connecting to MySQL {e}",
            }
        )

    mycursor = mydb.cursor()

    if campaign_id:
        mycursor.execute(
            f"SELECT * FROM `campaign` WHERE id='{campaign_id}'"
        )
    else:
        if backend_id == 17:
            mycursor.execute(
                "SELECT * FROM `campaign` ORDER BY `id` DESC LIMIT 1000"
            )
        else:
            mycursor.execute(
                "SELECT * FROM `campaign` ORDER BY `id` DESC LIMIT 500"
            )


    # this will extract row headers
    row_headers = [x[0] for x in mycursor.description]
    myresult = mycursor.fetchall()

    json_data = []
    current_site = Site.objects.get_current()
    status_choices = {
        'A': 'Active',
        'I': 'Inactive',
        'T': 'Finish',
        'NA': 'NA',
    }
    for result in myresult:
        json_result = dict(zip(row_headers, result))
        campaign_name = json_result.get('name')
        result_campaign_id = json_result.get('id')
        campaign_key_bytes = base64.b64encode(f"{backend_id}:{result_campaign_id}".encode('ascii'))
        campaign_key_string = campaign_key_bytes.decode("ascii")
        campaign_start_time = str(json_result.get('daytime_init'))
        campaign_end_time = str(json_result.get('daytime_end'))
        estatus = json_result.get('estatus')

        json_result['average_talk_time'] = json_result.pop('promedio')
        json_result['deviation'] = json_result.pop('desviacion')
        json_result['max_channels'] = json_result.pop('max_canales')
        json_result['num_completed'] = json_result.pop('num_completadas')
        link = f"/helpline/campaign/{campaign_key_string}"

        json_result['key'] = campaign_key_string
        json_result['daytime_init'] = str(campaign_start_time)
        json_result['daytime_end'] = str(campaign_end_time)

        json_result['datetime_init'] = str(json_result.pop('datetime_init'))
        json_result['datetime_end'] = str(json_result.pop('datetime_end'))
        if result_campaign_id:
            # Get total calls for the campaign
            mycursor.execute(
                f"SELECT status, COUNT(*) FROM `calls` WHERE `id_campaign` = '{result_campaign_id}'"

            )
            result = mycursor.fetchone()
            total_calls = result[1]
            json_result['total_calls'] = total_calls

            # Get campaign talk time and hold time
            mycursor.execute(
                f"SELECT SUM(`duration`), SUM(`duration_wait`) FROM `calls` WHERE `id_campaign` = '{result_campaign_id}'"

            )
            result = mycursor.fetchone()
            talk_time = result[0]
            hold_time = result[1]
            json_result['talk_time'] = str(timedelta(seconds=int(talk_time))) if talk_time else "00:00:00"
            json_result['hold_time'] = str(timedelta(seconds=int(hold_time))) if hold_time else "00:00:00"

            mycursor.execute(
                f"SELECT status, COUNT(*) FROM `calls` WHERE `id_campaign` = '{result_campaign_id}' GROUP BY `status`"
            )
            result = mycursor.fetchall()
            json_result['calls'] = {}
            for res in result:
                json_result['calls'][str(res[0])] = res[1]

            abandoned_calls = json_result['calls'].get('Abandoned', 0)
            failed_calls = json_result['calls'].get('Failure', 0)
            successful_calls = json_result['calls'].get('Success', 0)
            not_placed_calls = json_result['calls'].get('None', 0)
            short_calls = json_result['calls'].get('ShortCall', 0)
            json_result['placed_calls'] = abandoned_calls+failed_calls+successful_calls+short_calls
            json_result['not_placed_calls'] = not_placed_calls
            json_result['short_calls'] = short_calls
            json_result['successful_calls'] = successful_calls

        json_result['status'] = status_choices.get(estatus)

        json_result['link'] = link
        json_data.append(json_result)

    mycursor.close()
    mydb.close()

    if campaign_id:
        return {
            'campaign': json_data[0],
            'execution_time': time.time() - start_time,
            'host': host,
            'campaign_id': campaign_id,
            'campaign_name': campaign_name,
            'webhook_url': webhook_url,
            'api_key': api_key,
        }
    return {
        'campaigns': json_data,
        'execution_time': time.time() - start_time,
        'host': host,
        'campaign_id': campaign_id,
        'webhook_url': webhook_url,
        'api_key': api_key,
    }



def get_data_call_details(backend_id=None, start_date=None, end_date=None, limit=None, extensions=None):
    """ Get data about a campaign"""
    start_time = time.time()
    try:
        backend_manager_config = BackendServerManagerConfig.objects.get(
            id=backend_id
        )
    except BackendServerManagerConfig.DoesNotExist:
        backend_manager_config = None
        return {
            'backend_id': backend_id,
            'message': "Backend not found",
        }

    username = backend_manager_config.mysql_user
    password = backend_manager_config.mysql_password
    host = backend_manager_config.host
    if backend_manager_config.mysql_host:
        database_host = backend_manager_config.mysql_host
    else:
        database_host = backend_manager_config.host
    webhook_url = backend_manager_config.webhook_url if backend_manager_config.webhook_url else None
    api_key = pbx_auth_encode(
        backend_manager_config.id,
        backend_manager_config.pbxapi_user,
        backend_manager_config.pbxapi_password
    )


    try:
        mydb = mysql.connector.connect(
            host=database_host,
            user=username,
            password=password,
            database="asteriskcdrdb"
        )
    except Error as e:
        return(
            {
                "error": True,
                "message": f"Error while connecting to MySQL {e}",
            }
        )

    mycursor = mydb.cursor()


    mycursor.execute(
        f"SELECT * FROM `cdr` LIMIT 10;"
    )

    # this will extract row headers
    row_headers = [x[0] for x in mycursor.description]
    myresult = mycursor.fetchall()

    json_data = []
    current_site = Site.objects.get_current()
    disposition_choices = {
        'ANSWERED': 'Answered',
        'FAILED': 'Failed',
        'BUSY': 'Busy',
        'NO ANSWER': 'No Answer',
    }
    for result in myresult:
        json_result = dict(zip(row_headers, result))
        src = json_result.get('src')
        dst = json_result.get('dst')
        uniqueid = json_result.get('uniqueid')
        recording_key_bytes = base64.b64encode(f"{backend_id}:{uniqueid}".encode('ascii'))
        recording_key_string = recording_key_bytes.decode("ascii")
        json_result['recording_key'] = recording_key_string

        json_data.append(json_result)

    mycursor.close()
    mydb.close()

    return {
        'calldetails': json_data,
        'execution_time': time.time() - start_time,
    }


def pbx_auth_decode(auth):
    """Return check pbx authentication backend_id:clientid:clientsecret"""
    auth_basic_bytes = auth.encode('ascii')
    auth_bytes = base64.b64decode(auth_basic_bytes)
    auth = auth_bytes.decode('ascii')

    data = {}
    data['backend_id'] = auth.split(":")[0]
    data['clientid'] = auth.split(":")[1]
    data['clientsecret'] = auth.split(":")[2]

    return data


@shared_task(time_limit=300)
def upload_campaign_data_to_webhook(data):
    """ Use python requests to upload data to webhook url"""
    if data:
        upload_start_time = time.time()
        headers = {
            'User-Agent': 'Call Center Africa',
            'Content-type': 'application/json',
            'apiKey': 'et"Kh4}3?!QAyB{`',
        }
        webhook_res = None
        params = {
            'campaign_id': data.get("campaign_id"),
        }
        campaign_name = data.get("campaign_id")
        campaign_link = data.get("campaign_link")
        num_completed = data.get("num_completed")
        webhook_url = data.get("webhook_url")

        try:
            webhook_res = requests.post(
                webhook_url,
                headers=headers,
                params=params,
                json={'data': data},
            )
        except Exception as e:
            send_mail(
                f'{campaign_name} COMPLETE BUT NOT UPLOADED',
                f"Link: {campaign_link} {e} DATA: {data}",
                'robots@zerxis.co.ke',
                ["patrick@zerxis.com"],
                fail_silently=True,
            )

        upload_execution_time = time.time() - upload_start_time

        if num_completed:
            send_mail(
                f'{campaign_name} COMPLETE',
                f"Link: {campaign_link}/ Completed: {num_completed}\nUPLOADED {campaign_name} to {webhook_url} in {upload_execution_time} seconds\n status: {webhook_res.status_code}\n text: {webhook_res.text}",
                'robots@zerxis.co.ke',
                ["patrick@zerxis.com"],
                fail_silently=True,
            )

        return f"UPLOADED {campaign_name} to {webhook_url} in {upload_execution_time}"
    else:
        return "NO DATA TO UPLOAD"


@shared_task(time_limit=300)
def process_campaign_webhook_data(data):
    """Return json data of a campaign"""
    CAMPAING_JSON_CACHE_TIMEOUT = 600
    start_time = time.time()
    auth_base64 = data.get("auth")
    auth = pbx_auth_decode(auth_base64)
    backend_id = auth.get('backend_id')
    client_id = auth.get('clientid')
    client_secret = auth.get('clientsecret')
    client_secret_md5 = hashlib.md5(client_secret.encode()).hexdigest()

    campaign_id = data.get('id')
    campaign_name = data.get('name')
    num_completed = 0
    download_execution_time = 0
    upload_execution_time = 0

    if cache.get(f"{backend_id}_campaign_json_{campaign_id}"):
        data = cache.get(f"{backend_id}_campaign_json_{campaign_id}")
        campaign_host = data.get("host")
    else:
        campaign_data = get_data_campaign(
            backend_id=backend_id,
            campaign_id=campaign_id
        )
        api_key = campaign_data.pop("api_key")
        campaign = campaign_data.get("campaign") if data else "CACHE MISS"
        campaign_key = campaign.get("key")
        campaign_id = campaign.get("id")
        campaign_host = campaign_data.get("host")
        webhook_url = campaign_data.get("webhook_url")
        campaign_link = campaign.get("link")
        num_completed = campaign.get("num_completed")

        if campaign_host:
            download_start_time = time.time()
            url = f"https://download.callcenter.africa/index.php?menu=campaign_out&action=csv_data&id_campaign={campaign_id}&rawmode=yes&apiKey={auth_base64}"
            res = requests.get(url, verify=False, timeout=300)
            campaign_csv = res.text
            data = campaign_data
            data['res_status_code'] = res.status_code
            data['host'] = campaign_host
            data['campaign_id'] = campaign.get("name")
            data['webhook_url'] = webhook_url
            data['campaign_csv'] = campaign_csv
            data['num_completed'] = num_completed
            data['campaign_link'] = campaign_link
            download_execution_time = time.time() - download_start_time

            if campaign_csv:
                upload_campaign_data_to_webhook.delay(data) # Upload to webhook

        cache.set(
            f"{backend_id}_campaign_json_{campaign_id}",
            data,
            CAMPAING_JSON_CACHE_TIMEOUT
        )

    execution_time = time.time() - start_time
    result = {
        'backend_id': backend_id,
        'execution_time': execution_time,
        'download_execution_time': download_execution_time,
        'upload_execution_time': upload_execution_time,
        'campaign_host': campaign_host,
        'data': data,
    }
    return result


@shared_task(time_limit=300)
def update_inactive_campaigns(data):
    """Update inactive campaigns and process them to be uploaded"""
    BACKEND_CACHE_TIMEOUT = 360
    start_time = time.time()
    json_data = []
    base64_auth = data.get("auth")

    auth = pbx_auth_decode(data.get("auth"))
    backend_id = auth.get('backend_id')
    client_id = auth.get('clientid')
    client_secret = auth.get('clientsecret')
    client_secret_md5 = hashlib.md5(client_secret.encode()).hexdigest()

    if not cache.get(f'backend_manager_config_{backend_id}'):
        try:
            backend_manager_config = BackendServerManagerConfig.objects.get(
                id=backend_id
            )
        except BackendServerManagerConfig.DoesNotExist:
            backend_manager_config = None
            return "Backend not found"

        cache.set(f"backend_manager_config_{backend_id}",
            backend_manager_config,
           BACKEND_CACHE_TIMEOUT
        )
    backend_manager_config = cache.get(f'backend_manager_config_{backend_id}')
    if backend_manager_config.mysql_host:
        database_host = backend_manager_config.mysql_host
    else:
        database_host = backend_manager_config.host
    username = backend_manager_config.mysql_user
    password = backend_manager_config.mysql_password
    host = backend_manager_config.host
    webhook_url = backend_manager_config.webhook_url if backend_manager_config.webhook_url else None
    api_key = pbx_auth_encode(
        backend_manager_config.id,
        backend_manager_config.pbxapi_user,
        backend_manager_config.pbxapi_password
    )

    try:
        mydb = mysql.connector.connect(
            host=database_host,
            user=username,
            password=password,
            database="call_center"
        )
    except Error as e:
        return(f"Error while connecting to MySQL {e}")

    mycursor = mydb.cursor()

    datetime_end = timezone.localtime().strftime('%Y-%m-%d')
    daytime_end = timezone.localtime().strftime('%H:%M:%S')

    inactive_campaigns_sql = f'SELECT * FROM `campaign` WHERE datetime_end="{datetime_end}" AND daytime_end<"{daytime_end}" AND estatus = "A" OR estatus = "Z"'

    mycursor.execute(
        inactive_campaigns_sql
    )
    # this will extract row headers
    row_headers = [x[0] for x in mycursor.description]
    myresult = mycursor.fetchall()
    current_site = Site.objects.get_current()
    status_choices = {
        'A': 'Active',
        'I': 'Inactive',
        'T': 'Finish',
        'Z': 'Upload',
        'NA': 'NA',
    }

    for result in myresult:
        json_result = dict(zip(row_headers, result))
        json_result['auth'] = base64_auth
        campaign_name = json_result.get('name')
        result_campaign_id = json_result.get('id')
        campaign_key_bytes = base64.b64encode(f"{backend_id}:{result_campaign_id}".encode('ascii'))
        campaign_key_string = campaign_key_bytes.decode("ascii")
        campaign_start_time = json_result.get('daytime_init')
        campaign_end_time = json_result.get('daytime_end')
        estatus = json_result.get('estatus')

        json_result['average_talk_time'] = json_result.pop('promedio')
        json_result['deviation'] = json_result.pop('desviacion')
        json_result['max_channels'] = json_result.pop('max_canales')
        json_result['num_completed'] = json_result.pop('num_completadas')
        link = f"https://{current_site.domain}/helpline/campaign/{campaign_key_string}"

        json_result['key'] = campaign_key_string
        json_result['daytime_init'] = str(campaign_start_time)
        json_result['daytime_end'] = str(campaign_end_time)

        json_result['status'] = status_choices.get(estatus)

        json_result['link'] = link
        json_data.append(json_result)
        mycursor.execute(
            f'UPDATE campaign SET estatus = "I" WHERE id = {result_campaign_id} AND estatus = "A" OR estatus ="Z"'
        )
        process_campaign_webhook_data.delay(json_result)

    mydb.commit()
    updated_rows = (mycursor.rowcount, "record(s) affected")
    execution_time = (time.time() - start_time)
    return f"{updated_rows} in {execution_time} {backend_id} {inactive_campaigns_sql}"


@shared_task(time_limit=300)
def update_finished_campaigns(data):
    """Update finished campaigns and process them to be uploaded"""
    BACKEND_CACHE_TIMEOUT = 10
    start_time = time.time()
    json_data = []
    base64_auth = data.get("auth")

    auth = pbx_auth_decode(data.get("auth"))
    backend_id = auth.get('backend_id')
    client_id = auth.get('clientid')
    client_secret = auth.get('clientsecret')
    client_secret_md5 = hashlib.md5(client_secret.encode()).hexdigest()

    if not cache.get(f'backend_manager_config_{backend_id}'):
        try:
            backend_manager_config = BackendServerManagerConfig.objects.get(
                id=backend_id
            )
        except BackendServerManagerConfig.DoesNotExist:
            backend_manager_config = None
            return "Backend not found"

        cache.set(f"backend_manager_config_{backend_id}",
            backend_manager_config,
           BACKEND_CACHE_TIMEOUT
        )
    backend_manager_config = cache.get(f'backend_manager_config_{backend_id}')
    if backend_manager_config.mysql_host:
        database_host = backend_manager_config.mysql_host
    else:
        database_host = backend_manager_config.host
    username = backend_manager_config.mysql_user
    password = backend_manager_config.mysql_password
    host = backend_manager_config.host
    webhook_url = backend_manager_config.webhook_url if backend_manager_config.webhook_url else None
    api_key = pbx_auth_encode(
        backend_manager_config.id,
        backend_manager_config.pbxapi_user,
        backend_manager_config.pbxapi_password
    )

    try:
        mydb = mysql.connector.connect(
            host=database_host,
            user=username,
            password=password,
            database="call_center"
        )
    except Error as e:
        return(f"Error while connecting to MySQL {e}")

    mycursor = mydb.cursor()

    datetime_end = timezone.localtime().strftime('%Y-%m-%d')
    daytime_end = timezone.localtime().strftime('%H:%M:%S')

    inactive_campaigns_sql = f'SELECT * FROM `campaign` WHERE datetime_end="{datetime_end}" AND estatus = "T"'

    mycursor.execute(
        inactive_campaigns_sql
    )
    # this will extract row headers
    row_headers = [x[0] for x in mycursor.description]
    myresult = mycursor.fetchall()
    current_site = Site.objects.get_current()
    status_choices = {
        'A': 'Active',
        'I': 'Inactive',
        'T': 'Finish',
        'NA': 'NA',
    }

    for result in myresult:
        json_result = dict(zip(row_headers, result))
        json_result['auth'] = base64_auth
        campaign_name = json_result.get('name')
        result_campaign_id = json_result.get('id')
        campaign_key_bytes = base64.b64encode(f"{backend_id}:{result_campaign_id}".encode('ascii'))
        campaign_key_string = campaign_key_bytes.decode("ascii")
        campaign_start_time = json_result.get('daytime_init')
        campaign_end_time = json_result.get('daytime_end')
        estatus = json_result.get('estatus')

        json_result['average_talk_time'] = json_result.pop('promedio')
        json_result['deviation'] = json_result.pop('desviacion')
        json_result['max_channels'] = json_result.pop('max_canales')
        json_result['num_completed'] = json_result.pop('num_completadas')
        link = f"https://{current_site.domain}/helpline/campaign/{campaign_key_string}"

        json_result['key'] = campaign_key_string
        json_result['daytime_init'] = str(campaign_start_time)
        json_result['daytime_end'] = str(campaign_end_time)

        json_result['status'] = status_choices.get(estatus)

        json_result['link'] = link
        json_data.append(json_result)
        mycursor.execute(
            f'UPDATE campaign SET estatus = "I" WHERE id = {result_campaign_id} AND estatus = "T"'
        )
        process_campaign_webhook_data.delay(json_result)

    mydb.commit()
    updated_rows = (mycursor.rowcount, "record(s) affected")
    execution_time = (time.time() - start_time)

    mycursor.close()
    mydb.close()

    return f"{updated_rows} in {execution_time} {current_site.domain} {inactive_campaigns_sql}"


@shared_task(time_limit=300)
def campaign_summary(data, interval='daily'):
    """Get summary of autodial campagins"""
    BACKEND_CACHE_TIMEOUT = 10
    start_time = time.time()
    json_data = []
    base64_auth = data.get("auth")

    auth = pbx_auth_decode(data.get("auth"))
    backend_id = auth.get('backend_id')
    client_id = auth.get('clientid')
    client_secret = auth.get('clientsecret')
    client_secret_md5 = hashlib.md5(client_secret.encode()).hexdigest()

    if not cache.get(f'backend_manager_config_{backend_id}'):
        try:
            backend_manager_config = BackendServerManagerConfig.objects.get(
                id=backend_id
            )
        except BackendServerManagerConfig.DoesNotExist:
            backend_manager_config = None
            return "Backend not found"

        cache.set(
            f"backend_manager_config_{backend_id}",
            backend_manager_config,
            BACKEND_CACHE_TIMEOUT
        )
    backend_manager_config = cache.get(f'backend_manager_config_{backend_id}')
    database_host = backend_manager_config.database_host
    username = backend_manager_config.mysql_user
    password = backend_manager_config.mysql_password
    host = backend_manager_config.host
    api_key = pbx_auth_encode(
        backend_manager_config.id,
        backend_manager_config.pbxapi_user,
        backend_manager_config.pbxapi_password
    )

    try:
        mydb = mysql.connector.connect(
            host=database_host,
            user=username,
            password=password,
            database="call_center"
        )
    except Error as e:
        return f"Error while connecting to MySQL {e}"

    mycursor = mydb.cursor()

    datetime_end = timezone.now().strftime('%Y-%m-%d')
    daytime_end = timezone.now().strftime('%H:%M:%S')

    mycursor.execute(
        f'SELECT * FROM `campaign` WHERE datetime_end="{datetime_end}"'
    )
    # this will extract row headers
    row_headers = [x[0] for x in mycursor.description]
    myresult = mycursor.fetchall()
    current_site = Site.objects.get_current()
    status_choices = {
        'A': 'Active',
        'I': 'Inactive',
        'T': 'Finish',
        'NA': 'NA',
    }

    for result in myresult:
        json_result = dict(zip(row_headers, result))
        json_result['auth'] = base64_auth
        campaign_name = json_result.get('name')
        result_campaign_id = json_result.get('id')
        campaign_key_bytes = base64.b64encode(f"{backend_id}:{result_campaign_id}".encode('ascii'))
        campaign_key_string = campaign_key_bytes.decode("ascii")
        campaign_start_time = json_result.get('daytime_init')
        campaign_end_time = json_result.get('daytime_end')
        estatus = json_result.get('estatus')

        json_result['average_talk_time'] = json_result.pop('promedio')
        json_result['deviation'] = json_result.pop('desviacion')
        json_result['max_channels'] = json_result.pop('max_canales')
        json_result['num_completed'] = json_result.pop('num_completadas')
        link = f"https://{current_site.domain}/helpline/campaign/{campaign_key_string}"

        json_result['key'] = campaign_key_string
        json_result['daytime_init'] = str(campaign_start_time)
        json_result['daytime_end'] = str(campaign_end_time)

        json_result['status'] = status_choices.get(estatus)

        json_result['link'] = link
        json_data.append(json_result)
        mycursor.execute(
            f'UPDATE campaign SET estatus = "I" WHERE id = {result_campaign_id} AND estatus = "A"'
        )
        process_campaign_webhook_data.delay(json_result)

    mydb.commit()
    mycursor.close()
    mydb.close()
    updated_rows = (mycursor.rowcount, "record(s) affected")
    execution_time = (time.time() - start_time)
    return f"{updated_rows} in {execution_time}"


@shared_task(time_limit=300)
def backend_need_reload(backend_id, need_reload='true'):
    """Get summary of autodial campagins"""
    BACKEND_CACHE_TIMEOUT = 10
    start_time = time.time()

    if not cache.get(f'backend_manager_config_{backend_id}'):
        try:
            backend_manager_config = BackendServerManagerConfig.objects.get(
                id=backend_id
            )
        except BackendServerManagerConfig.DoesNotExist:
            backend_manager_config = None
            return "Backend not found"

        cache.set(
            f"backend_manager_config_{backend_id}",
            backend_manager_config,
            BACKEND_CACHE_TIMEOUT
        )
    backend_manager_config = cache.get(f'backend_manager_config_{backend_id}')
    database_host = backend_manager_config.mysql_host
    username = backend_manager_config.mysql_user
    password = backend_manager_config.mysql_password

    try:
        mydb = mysql.connector.connect(
            host=database_host,
            user=username,
            password=password,
            database="asterisk"
        )
    except Error as e:
        return f"Error while connecting to MySQL {e}"

    mycursor = mydb.cursor()

    mycursor.execute(
        f"UPDATE admin SET value = '{need_reload}' WHERE variable = 'need_reload'"
    )

    mydb.commit()
    mycursor.close()
    mydb.close()
    execution_time = (time.time() - start_time)
    return f"Marked backend as need reload {execution_time}"


@shared_task(time_limit=300)
def backend_do_reload(backend_id, need_reload='false'):
    """Get summary of autodial campagins"""
    BACKEND_CACHE_TIMEOUT = 10
    start_time = time.time()

    if not cache.get(f'backend_manager_config_{backend_id}'):
        try:
            backend_manager_config = BackendServerManagerConfig.objects.get(
                id=backend_id
            )
        except BackendServerManagerConfig.DoesNotExist:
            backend_manager_config = None
            return "Backend not found"

        cache.set(
            f"backend_manager_config_{backend_id}",
            backend_manager_config,
            BACKEND_CACHE_TIMEOUT
        )
    backend_manager_config = cache.get(f'backend_manager_config_{backend_id}')
    database_host = backend_manager_config.mysql_host
    username = backend_manager_config.mysql_user
    password = backend_manager_config.mysql_password
    backend = Backend(
        backend_manager_config
    ) if backend_manager_config else Backend()
    res = backend.do_reload()

    try:
        mydb = mysql.connector.connect(
            host=database_host,
            user=username,
            password=password,
            database="asterisk"
        )
    except Error as e:
        return f"Error while connecting to MySQL {e}"

    mycursor = mydb.cursor()

    mycursor.execute(
        f"UPDATE admin SET value = '{need_reload}' WHERE variable = 'need_reload'"
    )

    mydb.commit()
    mycursor.close()
    mydb.close()
    execution_time = (time.time() - start_time)
    return f"Reloaded backend {backend_id} {res} in {execution_time}"


def backend_server_execute_sql(backend_id, sql, database="call_center"):
    """ Connect to backend SQL Servre and return a connection object"""
    pass


def get_recording_file(backend_id, uniqueid):
    sql = f"SELECT * FROM `cdr` WHERE uniqueid='{uniqueid}' AND calldate > '';"
    try:
        backend_manager_config = BackendServerManagerConfig.objects.get(
            id=backend_id
        )
    except BackendServerManagerConfig.DoesNotExist:
        backend_manager_config = None
        return {
            'backend_id': backend_id,
            'message': "Backend not found",
        }

    username = backend_manager_config.mysql_user
    password = backend_manager_config.mysql_password
    host = backend_manager_config.host
    pbxapi_url = backend_manager_config.pbxapi_url
    api_key = pbx_auth_encode(
        backend_manager_config.id,
        backend_manager_config.pbxapi_user,
        backend_manager_config.pbxapi_password
    )

    if backend_manager_config.mysql_host:
        database_host = backend_manager_config.mysql_host
    else:
        database_host = backend_manager_config.host
    webhook_url = backend_manager_config.webhook_url if backend_manager_config.webhook_url else None
    api_key = pbx_auth_encode(
        backend_manager_config.id,
        backend_manager_config.pbxapi_user,
        backend_manager_config.pbxapi_password
    )


    try:
        mydb = mysql.connector.connect(
            host=database_host,
            user=username,
            password=password,
            database="asteriskcdrdb"
        )
    except Error as e:
        return(
            {
                "error": True,
                "message": f"Error while connecting to MySQL {e}",
            }
        )

    mycursor = mydb.cursor()
    start_time = time.time()
    mycursor.execute(
        f"{sql}"
    )
    execution_time = (time.time() - start_time)
    row_headers = [x[0] for x in mycursor.description]
    myresult = mycursor.fetchall()

    json_data = []
    current_site = Site.objects.get_current()
    for result in myresult:
        json_result = dict(zip(row_headers, result))
        recordingfile = json_result.get('recordingfile')
        json_data.append(json_result)
    mycursor.close()
    mydb.close()

    return {
        'host': host,
        'pbxapi_url': pbxapi_url,
        'uniqueid': uniqueid,
        'query_execution_time': execution_time,
        'api_key': api_key,
        'recordingfile': json_data,
        'sql': sql,
    }


@shared_task(time_limit=300)
def backend_get_eccp_credentials(hotdesk):
    """Get summary of autodial campagins"""
    BACKEND_CACHE_TIMEOUT = 5
    ECCP_CREDENTIALS_CACHE_TIMEOUT = 3
    start_time = time.time()
    json_result = {}
    backend_id = hotdesk.backend_manager_config.id

    if not cache.get(f'eccp_credentials_{hotdesk.extension}_{backend_id}'):
        try:
            backend_manager_config = BackendServerManagerConfig.objects.get(
                id=backend_id
            )
        except BackendServerManagerConfig.DoesNotExist:
            backend_manager_config = None
            return "Backend not found"

            cache.set(
                f"backend_manager_config_{backend_id}",
                backend_manager_config,
                BACKEND_CACHE_TIMEOUT
            )
        database_host = backend_manager_config.mysql_host
        username = backend_manager_config.mysql_user
        password = backend_manager_config.mysql_password

        try:
            mydb = mysql.connector.connect(
                host=database_host,
                user=username,
                password=password,
                database="call_center"
            )
        except Error as e:
            return f"Error while connecting to MySQL {e}"

        mycursor = mydb.cursor()
        mycursor.execute(
            f"SELECT * FROM `agent` WHERE number='{hotdesk.extension}'"
        )

        existing_agent = mycursor.fetchone()

        if existing_agent:
            # Agent already exists, return the agent details
            json_result['existing_agent'] = True
        else:
            # Agent doesn't exist, insert a new record
            agent_name = hotdesk.user.get_full_name()
            agent_type = 'SIP'
            agent_number = hotdesk.extension
            agent_password = f'{hotdesk.extension}'
            estatus = 'A'
            eccp_password = '7210e250eb5524c5f7782292efd74c07e5924f0a'

            mycursor.execute(
                f"INSERT INTO agent (type, number, name, password, estatus, eccp_password) VALUES ('{agent_type}', '{agent_number}', '{agent_name}', '{agent_password}', '{estatus}', '{eccp_password}')"
            )
            mydb.commit()
            json_result['existing_agent'] = False


        try:
            # this will extract row headers
            row_headers = [column[0] for column in mycursor.description]
            json_data = []

            json_result = dict(zip(row_headers, existing_agent))
            mycursor.close()
            mydb.close()

        except Exception as e:
            json_result['error'] = str(e)

        json_result['host'] = backend_manager_config.host

        cache.set(
            f"eccp_credentials_{hotdesk.extension}_{backend_id}",
            json_result,
            ECCP_CREDENTIALS_CACHE_TIMEOUT,
        )

    json_result = cache.get(f'eccp_credentials_{hotdesk.extension}_{backend_id}')
    execution_time =  time.time() - start_time,
    json_result['execution_time'] = execution_time
    return json_result



@shared_task(time_limit=300)
def backend_agent_status(eccp_credentials):
    """Login agent to backend ECCP Dialer"""
    ECCP_PORT = 20005
    agenttype = eccp_credentials.get('type')
    agentnumber= eccp_credentials.get('number')
    name = eccp_credentials.get('name')
    password = eccp_credentials.get('password')
    estatus = eccp_credentials.get('estatus')
    eccp_password = eccp_credentials.get('eccp_password')
    host = eccp_credentials.get('host')

    command = f'php {settings.BASE_DIR}/helpline/eccp/agentstatus.php {agenttype}/{agentnumber}'
    result = subprocess.run(
        [
            'php',
            f'{settings.BASE_DIR}/helpline/eccp/agentstatus.php',
            f'{agenttype}/{agentnumber}',
            f'{host}'
        ],
        universal_newlines = True,
        check=True,
        stdout = subprocess.PIPE,
    )
    return {
        'agent_status': result.stdout.splitlines(),
        'script': f'{settings.BASE_DIR}/helpline/eccp/agentstatus.php {agenttype}/{agentnumber} {host}'
    }



def stream_process_output(command, queue_name):
    # Establish a connection to RabbitMQ
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()

    # Declare the queue
    channel.queue_declare(queue=queue_name, durable=True, auto_delete=False)

    # Run the subprocess and stream the output
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    print (process.pid)

    # Stream the output line by line
    for line in iter(process.stdout.readline, ''):
        # Publish each line to the queue
        print(line)
        channel.basic_publish(exchange='', routing_key=queue_name, body=line.rstrip())

    # Wait for the process to finish
    process.wait()

    # Close the RabbitMQ connection
    connection.close()


@shared_task(time_limit=8)
def backend_agent_login(eccp_credentials):
    """Login agent to backend ECCP Dialer"""
    agentnumber = eccp_credentials.get('number')
    eccp_password = eccp_credentials.get('eccp_password')
    eccp_host = eccp_credentials.get('host')

    eccp = ECCP()
    eccp_connected = eccp.connect(
        eccp_host,
        'helplineagentconsole',
        '1dbf9d769b977302900637695761d397')
    if eccp_connected:
        eccp.setAgentNumber(f'SIP/{agentnumber}')
        eccp.setAgentPass(eccp_password)

        login_status = eccp.loginagent(agentnumber, eccp_password)
    else:
        return False
    return login_status
