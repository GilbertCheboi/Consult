#!/usr/bin/env python3
import sys
from eccp import ECCP

if len(sys.argv) < 4:
    sys.exit("Use: {} agentchannel agentpassword extension".format(sys.argv[0]))

agentname = sys.argv[1]
agentpass = sys.argv[2]
extension = sys.argv[3]
agenthost = sys.argv[4]

x = ECCP()
try:
    print("Connect...")
    cr = x.connect(agenthost, "agentconsole", "agentconsole")
    if hasattr(cr, 'failure'):
        sys.exit('Failed to connect to ECCP - {}'.format(cr.failure.message))
    x.setAgentNumber(agentname)
    x.setAgentPass(agentpass)
    print(x.getagentstatus())
    print("Login agent")
    r = x.loginagent(sys.argv[3])
    print("Loged in agent")
    print(r)
    bFalloLogin = False
    if 'logged-in' in r:
        while not bFalloLogin:
            x.wait_response(1)
            while True:
                e = x.getEvent()
                if e is None:
                    break
                print(e)
                for ee in e.iterchildren():
                    evt = ee
                if evt.tag == 'agentfailedlogin':
                    bFalloLogin = True
                    break
    print("Disconnect...")
    x.disconnect()
except Exception as e:
    print(e)
    print(x.getParseError())

