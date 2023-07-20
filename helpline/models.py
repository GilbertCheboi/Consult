# -*- coding: utf-8 -*-
"""Helpline Models"""

from __future__ import unicode_literals
import calendar
from datetime import timedelta, datetime, date, time as datetime_time
import time
import os
import re

from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver

from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.contrib.postgres.fields import ArrayField

from django.core.cache import cache
from django.core import validators
from django.forms.fields import URLField as FormURLField

from django.db.models import Avg
from django.utils import timezone
from django.apps import apps
from django.utils.translation import ugettext_lazy as _

from tinymce.models import HTMLField

from phonenumber_field.modelfields import PhoneNumberField

from helpline.utils import unique_slug_generator





class Address(models.Model):
    """Gives details about parties in a report"""
    hl_title = models.CharField(max_length=25, blank=True, null=True)
    hl_type = models.CharField(max_length=9, blank=True, null=True)
    hl_names = models.CharField(max_length=500, blank=True, null=True)
    hl_gender = models.CharField(max_length=7, blank=True, null=True)
    hl_ageclass = models.CharField(max_length=7, blank=True, null=True)
    hl_age = models.IntegerField(blank=True, null=True)
    hl_dob = models.DateField(blank=True, null=True)
    hl_yeardob = models.TextField(blank=True, null=True)
    hl_monthdob = models.SmallIntegerField(blank=True, null=True)
    hl_datedob = models.SmallIntegerField(blank=True, null=True)
    hl_language = models.CharField(max_length=250, blank=True, null=True)
    hl_relation = models.CharField(max_length=100, blank=True, null=True)
    hl_address1 = models.CharField(max_length=250, blank=True, null=True)
    hl_address2 = models.CharField(max_length=250, blank=True, null=True)
    hl_address3 = models.CharField(max_length=100, blank=True, null=True)
    hl_address4 = models.CharField(max_length=100, blank=True, null=True)
    hl_country = models.CharField(max_length=250, blank=True, null=True)
    hl_email = models.CharField(max_length=100, blank=True, null=True)
    hl_householdtype = models.CharField(max_length=13)
    hl_childrenumber = models.IntegerField(blank=True, null=True)
    hl_adultnumber = models.IntegerField(blank=True, null=True)
    hl_headoccupation = models.CharField(max_length=100, blank=True, null=True)
    hl_school = models.CharField(max_length=250, blank=True, null=True)
    hl_company = models.CharField(max_length=250, blank=True, null=True)
    hl_schooltype = models.CharField(max_length=100, blank=True, null=True)
    hl_class = models.CharField(max_length=50, blank=True, null=True)
    hl_attendance = models.CharField(max_length=12, blank=True, null=True)
    hl_attendancereason = models.TextField(blank=True, null=True)
    hl_schaddr = models.CharField(max_length=250, blank=True, null=True)
    hl_homerole = models.CharField(max_length=7, blank=True, null=True)
    hl_latitude = models.FloatField(blank=True, null=True)
    hl_longitude = models.FloatField(blank=True, null=True)
    hl_religion = models.CharField(max_length=100, blank=True, null=True)
    hl_career = models.CharField(max_length=13, blank=True, null=True)
    hl_shl_evel = models.CharField(max_length=11, blank=True, null=True)
    hl_health = models.CharField(max_length=12, blank=True, null=True)
    hl_disabled = models.CharField(max_length=3, blank=True, null=True)
    hl_notes = models.TextField(blank=True, null=True)
    hl_created = models.IntegerField(blank=True, null=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        blank=True, null=True
    )
    # Creator will be deleted in favor of user model
    hl_creator = models.IntegerField(blank=True, null=True)
    hl_deletedate = models.IntegerField(blank=True, null=True)
    hl_deleteby = models.IntegerField(blank=True, null=True)
    hl_deleted = models.IntegerField(blank=True, null=True)
    hl_current = models.SmallIntegerField(blank=True, null=True)
    hl_contact = models.IntegerField(blank=True, null=True)
    hl_time = models.IntegerField(blank=True, null=True)

    def __unicode__(self):
        return self.hl_names or u''

    def __str__(self):
        return self.hl_names or u''


