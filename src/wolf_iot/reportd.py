import argparse
import json
import os
import sys
import time
from typing import Any
import uuid

from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account
from paho.mqtt.client import Client, MQTTMessage

from wolf_iot.devices import TasmotaDevice, generate_devices_from_config
from wolf_iot.mqtt_utils import MqttBrokerParams


def log(*a: Any) -> None:
    print(*a, file=sys.stdout)
    sys.stdout.flush()


class Reporter:
    def __init__(self, google_session: AuthorizedSession) -> None:
        self._sess = google_session
        self._state: dict[str, dict[str, Any]] = {}

    def on_msg(self, _client: Client, userdata: dict[str, list[TasmotaDevice]], msg: MQTTMessage) -> None:
        device_name = msg.topic[5:-7]
        devices = userdata[device_name]
        data: dict[str, Any] = json.loads(msg.payload)
        to_report: dict[str, dict[str, Any]] = {}
        for device in devices:
            try:
                new_state = device.translate_state(data)
            except Exception as e:
                log(f'ERROR in {type(device).__name__}.translate_state({data!r})! {type(e).__name__}: {e}')
                continue
            if new_state == self._state.get(device.id):
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
            'payload': {'devices': {'states': to_report}},
        }
        log(json.dumps(req))
        resp = self._sess.post('https://homegraph.googleapis.com/v1/devices:reportStateAndNotification', json=req)
        log(resp, resp.json())


def get_google_session(account_json_path: bytes | str | os.PathLike) -> AuthorizedSession:
    credentials = service_account.Credentials.from_service_account_file(account_json_path)
    scoped_credentials = credentials.with_scopes(['https://www.googleapis.com/auth/homegraph'])
    return AuthorizedSession(scoped_credentials)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('-a', '--account-path', help='Path to JSON file containing Google account details')
    args = p.parse_args()

    google_session = get_google_session(args.account_path)

    brokers: dict[MqttBrokerParams, dict[str, list[TasmotaDevice]]] = {}
    clients: list[Client] = []

    reporter = Reporter(google_session)

    for device in generate_devices_from_config():
        if not (isinstance(device, TasmotaDevice) and device.url.startswith('mqtt://')):
            continue
        broker, device_name = MqttBrokerParams.parse_url(device.url)
        brokers.setdefault(broker, {}).setdefault(device_name, []).append(device)

    for broker, devices in brokers.items():
        client = Client(clean_session=True, userdata=devices)
        client.on_message = reporter.on_msg
        if broker.username is not None:
            client.username_pw_set(broker.username, broker.password)
        client.connect(broker.host, broker.port)

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


if __name__ == '__main__':
    main()
