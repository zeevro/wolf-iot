import json
import sys

import requests
from flask import jsonify, request

from wolf_iot.oauth2 import auth_required


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
        'devices': [
            {
                'id': '1',
                'type': 'action.devices.types.LIGHT',
                'traits': [
                    'action.devices.traits.OnOff',
                    'action.devices.traits.Brightness',
                ],
                'name': {
                    'name': 'Night light',
                },
                'willReportState': False,
                'roomHint': 'Bedroom',
            },
        ],
    }


@intent_handler('action.devices.QUERY')
def handle_query_intent(payload):
    ret = {}
    for device in payload['devices']:
        device_id = device['id']

        if device_id in ret:
            continue

        try:
            state = requests.get(my_devices[device_id]['url'], timeout=0.5).json()
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
                    requests.post(my_devices[device_id]['url'], json=execution['params'], timeout=0.5)
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


my_devices = {
    '1': {
        'url': 'http://10.0.0.51/',
    },
}


def init_fulfillment(app, fulfillment_endpoint_rule='/api/fulfillment/'):
    app.add_url_rule(fulfillment_endpoint_rule, 'fulfillment_endpoint', fulfillment_endpoint, methods=['POST'])
