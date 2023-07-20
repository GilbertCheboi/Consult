# -*- coding: utf-8 -*-

#
# Copyright (C) 2015-2017 Rodrigo Ramírez Norambuena <a@rodrigoramirez.com>
#

from __future__ import absolute_import
from __future__ import print_function
from django.core.cache import cache
from .config import QPanelConfig
from .utils import timedelta_from_field_dict, realname_queue_rename
from .asterisk import *
import six
# In case use Asterisk dont crash with ESL not in system
try:
    from .freeswitch import *
except:
    pass

import os, sys

from helpline.models import Service

class ConnectionErrorAMI(Exception):
    pass


class Backend(object):

    def __init__(self, backend_manager_config=None):
        self.config = QPanelConfig()
        self.backend_manager_config = backend_manager_config

        section_config = 'freeswitch'
        if self.is_asterisk():
            section_config = 'manager'
            self.user = self.config.get(section_config, 'user')

        if backend_manager_config:
            self.user = self.backend_manager_config.username
            self.host = self.backend_manager_config.host
            self.port = int(self.backend_manager_config.port)
            self.password = self.backend_manager_config.password
        else:
            self.host = self.config.get(section_config, 'host')
            self.port = int(self.config.get(section_config, 'port'))
            self.password = self.config.get(section_config, 'password')

        self.connection = self._connect()

    def is_freeswitch(self):
        return self.config.is_freeswitch()

    def is_asterisk(self):
        return not self.is_freeswitch()

    def _connect(self):
        if self.is_freeswitch():
            return self._connect_esl()
        return self._connect_ami()

    def _connect_ami(self):
        manager = AsteriskAMI(self.host, self.port, self.user, self.password)
        return manager

    def _connect_esl(self):
        esl = Freeswitch(self.host, self.port, self.password)
        return esl

    def _get_data_queue_from_backend(self):
        self.connection = self._connect()
        try:
            return self.connection.queueStatus()
        except Exception as e:
            print(str(e))
            return {}

    def get_data_queues(self):
        data = self._get_data_queue_from_backend()
        return self.parse_data(data)

    def parse_data(self, data):
        data = self.hide_queue(data)
        data = self.rename_queue(data)
        if self.is_freeswitch():
            return self.parse_fs(data)
        return self.parse_asterisk(data)

    def parse_fs(self, data):
        for q in data:
            for m in data[q]['members']:
                member = data[q]['members'][m]
                member['LastBridgeEndAgo'] = str(timedelta_from_field_dict('LastBridgeEnd', member))
                member['LastStatusChangeAgo'] = str(timedelta_from_field_dict('LastStatusChange', member))

            for c in data[q]['entries']:
                data[q]['entries'][c]['CreatedEpochAgo'] = str(timedelta_from_field_dict('CreatedEpoch',
                                                                                     data[q]['entries'][c]))

        return data

    def parse_asterisk(self, data):
        # convert references manager to string
        for q in data:
            for e in list(data[q]['entries']):
                tmp = data[q]['entries'].pop(e)
                data[q]['entries'][str(e)] = tmp
                tmp = data[q]['entries'][str(e)]['Channel']
                data[q]['entries'][str(e)]['Channel'] = str(tmp)
            for m in data[q]['members']:
                member = data[q]['members'][m]
                # Asterisk 1.8 dont have StateInterface
                if 'StateInterface' not in member:
                    member['StateInterface'] = m

                member['LastCallAgo'] = str(timedelta_from_field_dict('LastCall', member))
                # Time last pause
                member['LastPauseAgo'] = str(timedelta_from_field_dict('LastPause', member))

                # introduced in_call flag
                # asterisk commit 90b06d1a3cc14998cd2083bd0c4c1023c0ca7a1f
                if 'InCall' in member and member['InCall'] == '1':
                    member['Status'] = '10'

            for c in data[q]['entries']:
                data[q]['entries'][c]['WaitAgo'] = str(timedelta_from_field_dict('Wait',
                                                                             data[q]['entries'][c], True))

        return data

    def hide_queue(self, data):
        tmp_data = {}
        hide = self.config.get_hide_config()
        show = self.config.get_show_config()
        if len(show) == 0:
            for q in data:
                if q not in hide:
                    tmp_data[q] = data[q]
        else:
            s = set(show)
            inter = s & six.viewkeys(data)
            tmp_data = {x:data[x] for x in inter if x in data}

        return tmp_data

    def get_service(self, q):
        """Get service name from queue name"""
        SERVICE_CACHE_TIMEOUT = 10
        try:
            service = cache.get_or_set(
                f'{self.backend_manager_config}_service_backend_{q}',
                Service.objects.get(
                    queue=q,
                    backend_manager_config=self.backend_manager_config
                ),
                SERVICE_CACHE_TIMEOUT
            )

            return service
        except Service.DoesNotExist:
            return None

    def rename_queue(self, data):
        """Rename queue from Service model data"""
        tmp_data = {}
        for q in data:
            service = self.get_service(q)
            if service:
                rename = service.name
                slug = service.slug
                registered = True
            else:
                rename = q
                slug = q
                registered = False

            tmp_data[q] = data[q]
            tmp_data[q]['name'] = rename
            tmp_data[q]['slug'] = slug
            tmp_data[q]['registered'] = registered
        return tmp_data

    def _call_spy(self, channel, to_exten, with_whisper=False):
        self.connection = self._connect()
        try:
            return self.connection.spy(channel, to_exten, with_whisper)
        except Exception as e:
            print(str(e))
            return {}

    def _originate_call(self, channel, to_exten):
        self.connection = self._connect()
        try:
            return self.connection.originate_call(channel, to_exten)
        except Exception as e:
            print(str(e))
            return {}


    def whisper(self, channel, to_exten):
        return self._call_spy(channel, to_exten, 'w')

    def spy(self, channel, to_exten):
        return self._call_spy(channel, to_exten)

    def originate_call(self, channel, to_exten):
        return self._originate_call(channel, to_exten)

    def barge(self, channel, to_exten):
        return self._call_spy(channel, to_exten, 'B')

    def reset_stats(self, queue):
        return self.connection.reset_stats(queue)

    def hangup(self, channel):
        try:
            return self.connection.hangup(channel)
        except Exception as e:
            print(str(e))
            return {}

    def remove_from_queue(self, agent, queue):
        queue = realname_queue_rename(queue)
        self.connection = self._connect()
        try:
            return self.connection.remove_from_queue(agent, queue)
        except Exception as e:
            print(str(e))
            return e

    def add_to_queue(self, queue, interface, member_name=None):
        queue = realname_queue_rename(queue)
        self.connection = self._connect()
        try:
            return self.connection.add_to_queue(
                queue=queue,
                interface=interface,
                member_name=member_name
            )
        except Exception as e:

            print(str(e))
            return {}

    def db_get(self, family, key):
        """Get values from astDB backend"""
        self.connection = self._connect()
        try:
            return self.connection.db_get(
                family=family,
                key=key,
            )
        except Exception as e:

            print(str(e))
            return {}

    def db_put(self, family, key, value):
        """Put values from astDB sqlite3 backend"""
        self.connection = self._connect()
        try:
            return self.connection.db_put(
                family=family,
                key=key,
                value=value,
            )
        except Exception as e:

            print(str(e))
            return {}

    def db_del(self, family, key):
        """Delete key and value from astDB sqlite3 backend"""
        self.connection = self._connect()
        try:
            return self.connection.db_del(
                family=family,
                key=key,
            )
        except Exception as e:

            print(str(e))
            return {}

    def do_reload(self):
        """Reload backend PBX"""
        self.connection = self._connect()
        try:
            return self.connection.do_reload()
        except Exception as e:

            print(str(e))
            return {}

    def pause_queue_member(self, queue, interface, paused, reason=None):
        queue = realname_queue_rename(queue)
        self.connection = self._connect()
        try:
            return self.connection.pause_queue_member(
                queue=queue,
                interface=interface,
                paused=paused,
                reason=reason
            )
        except Exception as e:

            print(str(e))
            return e

