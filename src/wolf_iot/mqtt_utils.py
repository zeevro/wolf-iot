from dataclasses import dataclass
import queue
from typing import Self
import urllib.parse

from paho.mqtt.client import Client


@dataclass(frozen=True)
class MqttBrokerParams:
    host: str = 'localhost'
    port: int = 1883
    username: str | None = None
    password: str | None = None

    @classmethod
    def parse_url(cls, url: str) -> tuple[Self, str]:
        parts = urllib.parse.urlparse(url)
        return cls(parts.hostname or 'localhost', parts.port or 1883, parts.username, parts.password), parts.path.split('/', 2)[1]

    def cmnd(self, device_name: str, cmnd: str, payload: str | None = None) -> bytes:
        resp_q = queue.Queue[bytes](1)
        c = Client(clean_session=True)
        if self.username is not None:
            c.username_pw_set(self.username, self.password)
        c.connect(self.host, self.port)
        c.subscribe(f'stat/{device_name}/RESULT')
        c.on_message = lambda _client, _userdata, msg: resp_q.put(msg.payload)
        c.publish(f'cmnd/{device_name}/{cmnd}', payload)
        c.loop_start()
        try:
            return resp_q.get(timeout=1)
        except queue.Empty:
            raise TimeoutError from None
        finally:
            c.loop_stop()
