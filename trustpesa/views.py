# -*- coding: utf-8 -*-
"""IMAB API interaction app views """
import base64
import json
import time

from django.core.cache import cache
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.http import JsonResponse, Http404
from django.utils.translation import gettext as _
from django.shortcuts import render, redirect
import requests
import phonenumbers
from phonenumbers import carrier

from helpline.models import Contact, Address

from requests.exceptions import ConnectionError

from jsonview.decorators import json_view

from helpline.models import Report


def oauth_generate_access_token(clientid, clientsecret, scope):
    """Generate oAuth Key for IMAB API
    oAuth Key is Base64 encoded version of clientid:clientsecret"""
    ENDPOINT_URL = "https://api.imab.co.ke/api/oauth/generate"

    auth_basic = "%s:%s" % (clientid, clientsecret)
    auth_basic_bytes = auth_basic.encode("ascii")

    auth_base64_bytes = base64.b64encode(auth_basic_bytes)
    auth_base64_string = auth_base64_bytes.decode("ascii")

    headers = {
        "Authorization": "Basic " + auth_base64_string,
        "Content-Type": "application/json",
        "User-Agent": "callcenter.africa",
        "Accept": "*/*",
        "Cache-Control": "no-cache",
        "Accept-Encoding": "gzip, deflate, br",
    }

    data = {
        "grant_type": "client_credentials",
        "scope": scope,
    }
    response = requests.post(
        ENDPOINT_URL,
        data=json.dumps(data),
        headers=headers
    )

    return {
        "status": response.status_code,
        "data": json.loads(response.text),
    }


def get_customer_accountdetails(access_token, mobileno=None, idno=None):
    """Get customer account details from API
    Use E.164 International phone number formatting
    """

    ENDPOINT_URL = "https://api.imab.co.ke/api/customer/accountdetails"

    headers = {
        "Authorization": "Bearer " + access_token,
        "Content-Type": "application/json",
        "User-Agent": "callcenter.africa",
        "Accept": "*/*",
        "Cache-Control": "no-cache",
        "Accept-Encoding": "gzip, deflate, br",
    }

    data = {
        "mobileno": mobileno,
        "idno": idno,
    }
    response = requests.post(
        ENDPOINT_URL,
        data=json.dumps(data),
        headers=headers
    )

    return {
        "status": response.status_code,
        "data": json.loads(response.text),
    }


def get_customer_accountstatement(access_token, mobileno=None, accountid=None):
    """Get customer account details from API
    Use E.164 International phone number formatting
    """

    ENDPOINT_URL = "https://api.imab.co.ke/api/customer/accountstatement"

    headers = {
        "Authorization": "Bearer " + access_token,
        "Content-Type": "application/json",
        "User-Agent": "callcenter.africa",
        "Accept": "*/*",
        "Cache-Control": "no-cache",
        "Accept-Encoding": "gzip, deflate, br",
    }

    data = {
        "mobileno": "254722965774",
        "accountid": 2,
    }
    response = requests.post(
        ENDPOINT_URL,
        data=json.dumps(data),
        headers=headers
    )

    return {
        "status": response.status_code,
        "data": json.loads(response.text),
    }


@json_view
def customer_accountdetails(request):
    scope = 'bidiicredit'
    """ Get customer account details from phone number"""
    ACCESS_TOKEN_CACHE_TIMEOUT = 300
    start_time = time.time()
    if request.method == 'GET' or request.method == 'POST':
        case_number = request.GET.get('caseid')
        uniqueid = request.GET.get('uniqueid')
        if case_number:
            try:
                case_number = int(case_number)
            except ValueError:
                raise Http404(_("Case not found"))
            # Get a report object from the case number
            # Report object is then cached
            report = cache.get_or_set(
                "report_%s" % (case_number),
                get_object_or_404(Report, case_id=case_number),
                ACCESS_TOKEN_CACHE_TIMEOUT
            )
            # Check if Unique id in Report is the same as GET uniqueid
            # This is an extra layer of security case data
            if report.hl_unique != uniqueid:
                raise Http404(_("Case not found"))

            # Parse phone number from report object to phonenumbers object
            customer_number = phonenumbers.parse(report.telephone, "KE")
            international_f = phonenumbers.format_number(
                customer_number,
                phonenumbers.PhoneNumberFormat.INTERNATIONAL
            )
            e164_f = phonenumbers.format_number(
                customer_number,
                phonenumbers.PhoneNumberFormat.E164
            )

            mobileno = e164_f[1:]
            clientid = settings.IMAB_CLIENTID
            clientsecret = settings.IMAB_CLIENTSECRET

            # Fetch Auth Key from IMAB API or Cache
            auth_key = cache.get_or_set("imab_%s" % (scope),
                                        oauth_generate_access_token(
                                            clientid, clientsecret, scope
                                        ),
                                        ACCESS_TOKEN_CACHE_TIMEOUT)
            access_token = auth_key.get("data").get("access_token")
            # Use access token to fetch customer details from IMAB API
            customer_details = cache.get_or_set(
                "imab_%s_%s" % (scope, mobileno),
                get_customer_accountdetails(access_token, mobileno=mobileno),
                ACCESS_TOKEN_CACHE_TIMEOUT
            )
            # Measure execution time
            execution_time = (time.time() - start_time)

            return {
                "case": report.case.pk,
                "report": report.telephone,
                "international": international_f,
                "e164": e164_f,
                "mobileno": mobileno,
                "carrier": carrier.name_for_number(customer_number, "en"),
                "auth_key": auth_key,
                "customer_details": customer_details,
                "execution_time": execution_time
            }


