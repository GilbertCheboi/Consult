# -*- coding: utf-8 -*-

#
# Class Qpanel for Asterisk
#
# Copyright (C) 2015-2017 Rodrigo Ramírez Norambuena <a@rodrigoramirez.com>
#

from __future__ import absolute_import
from Asterisk.Manager import *


class ConnectionErrorAMI(Exception):
    '''
    This exception is raised when is not possible or is not connected to
    AMI for a requested action.
    '''
    _error = 'Not Connected'
    pass


class AsteriskAMI:

    def __init__(self, host, port, user, password):
        '''
        Initialise a class for Asterisk
        '''
        self.host = host
        self.port = int(port)
        self.password = password
        self.user = user
        self.is_connected = False
        self.connection = self.connect_ami()

    def connect_ami(self):
        try:
            manager = Manager((self.host, self.port), self.user, self.password)
            return manager
        except:
            return None

    def queueStatus(self):
        return self.getQueues()

    def getQueues(self):
        if self.connection is None:
            raise ConnectionErrorAMI(
                "Failed to connect to server at '{}:{}' for user {}\n"
                'Please check that Asterisk running and accepting AMI '
                'connections.'.format(self.host, self.port, self.user))

        cmd = self.connection.QueueStatus()
        return cmd

    def spy(self, channel, where_listen, option=None):
        '''Generate a Originate event by Manager to used Spy Application

        Parameters
        ----------
        channel: str
            channel to create Originate action tu use ChanSpy
        where_listen: str
            channel where listen the spy action.
        option: str
            other option to add for execute distinct options.
                whisper: w
                barge: B
            other string to add ChanSpy Command
            The option is concatenate to ',q'

        Returns
        -------
        originate result command : Dictionary
            if case the fail return return  {'Response': 'failed',
                                             'Message': str(msg)}
        '''

        options = ',q'
        if option:
            options = options + option
        try:
            # Add Spy Target to Caller ID
            # Channel Variable Should always be SIP/XXXX
            spy_target = channel.split("/")[1]
            # create a originate call for Spy a exten
            return self.connection.Originate(where_listen,
                                             application='ChanSpy',
                                             data=channel + options,
                                             caller_id=spy_target,
                                             async_param='yes')
        except Asterisk.Manager.ActionFailed as msg:
            return {'Response': 'failed', 'Message': str(msg)}
        except PermissionDenied as msg:
            return {'Response': 'failed', 'Message': 'Permission Denied'}

    def originate_call(self, channel, extension, option=None):
        '''Generate a Originate event by Manager to used Click to Call

        Parameters
        ----------
        channel: str
            channel to create Originate action e.g SIP/1001
        phone: str
            phone number to call

        Returns
        -------
        originate result command : Dictionary
            if case the fail return return  {'Response': 'failed',
                                             'Message': str(msg)}
        '''

        options = ''
        if option:
            options = options + option
        try:
            # create a originate call for an exten
            return self.connection.Originate(
                channel,
                extension=extension,
                context="from-internal",
                priority=1,
                async_param='yes',
                caller_id=extension
            )
        except Asterisk.Manager.ActionFailed as msg:
            return {
                'Response': 'failed',
                'Message': str(msg),
                "channel": channel,
                "extension": extension,
            }
        except PermissionDenied as msg:
            return {'Response': 'failed', 'Message': 'Permission Denied'}

    def hangup(self, channel):
        '''Hangup Channel

        Parameters
        ----------
        channel: str
            channel to hangup
        Returns
        -------
        hangup result action : Dictionary
            if case the fail return return  {'Response': 'failed',
                                             'Message': str(msg)}
        '''
        try:
            # hangup channels
            return self.connection.Hangup(channel)
        except Asterisk.Manager.ActionFailed as msg:
            return {'Response': 'failed', 'Message': str(msg)}
        except PermissionDenied as msg:
            return {'Response': 'failed', 'Message': 'Permission Denied'}

    def reset_stats(self, queue):
        'Reset stats for <queue>.'
        id = self.connection._write_action('QueueReset', {'Queue': queue})
        return self.connection._translate_response(
            self.connection.read_response(id))

    def isConnected(self):
        if not self.connection:
            return False
        return True

    def remove_from_queue(self, agent, queue):
        '''Remove a <agent> from a <queue>

        Parameters
        ----------
        agent: str
            Agent or Inteface to remove
        queue: str
            name of queue from remove agent
        Returns
        -------
        originate result command : Dictionary
            if case the fail return return  {'Response': 'failed',
                                             'Message': str(msg)}
        '''
        try:
            return self.connection.QueueRemove(queue, agent)
        except Asterisk.Manager.ActionFailed as msg:
            return {'Response': 'failed', 'Message': str(msg)}
        except PermissionDenied as msg:
            return {'Response': 'failed', 'Message': 'Permission Denied'}

    def add_to_queue(self, interface, queue, member_name=None):
        '''Add an <agent> to a <queue>

        Parameters
        ----------
        agent: str
            Agent or Inteface to add
        queue: str
            name of queue to add agent
        member_name: str
            name of agent
        Returns
        -------
        originate result command : Dictionary
            if case the fail return return  {'Response': 'failed',
                                             'Message': str(msg)}
        '''
        try:
            return self.connection.QueueAdd(
                queue=queue,
                interface=interface,
                penalty=0,
                member_name=member_name
            )
        except Asterisk.Manager.ActionFailed as msg:
            return {'Response': 'failed', 'Message': str(msg)}
        except PermissionDenied as msg:
            return {'Response': 'failed', 'Message': 'Permission Denied'}

    def db_put(self, family, key, value):
        """Add Asterisk astDB value"""
        try:
            return self.connection.DBPut(
                family,
                key,
                value,
            )
        except Asterisk.Manager.ActionFailed as msg:
            return {'Response': 'failed', 'Message': str(msg)}
        except PermissionDenied as msg:
            return {'Response': 'failed', 'Message': 'Permission Denied'}

    def db_get(self, family, key):
        """Get Asterisk astDB value"""
        try:
            return self.connection.DBGet(
                family,
                key,
            )
        except Asterisk.Manager.ActionFailed as msg:
            return {'Response': 'failed', 'Message': str(msg)}
        except PermissionDenied as msg:
            return {'Response': 'failed', 'Message': 'Permission Denied'}

    def db_del(self, family, key):
        """Delete Asterisk astDB value"""
        try:
            return self.connection.DBDel(
                family,
                key,
            )
        except Asterisk.Manager.ActionFailed as msg:
            return {'Response': 'failed', 'Message': str(msg)}
        except PermissionDenied as msg:
            return {'Response': 'failed', 'Message': 'Permission Denied'}

    def do_reload(self):
        """Do reload for backend PBX"""
        try:
            return self.connection.Command(
                'reload'
            )
        except Asterisk.Manager.ActionFailed as msg:
            return {'Response': 'failed', 'Message': str(msg)}
        except PermissionDenied as msg:
            return {'Response': 'failed', 'Message': 'Permission Denied'}

    def pause_queue_member(self, interface, queue, paused=None, reason=None):
        '''Pause an <agent> on a <queue>

        Parameters
        ----------
        agent: str
            Agent or Inteface to pause
        queue: str
            name of queue to pause agent
        paused: boolean
            True means the interface will be paused.
        reason: str
            reason for the break
        Returns
        -------
        originate result command : Dictionary
            if case the fail return return  {'Response': 'failed',
                                             'Message': str(msg)}
        '''
        try:
            return self.connection.QueuePause(
                queue=queue,
                interface=interface,
                paused=paused,
                reason=reason
            )
        except Asterisk.Manager.ActionFailed as msg:
            return {'Response': 'failed', 'Message': str(msg)}
        except PermissionDenied as msg:
            return {'Response': 'failed', 'Message': 'Permission Denied'}