class Contact(models.Model):
    """Contact information for an address"""
    first_name = models.CharField(_("First name"), max_length=255,
                                  blank=True, null=True)
    last_name = models.CharField(_("Last name"), max_length=255,
                                 blank=True, null=True)
    address = models.ForeignKey(Address, on_delete=models.CASCADE,
                                blank=True, null=True)
    phone = PhoneNumberField(null=True, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    assigned_to = models.ManyToManyField(
        User, related_name="contact_assigned_users",
        blank=True
    )
    created_by = models.ForeignKey(
        User, related_name="contact_created_by",
        on_delete=models.SET_NULL, null=True,
        blank=True
    )
    created_on = models.DateTimeField(_("Created on"), auto_now_add=True)
    is_active = models.BooleanField(default=False)
    hl_contact = models.CharField(max_length=250)
    hl_parent = models.IntegerField(blank=True, null=True)
    hl_type = models.CharField(max_length=12, blank=True, null=True)
    hl_calls = models.IntegerField(blank=True, null=True)
    hl_status = models.CharField(max_length=10, blank=True, null=True)
    hl_time = models.IntegerField(blank=True, null=True)

    class Meta:
        unique_together = (('address', 'hl_contact'),)

    def __unicode__(self):
        return self.hl_contact

    def __str__(self):
        return self.hl_contact

    def get_name(self):
        return self.address.hl_names


class Case(models.Model):
    """Case management model"""
    hl_case = models.AutoField(primary_key=True)
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        blank=True, null=True
    )
    hl_unique = models.CharField(unique=True, max_length=20,
                                 blank=True, null=True)
    hl_disposition = models.CharField(max_length=250, blank=True, null=True)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True, null=True
    )
    hl_data = models.CharField(max_length=9, blank=True, null=True)
    hl_popup = models.CharField(max_length=6,
                                blank=True, null=True)
    hl_time = models.IntegerField(blank=True, null=True)
    status = models.CharField(max_length=25, blank=True, null=True)
    case_detail = JSONField(default=dict, null=True, blank=True)

    def __unicode__(self):
        return str(self.hl_case)

    def __str__(self):
        return str(self.hl_case)


class CaseTrail(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE)
    hl_status = models.CharField(max_length=8)
    hl_to = models.CharField(max_length=10)
    hl_userkey = models.IntegerField()
    hl_service = models.CharField(max_length=11)
    hl_subcategory = models.CharField(max_length=250)
    hl_servicedesc = models.TextField()
    hl_details = models.TextField()
    hl_editby = models.IntegerField()
    hl_time = models.CharField(max_length=11)


class ClockBit(models.Model):
    hl_key = models.IntegerField()
    hl_clock = models.CharField(max_length=11)
    hl_service = models.IntegerField()
    hl_time = models.IntegerField()


class Country(models.Model):
    hl_category = models.CharField(max_length=100)
    hl_code = models.CharField(max_length=2)
    hl_country = models.CharField(max_length=250)
    hl_phone = models.IntegerField()


class Dialect(models.Model):
    hl_category = models.CharField(max_length=100, blank=True, null=True)
    hl_dialect = models.CharField(max_length=100, verbose_name="Language")
    hl_status = models.IntegerField(blank=True, null=True)

    class Meta:
        verbose_name = 'Language'
        verbose_name_plural = 'Languages'

    def __unicode__(self):
        return self.hl_dialect

    def __str__(self):
        return self.hl_dialect


def webrtc_gateway_url_default():
    """Return the default WebRTC Gateway URL
    This could be a Janus or Sylk Server Instance"""
    # Hard coded default for now
    # TODO: Move this to settings.py
    return "https://webrtc-gateway.callcenter.africa/janus"


class WebRTCURLFormField(FormURLField):
    '''URL Form field that accepts only https and wss'''
    default_validators = [
        validators.URLValidator(
            schemes=['https', 'wss']
        )
    ]


class WebRTCURLField(models.URLField):
    '''URL field that accepts URLs that start with wws:// .'''
    default_validators = [validators.URLValidator(schemes=['https', 'wss'])]

    def formfield(self, **kwargs):
        return super(WebRTCURLField, self).formfield(**{
            'form_class': WebRTCURLFormField,
        })


class SipServerConfig(models.Model):
    """Sip Server configs like SIP domain, Host or IP and port
    Used for connecting SIP clients to a PABX or SIP Proxy"""
    name = models.CharField(max_length=50)
    sip_host = models.CharField(max_length=253)
    sip_domain = models.CharField(max_length=253)
    sip_port = models.CharField(max_length=10)
    webrtc_gateway_url = WebRTCURLField(
        max_length=200,
        default=webrtc_gateway_url_default,
    )

    def __unicode__(self):
        return self.name

    def __str__(self):
        return str(self.name)


class TurnServerConfig(models.Model):
    """TURN Server configs like TURN URI, Host or IP and port"""
    name = models.CharField(max_length=50)
    turn_uri = models.CharField(max_length=253)
    turn_username = models.CharField(max_length=253)
    turn_password = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return str(self.name)


def pbxapi_url_default():
    """Return the default PBX API URL"""
    # Hard Coded to Call Center Africa API
    # TODO: Move this to settings.py
    return "https://api.callcenter.africa/"


def webhook_url_default():
    """Return the default WebHook URL"""
    # Hard Coded to Call Center Africa API
    return "https://api.callcenter.africa/webhook"


