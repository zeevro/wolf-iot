import json
import os
import sys

import appdirs
import requests
from flask import jsonify, request

from wolf_iot.oauth2 import auth_required


DEVICES_PATH = os.path.join(appdirs.site_config_dir('wolf_iot', False), 'devices.json')


intent_handlers = {}


def register_intent_handler(intent, handler_func):
    intent_handlers[intent] = handler_func


def intent_handler(intent):
    def register(handler_func):
        register_intent_handler(intent, handler_func)
        return handler_func
    return register


@intent_handler('action.devices.SYNC')
def handle_sync_intent(payload):
    return {
        'agentUserId': '1',
        'devices': devices_data_for_query,
    }


@intent_handler('action.devices.QUERY')
def handle_query_intent(payload):
    ret = {}
    for device in payload['devices']:
        device_id = device['id']

        if device_id in ret:
            continue

        try:
            state = requests.get(device_urls[device_id], timeout=0.5).json()
            ret[device_id] = dict(
                online=True,
                status='SUCCESS',
                **state,
            )
        except Exception as e:
            print('ERROR! {}: {}'.format(e.__class__.__name__, e), file=sys.stderr)
            ret[device_id] = dict(
                online=False,
                status='ERROR',
            )

    return {'devices': ret}


@intent_handler('action.devices.EXECUTE')
def handle_execute_intent(payload):
    ret = []
    success = set()
    error = set()
    for command in payload['commands']:
        device_ids = [device['id'] for device in command['devices']]
        for execution in command['execution']:
            for device_id in device_ids:
                try:
                    requests.post(device_urls[device_id], json=execution['params'], timeout=0.5)
                    success.add(device_id)
                except Exception as e:
                    print('ERROR! {}: {}'.format(e.__class__.__name__, e), file=sys.stderr)
                    error.add(device_id)

    if success:
        ret.append(dict(
            ids=list(success),
            status='SUCCESS',
        ))

    if error:
        ret.append(dict(
            ids=list(error),
            status='ERROR',
        ))

    return {'commands': ret}


@intent_handler('action.devices.DISCONNECT')
def handle_disconnect_intent(payload):
    pass


@auth_required
def fulfillment_endpoint():
    req = request.json
    resp_payload = {}

    print(json.dumps(req, indent=2), file=sys.stderr)

    for input_data in req['inputs']:
        handler = intent_handlers.get(input_data['intent'], None)
        if handler is None:
            continue
        payload = input_data.get('payload', None)
        resp_payload.update(handler(payload))

    print(json.dumps(resp_payload, indent=2), file=sys.stderr)

    if not resp_payload:
        return jsonify()

    return jsonify(
        requestId=req['requestId'],
        payload=resp_payload,
    )


device_urls = {}
devices_data_for_query = []


def init_fulfillment(app, fulfillment_endpoint_rule='/api/fulfillment/'):
    app.add_url_rule(fulfillment_endpoint_rule, 'fulfillment_endpoint', fulfillment_endpoint, methods=['POST'])

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
                "url": "http://192.168.1.153/"
            }
        ]
        with open(DEVICES_PATH, 'w') as f:
            json.dump(devices_config, f, indent=4)

    for dev in devices_config:
        device_urls[dev['id']] = dev.pop('url')
        devices_data_for_query.append(dev)
