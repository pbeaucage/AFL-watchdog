import logging
logging.basicConfig(level=logging.ERROR)

import time

import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

slack_token = os.environ['SLACK_TOKEN']
client = WebClient(token=slack_token)


from AFL.automation.APIServer.Client import Client

afl_system_serial = os.environ['AFL_SYSTEM_SERIAL']

def send_alert(text):
    alert_text = f"<!channel> {afl_system_serial}: {text}"
    print(f'    --> Sent alert to Slack {alert_text}')
    response = client.chat_postMessage(channel="C06F702K8HF",text=alert_text)

'''
server input schema:


    { 'address': 'localhost',
      'port':'5051',
      'suppress_alerts': [],

                Possible values for suppress_alerts include:
                        'server_down': warn if the server is unreachable.  encountering this error prevents all other alerts.
                        'server_paused_error': warn if the server is paused and last task errored
                        'server_idle_timeout': warn if the server has been idle for the last 5 checks
                        'server_paused': warn if the server is paused
                        'server_stuck': warn if the server has been running the same task for the last 5 checks
      'friendly_name': 'Test Server'
    },
'''

stuck_n_checks = 5
idle_n_checks = 5
servers = [
    { 'address': 'localhost',
      'port':'5051',
      'suppress_alerts': [],
      'friendly_name': 'Test Server'
    },

]
delay = 60

while True:
    for server in servers:
        if 'port' not in server.keys():
            server['port'] = '5000'
        if 'friendly_name' not in server.keys():
            server['friendly_name'] = server['address']
        if 'last_task_uuid' not in server.keys():
            server['last_task_uuid'] = ''
        if 'running_task_uuid' not in server.keys():
            server['running_task_uuid'] = ''
        if 'last_task_n_checks' not in server.keys():
            server['last_task_n_checks'] = 0
        if 'running_task_n_checks' not in server.keys():
            server['running_task_n_checks'] = 0

        print(f'Performing check on {server["friendly_name"]}')

        c = Client(server['address'],port=server['port'])
            
        # check for server_down    
        try:
            c.login('WatchDog')
        except Exception:
            if 'server_down' not in server['suppress_alerts']:
                send_alert(f'{server["friendly_name"]}: SERVER UNREACHABLE')
            continue
    
        # check for server_paused
        state = c.queue_state().content.decode(encoding='utf-8')
        
        if state == 'Paused' and 'server_paused' not in server['suppress_alerts']:
            send_alert(f'{server["friendly_name"]}: SERVER PAUSED')
        
        queue = c.get_queue()
        
        # check last task completion status
        if state == 'Paused' and 'server_paused_error' not in server['suppress_alerts']:
            if len(queue[1])>0:
                send_alert(f'{server["friendly_name"]}: SERVER PAUSED W/ RUNNING TASK (likely error)')
       
 
        if len(queue[1])>0:
            running_task_uuid = queue[1][0]['uuid']
        else:
            running_task_uuid = ''
        
        if len(queue[0])>0:
            last_task_uuid = queue[0][-1]['uuid']
        else:
            last_task_uuid = ''
        
        if running_task_uuid == server['running_task_uuid'] and running_task_uuid != '':
            server['running_task_n_checks']+= 1
        else:
            server['running_task_uuid'] = running_task_uuid
            server['running_task_n_checks'] = 0
        
        if last_task_uuid == server['last_task_uuid']:
            server['last_task_n_checks']+= 1
        else:
            server['last_task_uuid'] = last_task_uuid
            server['last_task_n_checks'] = 0

        if server['last_task_n_checks'] >= idle_n_checks and 'server_idle_timeout' not in server['suppress_alerts']:
            send_alert(f'{server["friendly_name"]} SERVER APPEARS IDLE, has not run for last {server["last_task_n_checks"]} checks')
        if server['running_task_n_checks'] >= stuck_n_checks and 'server_stuck' not in server['suppress_alerts']:
            send_alert(f'{server["friendly_name"]} SERVER APPEARS STUCK running for last {server["last_task_n_checks"]} checks')
 
    print(f'now sleeping for {delay}s')
    time.sleep(delay)    
