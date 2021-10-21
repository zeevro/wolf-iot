import queue
import urllib.parse

from paho.mqtt.client import Client as MQTTClient


def parse_mqtt_url(url):
    parts = urllib.parse.urlparse(url)

    return parts.path.split('/', 2)[1], parts.hostname, parts.port or 1883, parts.username, parts.password


def mqtt_cmnd(topic, payload=None, resp_topic=None, host=None, port=1883, username=None, password=None):
    resp_q = queue.Queue(1)

    c = MQTTClient(clean_session=True)
    if username is not None:
        c.username_pw_set(username, password)
    c.connect(host, port)
    c.subscribe(resp_topic or topic)
    c.on_message = lambda client, userdata, msg: resp_q.put(msg.payload)
    c.publish(topic, payload)
    c.loop_start()
    try:
        return resp_q.get(timeout=1)
    except queue.Empty:
        raise TimeoutError from None
    finally:
        c.loop_stop()