class BackendServerManagerConfig(models.Model):
    """Asterisk and Freeswitch manager config model
    e.g Join Queue, Leave Queue and get Queuestats from PBX/Switch
    """
    ASTERISK = 'asterisk'
    FREESWITCH = 'freeswitch'
    SERVER_TYPE_CHOICES = (
        (ASTERISK, 'Asterisk'),
        (FREESWITCH, 'Freeswitch'),
    )
    name = models.CharField(max_length=50)
    username = models.CharField(max_length=50)
    password = models.CharField(max_length=50)
    host = models.CharField(max_length=253)
    port = models.CharField(max_length=10)
    server_type = models.CharField(
        max_length=20,
        choices=SERVER_TYPE_CHOICES,
        default=ASTERISK
    )
    pbxapi_url = models.URLField(
        max_length=200,
        default=pbxapi_url_default
    )
    webhook_url = models.URLField(
        max_length=200,
        default=webhook_url_default
    )
    pbxapi_user = models.CharField(max_length=12, blank=True, null=True)
    pbxapi_password = models.CharField(max_length=50, blank=True, null=True)
    mysql_host = models.CharField(max_length=60, blank=True, null=True)
    mysql_user = models.CharField(max_length=12, blank=True, null=True)
    mysql_password = models.CharField(max_length=50, blank=True, null=True)
    mysql_port = models.IntegerField(
        blank=True,
        null=True,
        default=3306,
    )

    def __unicode__(self):
        return self.name

    def __str__(self):
        return str(self.name)


class Category(models.Model):
    hl_core = models.IntegerField(verbose_name='Core ID', default=1)
    hl_category = models.CharField(max_length=100, verbose_name='Category')
    hl_subcategory = models.CharField(max_length=100,
                                      verbose_name='Subcategory')
    hl_subsubcat = models.CharField(max_length=100,
                                    verbose_name='Sub-subcategory',
                                    blank=True, null=True)
    backend_manager_config = models.ForeignKey(
        BackendServerManagerConfig, on_delete=models.SET_NULL,
        blank=True, null=True,
        help_text=_('Backend Manager Config')
    )

    def get_subcategory(self):
        return Category.objects.filter(hl_category=self.hl_category)

    def get_sub_subcategory(self):
        return Category.objects.filter(hl_category=self.hl_subsubcat)

    def __unicode__(self):
        return self.hl_category

    def __str__(self):
        return self.hl_category


class Hotdesk(models.Model):
    """A hotdesk references the workstation an agent seats."""
    SIP = 'SIP'
    AVAILABLE = 'Available'
    UNAVAILABLE = 'Unavailable'
    EXTENSION_TYPE_CHOICES = (
        (SIP, 'SIP'),
    )
    AVAILABILITY_CHOICES = (
        (AVAILABLE, 'Available'),
        (UNAVAILABLE, 'Unavailable'),
    )
    extension = models.IntegerField(unique=True, primary_key=True)
    extension_type = models.CharField(
        max_length=6,
        choices=EXTENSION_TYPE_CHOICES,
        default=SIP
    )
    status = models.CharField(
        max_length=11,
        choices=AVAILABILITY_CHOICES,
        default=UNAVAILABLE
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True, null=True
    )
    agent = models.IntegerField(
        blank=True, null=True
    )
    secret = models.CharField(
        max_length=255,
        verbose_name="Secret",
        blank=True, null=True
    )
    sip_server = models.ForeignKey(
        SipServerConfig, on_delete=models.SET_NULL,
        blank=True, null=True,
        help_text=_('SIP Server')
    )
    backend_manager_config = models.ForeignKey(
        BackendServerManagerConfig, on_delete=models.SET_NULL,
        blank=True, null=True,
        help_text=_('Backend Manager Config')
    )
    primary = models.BooleanField(
        verbose_name=_("primary"),
        default=False,
    )
    turn_server = models.ForeignKey(
        TurnServerConfig, on_delete=models.SET_NULL,
        blank=True, null=True,
        help_text=_('TURN Server')
    )

    def __unicode__(self):
        return str(self.extension)

    def __str__(self):
        return str(self.extension)

    def update_hotdesk(self, status, extension):
        """Update extension status on hotdesk"""
        self.status = status
        self.extension = extension
        self.save()

    def save(self, *args, **kwargs):
        """Overrite the deafult save function and make saved Hotdesk Primary
        Make all other Hotdesk object secondary"""
        hotdesks = Hotdesk.objects.filter(user=self.user)
        if self.pk:
            hotdesks = hotdesks.exclude(pk=self.pk)
            if self.primary:
                hotdesks = hotdesks.filter(primary=True)
                hotdesks.update(primary=False)
                cache.delete(f"user_hotdesk_{self.user}")
        super(Hotdesk, self).save(*args, **kwargs)


class IMregistry(models.Model):
    hl_index = models.AutoField(primary_key=True)
    hl_chat = models.CharField(max_length=300)
    hl_mandatory = models.CharField(max_length=300)
    hl_path = models.CharField(max_length=300)
    hl_type = models.IntegerField()
    hl_table = models.CharField(max_length=100)


class MainCDR(models.Model):
    hl_unique = models.CharField(unique=True, max_length=32)
    hl_start = models.BigIntegerField()
    hl_end = models.IntegerField()
    hl_duration = models.IntegerField()
    hl_queue = models.CharField(max_length=100, blank=True, null=True)
    hl_agent = models.IntegerField()
    hl_bridge = models.CharField(max_length=100)
    hl_holdtime = models.IntegerField()
    hl_talktime = models.IntegerField()
    hl_vmail = models.CharField(max_length=7)
    hl_app = models.CharField(max_length=9)
    hl_status = models.CharField(max_length=11)
    hl_time = models.IntegerField()


