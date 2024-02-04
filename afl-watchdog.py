import logging
logging.basicConfig(level=logging.ERROR)

import time

import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

import datetime
import json

config = json.load(open(os.path.expanduser('~/.afl/watchdog-config.json'),'r'))
slack_token = config['slack_token']
slack_channel = config['slack_channel'] 
slack_shutoff_msg = config['slack_shutoff_msg']
try:
    afl_system_serial = os.environ['AFL_SYSTEM_SERIAL']
except KeyError:
    afl_system_serial = config['afl_system_serial']
stuck_n_checks = config['stuck_n_checks']
idle_n_checks = config['idle_n_checks']
servers = config['servers']
delay = config['delay']
image_endpoints = config['image_endpoints']
upload_endpoint = config['upload_endpoint']


# Create a SlackClient
client = WebClient(token=slack_token)


from AFL.automation.APIServer.Client import Client


def send_alert(text):
    '''
    Send a message to the slack channel, if not muted.
    '''
    alert_text = f"<!channel> {afl_system_serial}: {text}"
    if not is_muted():
        print(f'    --> Sent alert to Slack {alert_text}')
        response = client.chat_postMessage(channel=slack_channel,text=alert_text)
    else:
        print(f'    --> Muted, did not send alert to Slack {alert_text}')

def is_muted():
    '''
    check the slack channel for a message that says "SHUT UP"
     (or a more polite equivalent from config).
      If such a message exists, return True, else False.
    '''
    try:
        response = client.conversations_history(channel=slack_channel)
    except SlackApiError as e:
        print(f"Error: {e}")
        return False
    for message in response['messages']:
        if message['text'] == slack_shutoff_msg:
            return True
    return False

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
      'friendly_name': 'Test Server',
      'collect_status': True
    },
'''




while True:
    status_dict = {}
    status_dict['last_updated'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if len(image_endpoints)>0:
        status_dict['cameras'] = {}
        for camera,endpoint in image_endpoints.items():
            status_dict['cameras'][endpoint[0]] = camera
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
        if 'collect_status' not in server.keys():
            server['collect_status'] = True
        
        if server['collect_status']:
            status_dict[server['friendly_name']] = {}
            server_status = status_dict[server['friendly_name']]
        else:
            server_status = {}

        print(f'--> Performing check on {server["friendly_name"]}')

        c = Client(server['address'],port=server['port'])
            
        # check for server_down    
        try:
            c.login('WatchDog')
        except Exception:
            if 'server_down' not in server['suppress_alerts']:
                send_alert(f'{server["friendly_name"]}: SERVER UNREACHABLE')
                server_status['reachable'] = False
            continue
        server_status['reachable'] = True

        # check for server_paused
        state = c.queue_state().content.decode(encoding='utf-8')
        
        server_status['state'] = state
        server_status['errors'] = ''
        if state == 'Paused' and 'server_paused' not in server['suppress_alerts']:
            send_alert(f'{server["friendly_name"]}: SERVER PAUSED')
            server_status['errors'] += 'Server Paused | '
        queue = c.get_queue()
        
        server_status['queue'] = queue
        server_status['driver_status'] = c.driver_status()

        # check last task completion status
        if state == 'Paused' and 'server_paused_error' not in server['suppress_alerts']:
            if len(queue[1])>0:
                send_alert(f'{server["friendly_name"]}: SERVER PAUSED W/ RUNNING TASK (likely error)')
                server_status['errors'] += 'Server Paused w/ Running Task | '
 
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
            server_status['errors'] += 'Server Idle | '
        if server['running_task_n_checks'] >= stuck_n_checks and 'server_stuck' not in server['suppress_alerts']:
            send_alert(f'{server["friendly_name"]} SERVER APPEARS STUCK running for last {server["last_task_n_checks"]} checks')
            server_status['errors'] += 'Server Stuck | '
    json.dump(status_dict,open(os.path.expanduser('~/.afl/upload/status.json'),'w'))
    print(f'--> fetching images for status board')
    for fname,endpoint in image_endpoints.items():
        print(f'    --> getting {fname} from {endpoint}')
        os.system(f'wget -O ~/.afl/upload/{fname} {endpoint[1]}')
    if len(upload_endpoint)>0:
        print(f'--> performing SSH upload of status directory')
        os.system(f'rsync -avh ~/.afl/upload/* {upload_endpoint}')
    print(f'now sleeping for {delay}s')
    time.sleep(delay)    
