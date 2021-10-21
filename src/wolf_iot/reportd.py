import argparse
import json
import sys
import time
import uuid

from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account
from paho.mqtt.client import Client

from .devices import generate_devices_from_config
from .utils import parse_mqtt_url


def log(*a):
    print(*a, file=sys.stdout)
    sys.stdout.flush()


class Reporter:
    def __init__(self, google_session):
        self._sess = google_session
        self._state = {}

    def report_state(self):
        pass

    def on_msg(self, client, userdata, msg):
        device_name = msg.topic[5:-7]
        devices = userdata[device_name]
        data = json.loads(msg.payload)
        to_report = {}
        for device in devices:
            try:
                new_state = device._translate_state(data)
            except Exception:
                continue
            if new_state == self._state.get(device.id, None):
                # log(f'no change for {device.id}')
                continue
            # log(f'{device.id}({device_name}#{device.__class__.__name__}): {new_state}')
            self._state.setdefault(device.id, {}).update(new_state)
            # log('<STATE>', self._state)
            to_report[device.id] = self._state[device.id]

        if not to_report:
            return

        req = {
            'agentUserId': '1',
            'requestId': str(uuid.uuid4()),
            'payload': {
                'devices': {
                    'states': to_report,
                },
            },
        }
        log(json.dumps(req, indent=2))
        resp = self._sess.post('https://homegraph.googleapis.com/v1/devices:reportStateAndNotification', json=req)
        log(resp, resp.json())


def get_google_session(account_json_path):
    credentials = service_account.Credentials.from_service_account_file(account_json_path)
    scoped_credentials = credentials.with_scopes(['https://www.googleapis.com/auth/homegraph'])
    sess = AuthorizedSession(scoped_credentials)

    return sess


def main():
    p = argparse.ArgumentParser()
    p.add_argument('-a', '--account-path', help='Path to JSON file containing Google account details')
    args = p.parse_args()

    google_session = get_google_session(args.account_path)

    brokers = {}
    clients = []

    reporter = Reporter(google_session)

    for device_id, device, desc in generate_devices_from_config():
        if not device.url.startswith('mqtt://'):
            continue
        device_name, host, port, username, password = parse_mqtt_url(device.url)
        broker = (host, port, username, password)
        brokers.setdefault(broker, {}).setdefault(device_name, []).append(device)

    for (host, port, username, password), devices in brokers.items():
        client = Client(clean_session=True, userdata=devices)
        client.on_message = reporter.on_msg
        if username is not None:
            client.username_pw_set(username, password)
        client.connect(host, port)

        for device_name in devices:
            # log(f'{device_name} --> STATE')
            client.subscribe(f'stat/{device_name}/RESULT')
            client.publish(f'cmnd/{device_name}/state')

        client.loop_start()
        clients.append(client)

    try:
        while 1:
            time.sleep(5)
    except KeyboardInterrupt:
        print('Ctrl-C')

    for client in clients:
        client.loop_stop()


if __name__ == "__main__":
    main()

