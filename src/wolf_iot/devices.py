import pathlib
import posixpath
from typing import Any, ClassVar, cast

import appdirs
import msgspec
import requests

from wolf_iot.mqtt_utils import MqttBrokerParams


try:
    import commentjson as json
except ImportError:
    import json


# TODO: Replace "dict[str, Any]" with TypedDict/dataclass/msgspec.Struct/pydantic/etc.


# DEVICES_PATH = pathlib.Path(appdirs.site_config_dir('wolf_iot', False), 'devices.toml')
# DEVICES_PATH = pathlib.Path(appdirs.user_config_dir('wolf_iot', False), 'devices.toml')
DEVICES_PATH = pathlib.Path(__file__).parents[2] / 'tests' / 'devices.toml'

class BaseDevice:
    device_types: ClassVar[dict[str, type['AnyDevice']]] = {}

    url: str

    def __init__(self, device_id: str, params: dict[str, Any], description: dict[str, Any]) -> None:
        self.id = device_id
        self.description = description
        self._params = params
        self.__dict__.update(params)  # TODO: Eradicate!! Exterminate!!!

    def __init_subclass__(cls) -> None:
        cls.device_types[cls.__name__] = cast('type[AnyDevice]', cls)

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> 'AnyDevice':
        desc = config.copy()
        params = desc.pop('@wolf')
        typ = cls.device_types[f'{params.pop("@type")}Device']
        return typ(desc['id'], params, desc)

    def query(self) -> dict[str, Any]:
        raise NotImplementedError

    def execute(self, data: dict[str, Any]) -> None:
        raise NotImplementedError


class WolfIoTDevice(BaseDevice):
    def query(self) -> dict[str, Any]:
        return requests.get(self.url, timeout=0.5).json()

    def execute(self, data: dict[str, Any]) -> None:
        requests.post(self.url, json=data['params'], timeout=0.5)


class TasmotaDevice(BaseDevice):
    _commands: ClassVar[dict[str, str]] = {
        'on': 'Power',
        'brightness': 'Dimmer',
    }

    def _cmnd(self, cmnd: str) -> dict[str, Any]:
        if self.url.startswith('http://'):
            return requests.get(posixpath.join(self.url, 'cm'), {'cmnd': cmnd}, timeout=1).json()

        if self.url.startswith('mqtt://'):
            broker, device_name = MqttBrokerParams.parse_url(self.url)

            try:
                cmnd, payload = cmnd.split(None, 1)
            except ValueError:
                payload = None

            return json.loads(broker.cmnd(device_name, cmnd, payload))

        raise ValueError(f'Unsupported URL: {self.url!r}')

    @classmethod
    def translate_state(cls, state: dict[str, Any]) -> dict[str, Any]:
        on_key = 'POWER' if 'POWER' in state else 'POWER1'
        ret = {'on': str(state[on_key]).lower() in ('on', 'true', '1')}
        if 'Dimmer' in state:
            ret['brightness'] = state['Dimmer']
        return ret

    def query(self) -> dict[str, Any]:
        return self.translate_state(self._cmnd('state'))

    def execute(self, data: dict[str, Any]) -> None:
        for k, v in data['params'].items():
            if k in self._commands:
                self._cmnd(f'{self._commands[k]} {v}')
                break


class TasmotaFanDevice(TasmotaDevice):
    _fan_speeds_query: ClassVar[tuple[str, str, str, str]] = ('high_speed', 'low_speed', 'medium_speed', 'high_speed')
    _fan_speeds_command: ClassVar[dict[str, int]] = {'low_speed': 1, 'medium_speed': 2, 'high_speed': 3}

    @classmethod
    def translate_state(cls, state: dict[str, Any]) -> dict[str, Any]:
        speed = state['FanSpeed']
        return {
            'on': bool(speed),
            'currentFanSpeedSetting': cls._fan_speeds_query[speed],
        }

    def execute(self, data: dict[str, Any]) -> None:
        params = data['params']
        if 'on' in params:
            self._cmnd(f'POWER2 {params["on"]}')
        elif 'fanSpeed' in params:
            self._cmnd(f'FanSpeed {self._fan_speeds_command[params["fanSpeed"]]}')


AnyDevice = WolfIoTDevice | TasmotaDevice | TasmotaFanDevice


def generate_devices_from_config() -> list[AnyDevice]:
    if DEVICES_PATH.exists():
        devices = msgspec.toml.decode(DEVICES_PATH.read_bytes())['devices']
    else:
        devices = [
            {
                'id': '1',
                'type': 'action.devices.types.LIGHT',
                'traits': ['action.devices.traits.OnOff', 'action.devices.traits.Brightness'],
                'name': {'name': 'Dimmable light example'},
                'willReportState': False,
                'roomHint': 'Bedroom',
                '@wolf': {'@type': 'WolfIoT', 'url': 'http://10.0.0.51/'},
            }
        ]
        DEVICES_PATH.parent.mkdir(parents=True, exist_ok=True)
        DEVICES_PATH.write_bytes(msgspec.toml.encode({'devices': devices}))

    return [BaseDevice.from_config(dev_conf) for dev_conf in devices]
