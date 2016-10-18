#!/usr/bin/python -O

# Author: Florian Lambert <florian.lambert@enovance.com>

# Allow you to manage Worker/BalancerMember defined in your apache2 mod_proxy conf : 
#    <Proxy balancer://tomcatservers>
#        BalancerMember ajp://10.152.45.1:8001 route=web1 retry=60
#        BalancerMember ajp://10.152.45.2:8001 route=web2 retry=60
#    </Proxy>

# You have to allow /balancer-manager
# Like :
# ProxyPass /balancer-manager !
# <Location /balancer-manager>
#   SetHandler balancer-manager
#   Order Deny,Allow
#   Deny from all
#   Allow from 127.0.0.1
# </Location>

import argparse
import re
import HTMLParser
from urllib import urlencode
from urllib2 import Request, urlopen

# Get args
PARSER = argparse.ArgumentParser()
PARSER.add_argument("-l", "--list", 
            help="List Worker member and status", action='store_true')
PARSER.add_argument("-a", "--action", 
            help="\"add\", ""\"enable\", \"disable\", \"drain\", \"stop\", or \"rebalance\" the specified Worker", type=str)
PARSER.add_argument("-w", "--worker",
            help="Worker name : example ajp://127.0.0.1:8001", type=str)
ARGS = PARSER.parse_args()

#Fix if necessary
#vhostname
headers = {"Host": '127.0.0.1' }
#ip to reach apache
url="http://127.0.0.1/balancer-manager"

def balancer_status():
    req = Request(url, None, headers)
    f = urlopen(req)

    class TableParser(HTMLParser.HTMLParser):
        def __init__(self):
            self.datas=[]
            self._tds=[]
            HTMLParser.HTMLParser.__init__(self)
            self.in_td = False
        
        def handle_starttag(self, tag, attrs):
            if tag == 'td' or tag == 'th':
                self.in_td = True
        
        def handle_data(self, data):
            if self.in_td:
                self._tds.append(data)
        
        def handle_endtag(self, tag):
            self.in_td = False
            if tag == 'tr':
                self.datas.append(self._tds)
                self._tds = []
    
    p = TableParser()
    p.feed(f.read())

    template = "    {Worker:40} | {Status:10} | {Elected:10}"
    
    print template.format(Worker="Worker",Status="Status",Elected="Elected")
    for v in p.datas[2:]:
        print template.format(Worker=v[0],Status=v[4],Elected=v[5])

def find_balancer(html_file):
    result = re.search("b=([^&]+)&nonce=([^\"]+)", html_file.read())
    assert(result is not None)
    
    balancer = result.group(1)
    nonce = result.group(2)
        
    return balancer, nonce

def manage_worker(action, worker):
    # Read information
    req = Request(url, None, headers)
    html_file = urlopen(req)
    
    # Find balancer and nonce
    balancer, nonce = find_balancer(html_file)

    worker_regex = re.search( \
        "b=" + re.escape(balancer) + \
        "&w=" + re.escape(worker) + \
        "&nonce=" + re.escape(nonce), \
        html_file.read())
        
    query_map = {'b': balancer, 'nonce': nonce} 
    
    # Generate parameters
    if action == "add":
        assert(worker_regex is None)
        query_map['b_nwrker'] = worker
        query_map['b_wyes'] = '1'
    else:
        query_map['w'] = worker
        
        if action == "disable":
            query_map['w_status_D'] = '1'
        elif action == "enable":
            query_map['w_status_D'] = '0'
        elif action == "drain":
            query_map['w_status_N'] = '1'
        elif action == "stop":
            query_map['w_status_S'] = '1'
        elif action.startswith('rebalance'):
            action_split = action.split(':')
            if len(action_split) < 2:
                raise SystemExit('rebalance must be of format rebalance:load_factor')
            
            value = None
            try:
                value = int(action_split[1])
                assert(0 < value < 100)
            except Exception as ex:
                raise SystemExit('rebalance must have an integer value of between 0 and 100')
                
            query_map['w_lf'] = str(value)
            
        else:
            raise ValueError("action arg must be either disable or enable")

    req = Request(url, urlencode(query_map), headers)
    f = urlopen(req)
    print "Action\n    Worker %s [%s]\n" % (worker,action)
    balancer_status()


if __name__ == "__main__":
    #if ARGS.list is not None:
    if ARGS.list :
        balancer_status()
    elif ARGS.action and ARGS.worker:
        manage_worker(ARGS.action, ARGS.worker)
    else : PARSER.print_help()
