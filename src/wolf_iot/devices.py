import json
import os
import posixpath

import appdirs
import requests

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
        return requests.get(posixpath.join(self.url, 'cm'), {'cmnd': cmnd}, timeout=0.5).json()

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