class MatrixQA(models.Model):
    hl_type = models.CharField(max_length=5)
    hl_item = models.CharField(max_length=250)
    hl_data = models.TextField()
    hl_cycle = models.IntegerField()
    hl_menu = models.IntegerField()
    hl_score1 = models.CharField(max_length=100)
    hl_score2 = models.CharField(max_length=100)
    hl_score3 = models.CharField(max_length=100)
    hl_score4 = models.CharField(max_length=100)
    hl_mark1 = models.IntegerField()
    hl_mark2 = models.IntegerField()
    hl_mark3 = models.IntegerField()
    hl_mark4 = models.IntegerField()


class MenuLog(models.Model):
    hl_user = models.IntegerField()
    hl_key = models.IntegerField()
    hl_status = models.IntegerField()
    hl_menu = models.CharField(max_length=100)
    hl_path = models.CharField(max_length=100)
    hl_query = models.TextField()
    hl_data = models.TextField()
    hl_time = models.IntegerField()



class Offered(models.Model):
    hl_case = models.IntegerField(unique=True)
    hl_service = models.CharField(max_length=250)
    hl_projectname = models.CharField(max_length=6)
    hl_subcategory = models.CharField(max_length=250)
    hl_victimdev = models.CharField(max_length=13)
    hl_servicespects = models.CharField(max_length=50)
    hl_saction = models.IntegerField()
    hl_expenses = models.IntegerField()
    hl_expensesto = models.CharField(max_length=100)
    hl_remarks = models.TextField()
    hl_assesscomment = models.TextField()
    hl_time = models.IntegerField()


class Partner(models.Model):
    """Partnering Organizations"""
    code = models.CharField(max_length=10, blank=True, null=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    keyservices = models.CharField(max_length=100, blank=True, null=True)
    referralpartner = models.CharField(max_length=100, blank=True, null=True)
    region = models.CharField(max_length=100, blank=True, null=True)
    town = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    addresslocation = models.CharField(max_length=100, blank=True, null=True)
    contactperson = models.CharField(max_length=100, blank=True, null=True)
    contactpersontitle = models.CharField(max_length=100, blank=True, null=True)
    contactpersonemail = models.CharField(max_length=100, blank=True, null=True)
    contact_personphone = models.CharField(max_length=100, blank=True, null=True)
    contact_personofficephone = models.CharField(max_length=100, blank=True, null=True)
    contactpersonofficeemail = models.CharField(max_length=100, blank=True, null=True)
    contactpersonofficefax = models.CharField(max_length=100, blank=True, null=True)
    website = models.CharField(max_length=100, blank=True, null=True)
    pobox = models.CharField(max_length=100, blank=True, null=True)
    openinghours = models.CharField(max_length=100, blank=True, null=True)
    referralneeded = models.CharField(max_length=100, blank=True, null=True)
    referralpoint = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True, verbose_name='Notes')
    affiliations = models.TextField(blank=True, null=True)


class Postcode(models.Model):
    keyid = models.IntegerField(unique=True,primary_key=True)
    address2 = models.CharField(max_length=100)
    address3 = models.CharField(max_length=100)
    addresstype = models.CharField(max_length=100)

    def __unicode__(self):
        return self.address2

    def __str__(self):
        return self.address2

class QALog(models.Model):
    hl_case = models.ForeignKey(Case, on_delete=models.CASCADE)
    hl_key = models.IntegerField()
    hl_case = models.IntegerField()
    hl_supervisor = models.IntegerField()
    hl_counsellor = models.IntegerField()
    hl_total = models.IntegerField()
    hl_grq1 = models.IntegerField()
    hl_lsq1 = models.IntegerField()
    hl_lsq2 = models.IntegerField()
    hl_akq1 = models.IntegerField()
    hl_akq2 = models.IntegerField()
    hl_akq3 = models.IntegerField()
    hl_akq4 = models.IntegerField()
    hl_akq5 = models.IntegerField()
    hl_paq1 = models.IntegerField()
    hl_paq2 = models.IntegerField()
    hl_paq3 = models.IntegerField()
    hl_req1 = models.IntegerField()
    hl_req2 = models.IntegerField()
    hl_req3 = models.IntegerField()
    hl_req4 = models.IntegerField()
    hl_req5 = models.IntegerField()
    hl_req6 = models.IntegerField()
    hl_req7 = models.IntegerField()
    hl_req8 = models.IntegerField()
    hl_req9 = models.IntegerField()
    hl_req10 = models.IntegerField()
    hl_hpq1 = models.IntegerField()
    hl_hpq2 = models.IntegerField()
    hl_usq1 = models.IntegerField()
    hl_csq1 = models.IntegerField()
    hl_csq2 = models.IntegerField()
    hl_feedback = models.TextField()
    hl_time = models.IntegerField()
    hl_what = models.CharField(max_length=6, blank=True, null=True)


