# -*- coding: utf-8 -*-
import xml.etree.ElementTree as ET
import socket
import hashlib
import selectors
import re
import time


ECCP_PORT = 20005


class ECCPConnFailedException(Exception):
    pass


class ECCPUnauthorizedException(Exception):
    pass


class ECCPIOException(Exception):
    pass


class ECCPMalformedXMLException(Exception):
    pass


class ECCPUnrecognizedPacketException(Exception):
    pass


class ECCPBadRequestException(Exception):
    pass


class ECCP:
    def __init__(self):
        self._listaEventos = []  # Lista de eventos pendientes
        self._parseError = None
        self._response = None  # Respuesta recibida para un requerimiento
        self._parser = None  # Parser expat para separar los paquetes
        self._iPosFinal = 0 # Posición de parser para el paquete parseado
        self._sTipoDoc = None  # Tipo de paquete. Solo se acepta 'event' y 'response'
        self._bufferXML = ''  # Datos pendientes que no forman un paquete completo
        self._iNestLevel = 0  # Al llegar a cero, se tiene fin de paquete
        self._hConn = None
        self._iRequestID = 0
        self._sAppCookie = None
        self._agentNumber = ''
        self._agentStatus = ''
        self._agentPass = ''
        self._agentHash = ''
        self._loginResponse = ''

    def agentHash(self, agent_number, agent_pass):
        """Agent hash for auth"""
        return hashlib.md5(
            (self._sAppCookie + agent_number + agent_pass).encode()
        ).hexdigest()

    def login(self, username, password):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, "login")
        xml_cmdRequest_username = ET.SubElement(xml_cmdRequest, "username")
        xml_cmdRequest_username.text = username.replace('&', '&amp;')
        xml_cmdRequest_password = ET.SubElement(xml_cmdRequest, "password")
        xml_cmdRequest_password.text = password if re.match('^[a-fA-F0-9]{32}$', password) else hashlib.md5(password.encode()).hexdigest()

        xml_response = self.send_request(xml_request)

        # Find the 'login_response' element
        login_response_element = xml_response.find('login_response')

        # Check if 'success' element is present
        success_element = login_response_element.find('success')
        if success_element is not None:
            # 'success' element exists
            login_response_success = True
        else:
            # 'success' element is not present
            login_response_success = False

        print(f"Login Response: {xml_response.text}")
        print(f"Login Response BOOL: {login_response_success}")

        return login_response_success


    def connect(self, server, username, secret):
        iPuerto = ECCP_PORT
        if ':' in server:
            c = server.split(':')
            server = c[0]
            iPuerto = int(c[1])

        try:
            self._hConn = socket.create_connection((server, iPuerto))
        except Exception as e:
            raise ECCPConnFailedException(f"{server}:{iPuerto}: {e}")

        return self.login(username, secret)

    def setAgentNumber(self, sAgentNumber):
        self._agentNumber = sAgentNumber

    def setAgentPass(self, sAgentPass):
        self._agentPass = sAgentPass

    def logout(self):
        xml_logout = ET.Element('Logout')
        self.send_request(xml_logout)
        self._sAppCookie = None

    def disconnect(self):
        self.logout()
        if self._parser is not None:
            self._parser = None
        self._hConn.close()
        self._hConn = None

    def send_request(self, xml_request):
        self._iRequestID += 1
        xml_request.set('id', str(self._iRequestID))
        xml_request_str = ET.tostring(xml_request, encoding='utf-8')
        s = xml_request_str
        while s:
            iEscrito = self._hConn.send(s)
            if iEscrito <= 0:
                raise ECCPIOException('output')
            s = s[iEscrito:]
        xml_response = self.wait_response()
        # return xml_response
        xml_string = xml_response.decode('utf-8')
        # Parse the XML string
        root = ET.fromstring(xml_string)

        failure = root.find('failure')

        if failure:
            raise ECCPBadRequestException(
                failure.find('message').text,
                int(failure.find('code').text)
            )
        return root

    def loginagent(self, extension, password=None, timeout=None):
        xml_request = ET.Element("request")

        self._agentHash = self.agentHash(self._agentNumber, self._agentPass)

        xml_cmdRequest = ET.SubElement(xml_request, "loginagent")
        ET.SubElement(xml_cmdRequest, "agent_number").text = self._agentNumber
        ET.SubElement(xml_cmdRequest, "agent_hash").text = self._agentHash
        ET.SubElement(xml_cmdRequest, "extension").text = extension.replace('&', '&amp;')
        if password is not None:
            ET.SubElement(xml_cmdRequest, "password").text = password.replace('&', '&amp;')
        if timeout is not None:
            ET.SubElement(xml_cmdRequest, "timeout").text = timeout.replace('&', '&amp;')
        xml_response = self.send_request(xml_request)
        xml_request_str = ET.tostring(xml_request, encoding="utf-8", method="xml")
        print(f"STRING {xml_request_str}")
        failure = xml_response.find('loginagent_response').find('failure')

        if failure:
            raise ECCPBadRequestException(
                failure.find('message').text,
                int(failure.find('code').text)
            )
        return xml_response.find('loginagent_response').find("status").text

    def logoutagent(self):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, "logoutagent")
        ET.SubElement(xml_cmdRequest, "agent_number").text = self._agentNumber
        ET.SubElement(xml_cmdRequest, "agent_hash").text = self.agentHash(self._agentNumber, self._agentPass)
        xml_response = self.send_request(xml_request)
        return xml_response.logoutagent_response


    def getagentstatus(self, sAgentNumber=None):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, "getagentstatus")
        xml_cmdRequest_agent_number = ET.SubElement(xml_cmdRequest, "agent_number")
        xml_cmdRequest_agent_number.text = self._agentNumber if sAgentNumber is None else sAgentNumber
        xml_response = self.send_request(xml_request)
        return xml_response.find("getagentstatus_response").find("status").text

    def mixmonitormute(self, timeout=None):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, "mixmonitormute")
        xml_cmdRequest.addChild("agent_number", self._agentNumber)
        xml_cmdRequest.addChild("agent_hash", self.agentHash(self._agentNumber, self._agentPass))
        if timeout is not None and int(timeout) > 0:
            xml_cmdRequest.addChild("timeout", str(int(timeout)))
        xml_response = self.send_request(xml_request)
        return xml_response.find("mixmonitormute_response")

    def mixmonitorunmute(self):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, "mixmonitorunmute")
        xml_cmdRequest.addChild("agent_number", self._agentNumber)
        xml_cmdRequest.addChild("agent_hash", self.agentHash(self._agentNumber, self._agentPass))
        xml_response = self.send_request(xml_request)
        return xml_response.find("mixmonitorunmute_response")

    def getmultipleagentstatus(self, agentlist):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, "getmultipleagentstatus")
        xml_agents = ET.SubElement(xml_cmdRequest, "agents")
        for agentNumber in agentlist:
            xml_agents.addChild("agent_number", agentNumber)
        xml_response = self.send_request(xml_request)
        return xml_response.find("getmultipleagentstatus_response")

    def getcampaigninfo(self, campaign_type, campaign_id):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, "getcampaigninfo")
        xml_cmdRequest.addChild("campaign_type", campaign_type.replace("&", "&amp;"))
        xml_cmdRequest.addChild("campaign_id", campaign_id.replace("&", "&amp;"))
        xml_response = self.send_request(xml_request)
        return xml_response.find("getcampaigninfo_response")

    def getqueuescript(self, queue):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, "getqueuescript")
        xml_cmdRequest.addChild("queue", queue.replace("&", "&amp;"))
        xml_response = self.send_request(xml_request)
        return xml_response.find("getqueuescript_response")

    def getcallinfo(self, campaign_type, campaign_id, call_id):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, 'getcallinfo')
        xml_cmdRequest_child1 = ET.SubElement(xml_cmdRequest, 'campaign_type')
        xml_cmdRequest_child1.text = campaign_type.replace('&', '&amp;')
        if campaign_id is not None:
            xml_cmdRequest_child2 = ET.SubElement(xml_cmdRequest, 'campaign_id')
            xml_cmdRequest_child2.text = campaign_id.replace('&', '&amp;')
        xml_cmdRequest_child3 = ET.SubElement(xml_cmdRequest, 'call_id')
        xml_cmdRequest_child3.text = call_id.replace('&', '&amp;')
        xml_response = self.send_request(xml_request)
        return xml_response.find('getcallinfo_response').text

    def setcontact(self, call_id, contact_id):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, 'setcontact')
        xml_cmdRequest_child1 = ET.SubElement(xml_cmdRequest, 'agent_number')
        xml_cmdRequest_child1.text = self._agentNumber
        xml_cmdRequest_child2 = ET.SubElement(xml_cmdRequest, 'agent_hash')
        xml_cmdRequest_child2.text = self.agentHash(self._agentNumber, self._agentPass)
        xml_cmdRequest_child3 = ET.SubElement(xml_cmdRequest, 'call_id')
        xml_cmdRequest_child3.text = call_id.replace('&', '&amp;')
        xml_cmdRequest_child4 = ET.SubElement(xml_cmdRequest, 'contact_id')
        xml_cmdRequest_child4.text = contact_id.replace('&', '&amp;')
        xml_response = self.send_request(xml_request)
        return xml_response.find('setcontact_response').text

    def saveformdata(self, campaign_type, call_id, formdata):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, 'saveformdata')
        xml_cmdRequest_child1 = ET.SubElement(xml_cmdRequest, 'agent_number')
        xml_cmdRequest_child1.text = self._agentNumber
        xml_cmdRequest_child2 = ET.SubElement(xml_cmdRequest, 'agent_hash')
        xml_cmdRequest_child2.text = self.agentHash(self._agentNumber, self._agentPass)
        xml_cmdRequest_child3 = ET.SubElement(xml_cmdRequest, 'campaign_type')
        xml_cmdRequest_child3.text = campaign_type.replace('&', '&amp;')
        xml_cmdRequest_child4 = ET.SubElement(xml_cmdRequest, 'call_id')
        xml_cmdRequest_child4.text = call_id.replace('&', '&amp;')

        xml_forms = ET.SubElement(xml_cmdRequest, 'forms')
        for idForm, fields in formdata.items():
            xml_form = ET.SubElement(xml_forms, 'form')
            xml_form.set('id', idForm)
            for idField, sFieldValue in fields.items():
                xml_field = ET.SubElement(xml_form, 'field')
                xml_field.set('id', idField)
                xml_field.text = sFieldValue.replace('&', '&amp;')

        xml_response = self.send_request(xml_request)
        return xml_response.find('saveformdata_response').text

    def getpauses(self):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, 'getpauses')
        xml_response = self.send_request(xml_request)
        return xml_response.find('getpauses_response').text

    def pauseagent(self, pause_type):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, "pauseagent")
        ET.SubElement(xml_cmdRequest, "agent_number").text = self._agentNumber
        ET.SubElement(xml_cmdRequest, "agent_hash").text = self.agentHash(self._agentNumber, self._agentPass)
        ET.SubElement(xml_cmdRequest, "pause_type").text = pause_type.replace('&', '&amp;')
        xml_response = self.send_request(xml_request)
        return xml_response.find("pauseagent_response").text

    def unpauseagent(self):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, "unpauseagent")
        ET.SubElement(xml_cmdRequest, "agent_number").text = self._agentNumber
        ET.SubElement(xml_cmdRequest, "agent_hash").text = self.agentHash(self._agentNumber, self._agentPass)
        xml_response = self.send_request(xml_request)
        return xml_response.find("unpauseagent_response").text

    def hangup(self):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, "hangup")
        ET.SubElement(xml_cmdRequest, "agent_number").text = self._agentNumber
        ET.SubElement(xml_cmdRequest, "agent_hash").text = self.agentHash(self._agentNumber, self._agentPass)
        xml_response = self.send_request(xml_request)
        return xml_response.find("hangup_response").text

    def hold(self):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, "hold")
        ET.SubElement(xml_cmdRequest, "agent_number").text = self._agentNumber
        ET.SubElement(xml_cmdRequest, "agent_hash").text = self.agentHash(self._agentNumber, self._agentPass)
        xml_response = self.send_request(xml_request)
        return xml_response.find("hold_response").text

    def unhold(self):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, "unhold")
        ET.SubElement(xml_cmdRequest, "agent_number").text = self._agentNumber
        ET.SubElement(xml_cmdRequest, "agent_hash").text = self.agentHash(self._agentNumber, self._agentPass)
        xml_response = self.send_request(xml_request)
        return xml_response.find("unhold_response").text

    def transfercall(self, extension):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, "transfercall")
        ET.SubElement(xml_cmdRequest, "agent_number").text = self._agentNumber
        ET.SubElement(xml_cmdRequest, "agent_hash").text = self.agentHash(self._agentNumber, self._agentPass)
        ET.SubElement(xml_cmdRequest, "extension").text = extension.replace('&', '&amp;')
        xml_response = self.send_request(xml_request)
        return xml_response.find("transfercall_response").text

    def atxfercall(self, extension):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, "atxfercall")
        ET.SubElement(xml_cmdRequest, "agent_number").text = self._agentNumber
        ET.SubElement(xml_cmdRequest, "agent_hash").text = self.agentHash(self._agentNumber, self._agentPass)
        ET.SubElement(xml_cmdRequest, "extension").text = extension.replace('&', '&amp;')
        xml_response = self.send_request(xml_request)
        return xml_response.find("atxfercall_response").text

    def getcampaignstatus(self, campaign_type, campaign_id, datetime_start=None):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, "getcampaignstatus")
        ET.SubElement(xml_cmdRequest, "campaign_type").text = campaign_type.replace('&', '&amp;')
        ET.SubElement(xml_cmdRequest, "campaign_id").text = campaign_id.replace('&', '&amp;')
        if datetime_start is not None:
            ET.SubElement(xml_cmdRequest, "datetime_start").text = datetime_start.replace('&', '&amp;')
        xml_response = self.send_request(xml_request)
        return xml_response.find("getcampaignstatus_response").text

    def dial(self):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, "dial")
        xml_response = self.send_request(xml_request)
        return xml_response.find("dial_response").text

    def getrequestlist(self):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, "getrequestlist")
        xml_response = self.send_request(xml_request)
        return xml_response.find("getrequestlist_response").text

    def schedulecall(self, schedule, sameagent, newphone, newcontactname,
                     campaign_type=None, call_id=None):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, "schedulecall")
        ET.SubElement(xml_cmdRequest, "agent_number").text = self._agentNumber
        ET.SubElement(xml_cmdRequest, "agent_hash").text = self.agentHash(self._agentNumber, self._agentPass)
        
        if isinstance(schedule, dict):
            xml_schedule = ET.SubElement(xml_cmdRequest, "schedule")
            for k in ['date_init', 'date_end', 'time_init', 'time_end']:
                if k in schedule:
                    ET.SubElement(xml_schedule, k).text = schedule[k]
        
        if sameagent:
            ET.SubElement(xml_cmdRequest, "sameagent").text = "1"
        if newphone is not None:
            ET.SubElement(xml_cmdRequest, "newphone").text = newphone.replace('&', '&amp;')
        if newcontactname is not None:
            ET.SubElement(xml_cmdRequest, "newcontactname").text = newcontactname.replace('&', '&amp;')
        if campaign_type is not None:
            ET.SubElement(xml_cmdRequest, "campaign_type").text = campaign_type.replace('&', '&amp;')
        if call_id is not None:
            ET.SubElement(xml_cmdRequest, "call_id").text = call_id.replace('&', '&amp;')

        xml_response = self.send_request(xml_request)
        return xml_response.find("schedulecall_response").text

    def filterbyagent(self):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, "filterbyagent")
        ET.SubElement(xml_cmdRequest, "agent_number").text = self._agentNumber
        xml_response = self.send_request(xml_request)
        return xml_response.find("filterbyagent_response").text

    def removefilterbyagent(self):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, "filterbyagent")
        ET.SubElement(xml_cmdRequest, "agent_number").text = "any"
        xml_response = self.send_request(xml_request)
        return xml_response.find("filterbyagent_response").text


    def getchanvars(self, sAgentNumber=None):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, "getchanvars")
        ET.SubElement(xml_cmdRequest, "agent_number").text = self._agentNumber if sAgentNumber is None else sAgentNumber
        ET.SubElement(xml_cmdRequest, "agent_hash").text = self.agentHash(self._agentNumber, self._agentPass)
        xml_response = self.send_request(xml_request)
        return xml_response.find('getchanvars_response').text

    def getcampaignlist(self, campaign_type=None, status=None,
                        filtername=None, datetime_start=None, datetime_end=None,
                        offset=None, limit=None):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, "getcampaignlist")
        if campaign_type is not None:
            ET.SubElement(xml_cmdRequest, "campaign_type").text = campaign_type.replace('&', '&amp;')
        if status is not None:
            ET.SubElement(xml_cmdRequest, "status").text = status.replace('&', '&amp;')
        if filtername is not None:
            ET.SubElement(xml_cmdRequest, "filtername").text = filtername.replace('&', '&amp;')
        if datetime_start is not None:
            ET.SubElement(xml_cmdRequest, "datetime_start").text = datetime_start.replace('&', '&amp;')
        if datetime_end is not None:
            ET.SubElement(xml_cmdRequest, "datetime_end").text = datetime_end.replace('&', '&amp;')
        if offset is not None:
            ET.SubElement(xml_cmdRequest, "offset").text = offset.replace('&', '&amp;')
        if limit is not None:
            ET.SubElement(xml_cmdRequest, "limit").text = limit.replace('&', '&amp;')
        xml_response = self.send_request(xml_request)
        return xml_response.find("getcampaignlist_response").text

    def getcampaignqueuewait(self, campaign_type, campaign_id):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, 'getcampaignqueuewait')
        xml_cmdRequest_child1 = ET.SubElement(xml_cmdRequest, 'campaign_type')
        xml_cmdRequest_child1.text = campaign_type.replace('&', '&amp;')
        xml_cmdRequest_child2 = ET.SubElement(xml_cmdRequest, 'campaign_id')
        xml_cmdRequest_child2.text = campaign_id.replace('&', '&amp;')
        xml_response = self.send_request(xml_request)
        return xml_response.find('getcampaignqueuewait_response').text

    def getagentqueues(self, sAgentNumber=None):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, 'getagentqueues')
        agent_number = sAgentNumber if sAgentNumber is not None else self._agentNumber
        ET.SubElement(xml_cmdRequest, 'agent_number').text = agent_number
        xml_response = self.send_request(xml_request)
        return xml_response.find('getagentqueues_response').text
    
    def getmultipleagentqueues(self, agentlist):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, "getmultipleagentqueues")
        xml_agents = ET.SubElement(xml_cmdRequest, "agents")
        for sAgentNumber in agentlist:
            ET.SubElement(xml_agents, "agent_number").text = sAgentNumber
        xml_response = self.send_request(xml_request)
        return xml_response.find('getmultipleagentqueues_response')

    def getagentactivitysummary(self, datetime_start=None, datetime_end=None):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, "getagentactivitysummary")
        if datetime_start is not None:
            ET.SubElement(xml_cmdRequest, "datetime_start").text = datetime_start.replace('&', '&amp;')
        if datetime_end is not None:
            ET.SubElement(xml_cmdRequest, "datetime_end").text = datetime_end.replace('&', '&amp;')
        xml_response = self.send_request(xml_request)
        return xml_response.find('getagentactivitysummary_response')


    def campaignlog(self, campaign_type, campaign_id=None, queue=None, datetime_start=None,
                    datetime_end=None, lastN=None, idbefore=0):
        xml_request = ET.Element('request')
        xml_cmdRequest = ET.SubElement(xml_request, 'campaignlog')
        xml_cmdRequest.addChild('campaign_type').text = campaign_type.replace('&', '&amp;')
        if campaign_id is not None:
            xml_cmdRequest.addChild('campaign_id').text = campaign_id.replace('&', '&amp;')
        if queue is not None:
            xml_cmdRequest.addChild('queue').text = queue.replace('&', '&amp;')
        if datetime_start is not None:
            xml_cmdRequest.addChild('datetime_start').text = datetime_start.replace('&', '&amp;')
        if datetime_end is not None:
            xml_cmdRequest.addChild('datetime_end').text = datetime_end.replace('&', '&amp;')
        if lastN is not None:
            xml_cmdRequest.addChild('last_n').text = lastN
        if idbefore is not None:
            xml_cmdRequest.addChild('idbefore').text = str(idbefore)
        xml_response = self.send_request(xml_request)
        return xml_response.find('campaignlog_response')
    
    def callprogress(self, enable):
        xml_request = ET.Element('request')
        xml_cmdRequest = ET.SubElement(xml_request, 'callprogress')
        xml_cmdRequest.addChild('enable').text = '1' if enable else '0'
        xml_response = self.send_request(xml_request)
        return xml_response.find('callprogress_response')
    
    def getincomingqueuestatus(self, queue, datetime_start=None):
        xml_request = ET.Element('request')
        xml_cmdRequest = ET.SubElement(xml_request, 'getincomingqueuestatus')
        xml_cmdRequest.addChild('queue').text = queue.replace('&', '&amp;')
        if datetime_start is not None:
            xml_cmdRequest.addChild('datetime_start').text = datetime_start.replace('&', '&amp;')
        xml_response = self.send_request(xml_request)
        return xml_response.find('getincomingqueuestatus_response')
    
    def getincomingqueuelist(self):
        xml_request = ET.Element('request')
        xml_cmdRequest = ET.SubElement(xml_request, 'getincomingqueuelist')
        xml_response = self.send_request(xml_request)
        return xml_response.find('getincomingqueuelist_response')


    def pingagent(self):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, "pingagent")
        xml_cmdRequest_agent_number = ET.SubElement(xml_cmdRequest, "agent_number")
        xml_cmdRequest_agent_number.text = self._agentNumber
        xml_cmdRequest_agent_hash = ET.SubElement(xml_cmdRequest, "agent_hash")
        xml_cmdRequest_agent_hash.text = self.agentHash(self._agentNumber, self._agentPass)
        xml_response = self.send_request(xml_request)
        return xml_response.find("pingagent_response")

    
    def dumpstatus(self):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, "dumpstatus")
        xml_response = self.send_request(xml_request)
        return xml_response.find('dumpstatus_response')
    
    def refreshagents(self):
        xml_request = ET.Element("request")
        xml_cmdRequest = ET.SubElement(xml_request, "refreshagents")
        xml_response = self.send_request(xml_request)
        return xml_response.find('refreshagents_response')


    def start_element_handler(self, event, element):
        if event == 'start':
            # Process the start element
            print("Start element:", element.tag)

    def wait_response(self, timeout=None):
        iTotalPaquetes = 0
        iTimestampInicio = iTimestampFinal = None
        sel = selectors.DefaultSelector()


        while self._response is None:
            if timeout is None:
                sec = usec = None
            elif not self._listaEventos:
                sec = int(timeout)
                usec = int((timeout - sec) * 1000000)
            else:
                timeout = sec = usec = 0

            sel = selectors.DefaultSelector()
            # Register a socket for monitoring
            sel.register(self._hConn, selectors.EVENT_READ, data=None)
            # Monitor registered events
            events = sel.select()
            for key, mask in events:
                if key.data is None:
                    # Handle the server socket
                    print("Client socket is ready for reading.")
                else:
                    # Handle the client socket
                    client_socket = key.fileobj

                    # Read data from the client socket
                    data = client_socket.recv(1024)
                    if data:
                        # Process the received data
                        print("Received data:", data.decode())
                    else:
                        # Client closed the connection
                        sel.unregister(client_socket)
                        client_socket.close()
                        print("Client socket closed.")


            #listoLeer, _, _ = select.select([self._hConn], [], [], sec, usec)
            if not events:
                break

            s = self._hConn.recv(65536)
            if len(s) == 0:
                raise ECCPIOException('input')
            decoded_data = s.decode('utf-8')

            self._bufferXML += decoded_data

            if self._parser is None:
                self._parser = ET.XMLPullParser(['start', 'end'])
                #start_element_handler(event, element)
                self.StartElementHandler = self.xmlStartHandler
                self.EndElementHandler = self.xmlEndHandler

            self._parser.feed(s)
            # event, element = self._parser.read_events()

            # Iterate over the events
            for event, elem in self._parser.read_events():
                self._sTipoDoc = elem.tag
                # Save events
                self._listaEventos.append(elem)
                #print(event, elem)
                if elem.tag == 'app_cookie':
                    self._sAppCookie = elem.text
                #raise ECCPUnrecognizedPacketException(self._sTipoDoc)

                #self._bufferXML = self._bufferXML[self._iPosFinal + 1:]
                self._response = s
                self._resetParser()

            if iTimestampInicio is None:
                iTimestampInicio = time.time()
            iTimestampFinal = time.time()

            if timeout is not None and iTimestampFinal - iTimestampInicio >= timeout:
                break

        if self._response is not None:
            response = self._response
            self._response = None
            return response
        elif self._listaEventos:
            return self._listaEventos.pop(0)
        else:
            raise ECCPIOException('timeout')

    def getParseError(self):
        return self._parseError

    def getEvent(self):
        if self._listaEventos:
            return self._listaEventos.pop(0)
        else:
            raise ECCPIOException('No more events')

    def _parsearPaquetesXML(self, sDatos):
        iTotalPaquetes = 0

        while len(sDatos) > 0:
            s = sDatos[0]
            sDatos = sDatos[1:]

            if self._parser is None:
                self._parser = ET.XMLPullParser(['start', 'end'])
                self._parser._parser.StartElementHandler = self.xmlStartHandler
                self._parser._parser.EndElementHandler = self.xmlEndHandler

            self._parser.feed(s)

            if self._iNestLevel == 0:
                if self._sTipoDoc == 'response':
                    self._response = ET.fromstring(self._bufferXML[:self._iPosFinal + 1])
                    return 'response'
                elif self._sTipoDoc == 'event':
                    xml_event = ET.fromstring(self._bufferXML[:self._iPosFinal + 1])
                    self._listaEventos.append(xml_event)
                    return 'event'
                else:
                    raise ECCPUnrecognizedPacketException(self._sTipoDoc)

                self._bufferXML = self._bufferXML[self._iPosFinal + 1:]
                self._resetParser()

    def _resetParser(self):
        self._parser = None
        self._iPosFinal = None
        self._sTipoDoc = None
        self._iNestLevel = 0

    def xmlStartHandler(self, name, attrs):
        self._iNestLevel += 1

        if self._iNestLevel == 1:
            if name == 'event':
                self._sTipoDoc = 'event'
            elif name == 'response':
                self._sTipoDoc = 'response'
            else:
                self._sTipoDoc = None

        if self._iNestLevel == 1 and self._sTipoDoc is not None:
            self._bufferXML = ''

        if self._sTipoDoc is not None:
            self._bufferXML += '<' + name
            for k, v in attrs.items():
                self._bufferXML += ' ' + k + '="' + v + '"'
            self._bufferXML += '>'

    def xmlEndHandler(self, name):
        self._bufferXML += '</' + name + '>'
        if self._sTipoDoc is not None:
            self._iPosFinal = len(self._bufferXML) - 1

        self._iNestLevel -= 1

        if self._iNestLevel == 0:
            self._iPosFinal = len(self._bufferXML) - 1


def main():
    server = '127.0.0.1'
    username = 'helplineagentconsole'
    secret = '1dbf9d769b977302900637695761d397'

    eccp = ECCP()
    try:
        eccp.connect(server, username, secret)
        print('Connected successfully')
        # Do something with the ECCP connection
    except ECCPConnFailedException as e:
        print(f'Failed to connect: {str(e)}')
    except ECCPUnauthorizedException as e:
        print(f'Unauthorized: {str(e)}')
    except Exception as e:
        print(f'Error: {str(e)}')
    finally:
        eccp.disconnect()


if __name__ == '__main__':
    main()