def phone_verification(request):
    """ Phone verification prototype"""
    data = {}
    phone = request.GET.get('phone')
    if phone:
        # Parse phone number from report object to phonenumbers object
        try:
            customer_number = phonenumbers.parse(phone, "KE")
            international_f = phonenumbers.format_number(
                customer_number,
                phonenumbers.PhoneNumberFormat.INTERNATIONAL
            )
            e164_f = phonenumbers.format_number(
                customer_number,
                phonenumbers.PhoneNumberFormat.E164
            )
            mobileno = e164_f[1:]
            data['customer_number'] = customer_number
            data['international_f'] = international_f
            data['e164_f'] = e164_f
            data['mobileno'] = mobileno
            data['phone'] = phone
            contact = Contact.objects.filter(hl_contact=mobileno[3:])
            data['contact'] = contact
        except:
            data['phone'] = phone

    return render(
        request,
        'trustpesa/home.html',
        data
    )

@json_view
def customer_accountstatement(request):
    scope = 'bidiicredit'
    """Query customer account statement and return latest 5 transactions"""
    ACCESS_TOKEN_CACHE_TIMEOUT = 300
    start_time = time.time()
    if request.method == 'GET' or request.method == 'POST':
        case_number = request.GET.get('caseid')
        uniqueid = request.GET.get('uniqueid')
        if case_number:
            try:
                case_number = int(case_number)
            except ValueError:
                raise Http404(_("Case not found"))
            # Get a report object from the case number
            # Report object is then cached
            report = cache.get_or_set(
                "report_%s" % (case_number),
                get_object_or_404(Report, case_id=case_number),
                ACCESS_TOKEN_CACHE_TIMEOUT
            )
            # Check if Unique id in Report is the same as GET uniqueid
            # This is an extra layer of security case data
            if report.hl_unique != uniqueid:
                raise Http404(_("Case not found"))

            # Parse phone number from report object to phonenumbers object
            customer_number = phonenumbers.parse(report.telephone, "KE")
            international_f = phonenumbers.format_number(
                customer_number,
                phonenumbers.PhoneNumberFormat.INTERNATIONAL
            )
            e164_f = phonenumbers.format_number(
                customer_number,
                phonenumbers.PhoneNumberFormat.E164
            )

            mobileno = e164_f[1:]
            clientid = settings.IMAB_CLIENTID
            clientsecret = settings.IMAB_CLIENTSECRET

            # Fetch Auth Key from IMAB API or Cache
            auth_key = cache.get_or_set("imab_%s" % (scope),
                                        oauth_generate_access_token(
                                            clientid, clientsecret, scope
                                        ),
                                        ACCESS_TOKEN_CACHE_TIMEOUT)
            access_token = auth_key.get("data").get("access_token")
            # Use access token to fetch customer details from IMAB API
            customer_statement = cache.get_or_set(
                "imab_accountstatement_%s_%s" % (scope, mobileno),
                get_customer_accountstatement(access_token, mobileno=mobileno),
                ACCESS_TOKEN_CACHE_TIMEOUT
            )
            # Measure execution time
            execution_time = (time.time() - start_time)

            return {
                "case": report.case.pk,
                "report": report.telephone,
                "international": international_f,
                "e164": e164_f,
                "mobileno": mobileno,
                "carrier": carrier.name_for_number(customer_number, "en"),
                "auth_key": auth_key,
                "customer_statement": customer_statement,
                "execution_time": execution_time
            }