class Recorder(models.Model):
    hl_case = models.ForeignKey(Case, on_delete=models.CASCADE)
    hl_key = models.IntegerField(blank=True, null=True)
    hl_type = models.CharField(max_length=9, blank=True, null=True)
    hl_service = models.IntegerField(blank=True, null=True)
    hl_unique = models.CharField(max_length=25, blank=True, null=True)
    hl_status = models.CharField(max_length=7, blank=True, null=True)
    hl_staff = models.IntegerField(blank=True, null=True)
    hl_time = models.IntegerField(blank=True, null=True)


class Registry(models.Model):
    hl_key = models.IntegerField(unique=True)
    hl_names = models.CharField(max_length=255)
    hl_age = models.CharField(max_length=7)
    hl_gender = models.CharField(max_length=7)
    hl_relation = models.CharField(max_length=100)
    hl_address = models.CharField(max_length=500)
    hl_orient = models.CharField(max_length=8)
    hl_cases = models.IntegerField()
    hl_data = models.TextField()
    hl_status = models.CharField(max_length=7)
    hl_healthstatus = models.CharField(max_length=100)
    hl_proffession = models.CharField(max_length=200)
    hl_maritalstatus = models.CharField(max_length=8)
    hl_householdshared = models.CharField(max_length=3)
    hl_time = models.IntegerField()
    hl_hivrelated = models.IntegerField()


class Disposition(models.Model):
    """The final known disposition of a case"""
    value = models.CharField(max_length=50)
    description = models.CharField(max_length=100, blank=True, null=True)

    def __unicode__(self):
        return str(self.value)


class ServiceExternalURL(models.Model):
    """External URL with templates for services"""
    WINDOW = 'window'
    IFRAME = 'iframe'
    OPENTYPE_CHOICES = (
        (WINDOW, _('New window')),
        (IFRAME, _('Embedded frame')),
    )
    urltemplate = models.CharField(max_length=255)
    description = models.CharField(max_length=64)
    status = models.BooleanField(
        default=True, blank=True, null=True,
        verbose_name=_("Enabled")
    )
    opentype = models.CharField(
        max_length=8,
        choices=OPENTYPE_CHOICES,
        default=WINDOW
    )

    def __unicode__(self):
        return self.urltemplate

    def __str__(self):
        return str(self.urltemplate)


class Service(models.Model):
    """Identifies a queue that agents can be assigned"""
    extension = models.CharField(
        max_length=100,
        help_text=_('Extension callers will dial e.g 116.'),
    )
    name = models.CharField(
        max_length=255,
        help_text=_('Service name')
    )
    queue = models.CharField(
        max_length=255,
        blank=True, null=True,
        help_text=_('Corresponding Asterisk Queue name')
    )
    sip_server = models.ForeignKey(
        SipServerConfig, on_delete=models.SET_NULL,
        blank=True, null=True,
        help_text=_('SIP Server')
    )
    backend_manager_config = models.ForeignKey(
        BackendServerManagerConfig, on_delete=models.SET_NULL,
        blank=True, null=True,
        help_text=_('Backend Server')
    )
    status = models.BooleanField(default=True, blank=True, null=True)
    external_url = models.ForeignKey(
        ServiceExternalURL, on_delete=models.SET_NULL,
        blank=True, null=True,
        help_text=_('External URL')
    )
    script = HTMLField(blank=True, null=True)
    disposition_choices = ArrayField(
        models.CharField(max_length=50, blank=True),
        null=True,
        blank=True
    )
    slug = models.SlugField(
        _('Slug'),
        max_length=50,
        unique=True,
        null=True,
        blank=True
    )
    managed = models.BooleanField(default=False, blank=True, null=True)


    def __unicode__(self):
        return self.name

    def __str__(self):
        return str(self.name)

    class Meta:
        unique_together = (('extension', 'backend_manager_config'),)

class Break(models.Model):
    """List of breaks"""
    ACTIVE = 'A'
    INACTIVE = 'I'
    STATUS_CHOICES = (
        (ACTIVE, 'Active'),
        (INACTIVE, 'Inactive'),
    )

    name = models.CharField(max_length=50)
    description = models.CharField(max_length=250)
    status = models.CharField(
        max_length=1,
        choices=STATUS_CHOICES,
        default=ACTIVE
    )

    def __unicode__(self):
        return self.name

    def __str__(self):
        return str(self.name)


class IpAddress(models.Model):
    """Store IP Addresses that interact with  the system"""
    pub_date = models.DateTimeField(
        _("Date Published"),
        auto_now_add=True,
    )
    ip_address = models.GenericIPAddressField()
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True, null=True
    )
    comment = models.CharField(max_length=80, blank=True, null=True)
    banned = models.BooleanField(default=False)
    user_data = models.CharField(max_length=255)

    def __unicode__(self):
        return self.ip_address

    def __str__(self):
        return str(self.ip_address)


