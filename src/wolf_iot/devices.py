import os
import posixpath

import appdirs
import requests

from .utils import parse_mqtt_url, mqtt_cmnd

try:
    import commentjson as json
except ImportError:
    import json


DEVICES_PATH = os.path.join(appdirs.site_config_dir('wolf_iot', False), 'devices.json')


class BaseDevice:
    def __init__(self, device_id, description):
        self.id = device_id
        self.__dict__.update(description)


class WolfIoTDevice(BaseDevice):
    def query(self):
        return requests.get(self.url, timeout=0.5).json()

    def execute(self, data):
        requests.post(self.url, json=data['params'], timeout=0.5)


class TasmotaDevice(BaseDevice):
    _commands = {
        'on': 'Power',
        'brightness': 'Dimmer',
    }

    def _cmnd(self, cmnd):
        if self.url.startswith('http://'):
            return requests.get(posixpath.join(self.url, 'cm'), {'cmnd': cmnd}, timeout=1).json()

        if self.url.startswith('mqtt://'):
            device_name, host, port, username, password = parse_mqtt_url(self.url)

            try:
                cmnd, payload = cmnd.split(None, 1)
            except ValueError:
                payload = None

            return json.loads(mqtt_cmnd(f'cmnd/{device_name}/{cmnd}', payload, f'stat/{device_name}/RESULT', host, port, username, password))

    @staticmethod
    def _translate_state(state):
        on_key = 'POWER' if 'POWER' in state else 'POWER1'
        ret = {'on': str(state[on_key]).lower() in ('on', 'true', '1')}
        if 'Dimmer' in state:
            ret['brightness'] = state['Dimmer']
        return ret

    def query(self):
        return self._translate_state(self._cmnd('state'))

    def execute(self, data):
        for k, v in data['params'].items():
            if k in self._commands:
                self._cmnd(f'{self._commands[k]} {v}')
                break


class TasmotaFanDevice(TasmotaDevice):
    _fan_speeds_query = [
        'high_speed',
        'low_speed',
        'medium_speed',
        'high_speed'
    ]

    _fan_speeds_command = {
        'low_speed': 1,
        'medium_speed': 2,
        'high_speed': 3
    }

    @classmethod
    def _translate_state(cls, state):
        speed = state['FanSpeed']
        return {
            'on': bool(speed),
            'fanspeed': cls._fan_speeds_query[speed],
        }

    def execute(self, data):
        params = data['params']
        if 'on' in params:
            self._cmnd(f"POWER2 {params['on']}")
        elif 'fanSpeed' in params:
            self._cmnd(f"FanSpeed {self._fan_speeds_command[params['fanSpeed']]}")


def generate_devices_from_config():
    try:
        with open(DEVICES_PATH) as f:
            devices_config = json.load(f)
    except FileNotFoundError:
        os.makedirs(os.path.dirname(DEVICES_PATH), exist_ok=True)
        devices_config = [
            {
                "id": "1",
                "type": "action.devices.types.LIGHT",
                "traits": [
                    "action.devices.traits.OnOff",
                    "action.devices.traits.Brightness"
                ],
                "name": {
                    "name": "Dimmable light example"
                },
                "willReportState": False,
                "roomHint": "Bedroom",
                "@wolf": {
                    "@type": "WolfIoT",
                    "url": "http://10.0.0.51/"
                }
            }
        ]
        with open(DEVICES_PATH, 'w') as f:
            json.dump(devices_config, f, indent=4)

    ret = []

    for dev in devices_config:
        dev_id = dev['id']
        params = dev.pop('@wolf')
        cls = f"{params.pop('@type')}Device"
        ret.append((dev_id, globals().get(cls)(dev_id, params), dev))

    return ret