class Clock(models.Model):
    """A Clock is an audit trail of agent actions"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        blank=True, null=True
    )
    hl_clock = models.CharField(verbose_name='Action', max_length=50)
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE,
        blank=True, null=True
    )
    hl_time = models.IntegerField(verbose_name='Time')
    break_reason = models.ForeignKey(
        Break,
        blank=True,
        null=True,
        on_delete=models.SET_NULL
    )
    ip_address = models.ForeignKey(
        IpAddress,
        blank=True,
        null=True,
        on_delete=models.SET_NULL
    )
    clock_in = models.DateTimeField(
        _("Clock in"),
        auto_now_add=True,
        blank=True,
        null=True
    )
    clock_out = models.DateTimeField(
        _("Clock out"),
        blank=True,
        null=True
    )
    duration = models.DurationField(
        verbose_name='Duration',
        blank=True,
        null=True
    )

    def __unicode__(self):
        return self.hl_clock

    def __str__(self):
        return self.hl_clock

class Report(models.Model):
    """Main report table."""
    address = models.ForeignKey(
        Address,
        on_delete=models.CASCADE,
        blank=True, null=True
    )
    case = models.OneToOneField(
        Case, on_delete=models.CASCADE,
        related_name='Report',
        blank=True, null=True
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True, null=True
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        blank=True, null=True
    )
    calldate = models.CharField(max_length=250, verbose_name='Call Date',
                                blank=True, null=True)
    queuename = models.TextField(verbose_name='Queue Name',
                                 blank=True, null=True)
    telephone = models.CharField(max_length=20, verbose_name='Telephone',
                                 blank=True, null=True)
    callernames = models.CharField(max_length=250, verbose_name='Caller Names',
                                   blank=True, null=True)
    casearea = models.CharField(max_length=13, verbose_name='Case Area',
                                blank=True, null=True)
    counsellorname = models.TextField(verbose_name='Agent Name',
                                      blank=True, null=True)
    agentchannel = models.CharField(max_length=100,
                                    verbose_name='Agent Channel',
                                    blank=True, null=True)
    callstart = models.TimeField(verbose_name='Call Start',
                                 blank=True, null=True)
    callend = models.TimeField(verbose_name='Call End',
                               blank=True, null=True)
    talktime = models.DurationField(verbose_name='Talk Time',
                                    blank=True, null=True)
    holdtime = models.DurationField(verbose_name='Hold Time',
                                    blank=True, null=True)
    walkintime = models.TimeField(verbose_name='Walkin Time',
                                  blank=True, null=True)
    calltype = models.CharField(max_length=11, verbose_name='Call Type',
                                blank=True, null=True)
    casestatus = models.CharField(max_length=16, verbose_name='Case Status',
                                  blank=True, null=True, default="Close")
    escalatename = models.CharField(max_length=250,
                                    verbose_name='Escalated Name',
                                    blank=True, null=True)
    casetype = models.CharField(max_length=6, verbose_name='Case Type',
                                blank=True, null=True)
    hl_time = models.IntegerField(verbose_name='Time', blank=True, null=True)
    hl_unique = models.CharField(unique=True, max_length=20,
                                 blank=True, null=True,
                                 verbose_name='Unique Call-ID')
    qa = models.CharField(max_length=3, verbose_name='QA',
                          blank=True, null=True)

    def __unicode__(self):
        return str(self.case.hl_case)

    def __str__(self):
        return str(self.case.hl_case if self.case else '-')

    def get_call_type(self):
        """ Get casetype."""
        if self.casetype:
            if self.casetype.lower() == "call":
                return "Inbound"
            elif self.casetype.lower() == "voicemail":
                return "Voicemail"
            else:
                return "Outbound"
        else:
            return "Walkin"

    def get_absolute_url(self):
        """Calculate the canonical URL for Report."""
        # Django 1.10 breaks reverse imports.
        try:
            from django.urls import reverse
        except Exception as e:
            from django.core.urlresolvers import reverse

        return reverse(
            'case_form',
            args=["call"]
        ) + "?case=%s&uniqueid=%s" % (
            str(self.case), str(self.hl_unique)
        )

    def get_qa_url(self):
        """Calculate the canonical URL for Report."""
        # Django 1.10 breaks reverse imports.
        try:
            from django.urls import reverse
        except Exception as e:
            from django.core.urlresolvers import reverse

        return reverse('case_form', args=[self.casetype.lower() if self.qa else "qa"]) + "?case=%s" % str(self.case)

    def get_address(self):
        """ Return the Address model associated with phone number
        Worst piece of code ever. I'll have to sort out dba"""
        contact = Contact.objects.filter(hl_contact=self.telephone)
        if contact:
            if contact[0].address:
                return contact[0].address
        else:
            return None

class Messaging(models.Model):
    """Inbuilt messaging model"""
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        blank=True, null=True
    )
    hl_service = models.CharField(max_length=100, verbose_name='Service')
    hl_contact = models.CharField(max_length=25, verbose_name='Contact')
    hl_key = models.IntegerField(verbose_name='Key')
    hl_type = models.CharField(max_length=6, verbose_name='Type')
    hl_status = models.CharField(max_length=7, verbose_name='Status')
    hl_staff = models.IntegerField(verbose_name='Staff', blank=True, null=True)
    hl_content = models.TextField(verbose_name='Content')
    hl_time = models.IntegerField(verbose_name='Time')

    def get_formatted_time(self):
        """Get ISO formated time from time stamp"""
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.hl_time))

    def __unicode__(self):
        return str(self.hl_contact)

    def __str__(self):
        return str(self.hl_contact)

class Role(models.Model):
    hl_role = models.CharField(max_length=100)
    hl_context = models.CharField(max_length=100)
    hl_status = models.IntegerField()
    hl_count = models.IntegerField()
    hl_time = models.IntegerField()


class Schedule(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        blank=True, null=True
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        blank=True, null=True
    )
    hl_status = models.CharField(max_length=7)

    class Meta:
        unique_together = (('user', 'service'),)

    def __unicode__(self):
        return str(self.id)

    def __str__(self):
        return str(self.id)


class Search(models.Model):
    hl_word = models.CharField(unique=True, max_length=100)
    hl_path = models.CharField(max_length=100)
    hl_menu = models.CharField(max_length=100)
    hl_service = models.CharField(max_length=100)


class Scheme(models.Model):
    """Insuarance scheme that a caller belongs to"""
    name = models.CharField(max_length=50)

    def __unicode__(self):
        return str(self.name)


class SMSCDR(models.Model):
    sender = models.CharField(max_length=30)
    receiver = models.CharField(max_length=30)
    msg = models.CharField(max_length=320, blank=True, null=True)
    time = models.DateTimeField(db_column='Time', blank=True, null=True)
    uniqueid = models.CharField(max_length=50)
    received = models.IntegerField()
    processing = models.IntegerField()
    processing_by = models.IntegerField()
    dateprocessed = models.DateTimeField()
    processed_by = models.IntegerField()
    link_id = models.CharField(max_length=300)


class HelplineUser(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name='HelplineUser'
    )
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        blank=True, null=True
    )
    hl_key = models.IntegerField(
        unique=True, primary_key=True,
        verbose_name=_('Key'),
        help_text=_('Autogenerated')
    )
    hl_auth = models.IntegerField(
        verbose_name=_('Auth'),
        help_text=_('Autogenerated Four digit numeric number e.g. 1973.')
    )
    hl_pass = models.CharField(
        max_length=500,
        verbose_name=_('PIN'), help_text=_('Four digit numeric PIN')
    )
    hl_exten = models.CharField(
        max_length=55,
        blank=True, null=True,
        verbose_name=_('Exten'), help_text=_('Agent Softphone extension.')
    )
    hl_status = models.CharField(
        max_length=11, blank=True,
        null=True,
        verbose_name=_('Status')
    )
    hl_calls = models.IntegerField(
        blank=True, null=True,
        verbose_name=_('Total Calls')
    )
    hl_email = models.CharField(
        max_length=500, blank=True,
        null=True,
        verbose_name=_('Email')
    )
    hl_names = models.CharField(
        max_length=250,
        blank=True,
        null=True,
        verbose_name=_('Names'))
    hl_nick = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Nick')
    )
    hl_avatar = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Avatar'))
    hl_role = models.CharField(
        max_length=10,
        blank=True, null=True,
        verbose_name=_('Role')
    )
    hl_area = models.CharField(
        max_length=100,
        blank=True, null=True,
        verbose_name=_("Area")
    )
    hl_phone = models.CharField(
        max_length=25,
        blank=True, null=True,
        verbose_name=_('Phone'))
    hl_branch = models.CharField(
        max_length=13,
        blank=True, null=True,
        verbose_name=_('Branch'))
    hl_case = models.IntegerField(
        blank=True, null=True,
        verbose_name=_('Case'))
    hl_clock = models.IntegerField(
        blank=True, null=True,
        verbose_name=_('Clock')
    )
    hl_time = models.IntegerField(
        blank=True, null=True,
        verbose_name=_('Time')
    )

    def get_schedule(self):
        """Returns the users schedule in the helpline"""
        return Schedule.objects.filter(user=self.user)

    def __unicode__(self):
        return self.hl_names if self.hl_names else "No Name"

    def __str__(self):
        return self.hl_names if self.hl_names else "No Name"

    def get_average_talk_time(self):
        """Get the average talk time for a user.
        Counted from the last midnight"""
        # Get the epoch time of the last midnight
        midnight_datetime = datetime.combine(date.today(),
                                             datetime_time.min)
        midnight = calendar.timegm(midnight_datetime.timetuple())

        # Get the average seconds of hold time from last midnight.
        # Return global values for supervisors.
        if self.user.is_staff:
            seconds = Report.objects.filter(
                calldate=date.today()).aggregate(
                    Avg('talktime')).get('talktime__avg')
        else:
            seconds = Report.objects.filter(
                calldate=date.today()).aggregate(
                    Avg('talktime')).get('talktime__avg')

        td = timedelta(seconds=seconds if seconds else 0)
        att = {'hours': "%02d" % (td.seconds//3600),
               'min': "%02d" % ((td.seconds//60) % 60),
               'seconds': "%02d" % ((td.seconds) % 60)}
        return att

    def get_average_wait_time(self):
        """Get the average hold time for a user.
        Counted from the last midnight"""
        # Get the epoch time of the last midnight
        midnight_datetime = datetime.combine(date.today(),
                                    datetime_time.min)
        midnight = calendar.timegm(midnight_datetime.timetuple())
        # Get the average seconds of hold time from last midnight.
        # Return global values for supervisors.
        if self.user.is_staff:
            seconds = MainCDR.objects.filter(
                hl_time__gt=midnight).filter(
                    hl_agent__exact=self.hl_key).aggregate(
                        Avg('hl_holdtime')).get('hl_holdtime__avg')
        else:
            seconds = MainCDR.objects.filter(
                hl_time__gt=midnight).aggregate(
                        Avg('hl_holdtime')).get('hl_holdtime__avg')

        td = timedelta(seconds = seconds if seconds else 0)
        awt = {'hours':"%02d" % (td.seconds//3600)
            ,'min':"%02d" % ((td.seconds//60)%60),'seconds': "%02d" % ((td.seconds)%60)}
        return awt

    def get_login_duration(self):
        time_now = timezone.now()
        last_login = self.user.last_login if self.user.last_login else timezone.now()
        ld = time_now - last_login
        login_duration = {
            'hours': "%02d" % (ld.seconds//3600),
            'min': "%02d" % ((ld.seconds//60) % 60),
            'seconds': "%02d" % ((ld.seconds) % 60)
        }
        return login_duration

    def get_ready_duration(self):
        """Get how long the agent has been on the queue"""
        clockin = Clock.objects.filter(
            user=self.user,
            hl_clock="Queue Join").order_by('-id').first()
        clockout = Clock.objects.filter(
            user=self.user,
            hl_clock="Queue Leave"
        ).order_by('-id').first()

        if clockin:
            if clockout:
                if clockout.hl_time > clockin.hl_time:
                    return
            seconds = time.time() - clockin.hl_time
            ld = timedelta(seconds=seconds if seconds else 0)
            ready_duration = {
                'hours': "%02d" % (ld.seconds//3600),
                'min': "%02d" % (
                    (ld.seconds//60) % 60),
                'seconds': "%02d" % (
                    (ld.seconds) % 60)
            }
            return ready_duration
        else:
            return

    def get_recent_clocks(self):
        """Get recent actions A.K.A Clocks
        We return only 5 at this time."""
        return Clock.objects.filter(user=self.user).order_by('-id')[:5]


class Cdr(models.Model):
    """A CDR consists of a unique identifier and several
    fields of information about a call"""
    accountcode = models.IntegerField(blank=True, null=True)
    calldate = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    clid = models.CharField(max_length=80, blank=True, null=True)
    src = models.CharField(max_length=80, blank=True, null=True)
    dst = models.CharField(max_length=80, blank=True, null=True)
    dcontext = models.CharField(max_length=80, blank=True, null=True)
    channel = models.CharField(max_length=80, blank=True, null=True)
    dstchannel = models.CharField(max_length=80, blank=True, null=True)
    lastapp = models.CharField(max_length=80, blank=True, null=True)

    lastdata = models.CharField(max_length=80, blank=True, null=True)
    duration = models.IntegerField(blank=True, null=True)
    billsec = models.IntegerField(blank=True, null=True)
    disposition = models.CharField(max_length=45, blank=True, null=True)
    amaflags = models.IntegerField(blank=True, null=True)
    accountcode = models.CharField(max_length=50, blank=True, null=True)
    uniqueid = models.CharField(max_length=50, blank=True, null=True)
    userfield = models.CharField(max_length=255, blank=True, null=True)
    recordingfile = models.CharField(max_length=255, blank=True, null=True)
    peeraccount = models.CharField(max_length=50, blank=True, null=True)
    linkedid = models.CharField(max_length=50, blank=True, null=True)
    sequence = models.CharField(max_length=50, blank=True, null=True)

    def __unicode__(self):
        return "%s -> %s" % (self.src, self.dst)

    def __str__(self):
        return "%s -> %s" % (self.src, self.dst)

    def get_case(self):
        return Case.objects.get(hl_unique=self.uniqueid)


class DID(models.Model):
    """DIDs or Phone numbers go here"""
    hotdesk = models.ManyToManyField(
        Hotdesk, related_name="did_assigned_hotdesks",
        blank=True
    )
    # Phone number to be used e.g +254XXXX
    number = models.CharField(max_length=45, blank=True, null=True)
    comment = models.CharField(max_length=80, blank=True, null=True)
    # If you need to add a prefix before a dialed out number
    # E.g 9 should be added automatically to use this DID
    prefix = models.CharField(max_length=5, blank=True, null=True)


class RecordPlay(models.Model):
    """Record Play list"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        blank=True, null=True
    )
    numeric_id = models.BigIntegerField(blank=True, null=True)
    name = models.CharField(max_length=50, blank=True, null=True)
    created_on = models.DateTimeField(_("Created on"), auto_now_add=True)
    audio = models.BooleanField(default=False)
    audio_codec = models.CharField(max_length=10, blank=True, null=True)
    video = models.BooleanField(default=False)
    video_codec = models.CharField(max_length=10, blank=True, null=True)
    data = models.BooleanField(default=False)


@receiver(pre_save, sender=Service)
def pre_save_receiver(sender, instance, *args, **kwargs):
    """Create a new slug before save"""
    if not instance.slug:
        instance.slug = unique_slug_generator(instance)
