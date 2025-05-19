from collections.abc import Callable
import json
import sys
from typing import Any

from flask import Flask, Response, jsonify, request

from wolf_iot.devices import AnyDevice, generate_devices_from_config
from wolf_iot.oauth2 import auth_required


intent_handlers = {}


type IntentHandler[Req: dict[str, Any], Resp: dict[str, Any] | None] = Callable[[Req], Resp]


def intent_handler[F: IntentHandler](intent: str) -> Callable[[F], F]:
    def register(handler_func: F) -> F:
        intent_handlers[intent] = handler_func
        return handler_func

    return register


@intent_handler('action.devices.SYNC')
def handle_sync_intent(_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        'agentUserId': '1',
        'devices': devices_data_for_query,
    }


@intent_handler('action.devices.QUERY')
def handle_query_intent(payload: dict[str, Any]) -> dict[str, Any]:
    ret = {}
    for device_data in payload['devices']:
        device_id = device_data['id']
        device = devices[device_id]

        if device_id in ret:
            continue

        try:
            ret[device_id] = device.query()
            ret[device_id].setdefault('online', True)
            ret[device_id].setdefault('status', 'SUCCESS')
        except Exception as e:
            print(f'ERROR! {e.__class__.__name__}: {e}', file=sys.stderr)
            ret[device_id] = {
                'online': False,
                'status': 'ERROR',
            }

    return {'devices': ret}


@intent_handler('action.devices.EXECUTE')
def handle_execute_intent(payload: dict[str, Any]) -> dict[str, Any]:
    ret = []
    success = set()
    error = set()
    for command in payload['commands']:
        device_ids = [device['id'] for device in command['devices']]
        for execution in command['execution']:
            for device_id in device_ids:
                device = devices[device_id]
                try:
                    device.execute(execution)
                    success.add(device_id)
                except Exception as e:
                    print(f'ERROR! {e.__class__.__name__}: {e}', file=sys.stderr)
                    error.add(device_id)

    if success:
        ret.append(
            {
                'ids': list(success),
                'status': 'SUCCESS',
            }
        )

    if error:
        ret.append(
            {
                'ids': list(error),
                'status': 'ERROR',
            }
        )

    return {'commands': ret}


@intent_handler('action.devices.DISCONNECT')
def handle_disconnect_intent(_payload: dict[str, Any]) -> None:
    pass


@auth_required
def fulfillment_endpoint() -> Response:
    req = request.json
    resp_payload = {}

    print(json.dumps(req), file=sys.stderr)

    for input_data in req['inputs']:
        handler = intent_handlers.get(input_data['intent'], None)
        if handler is None:
            continue
        payload = input_data.get('payload', None)
        resp_payload.update(handler(payload))

    print(json.dumps(resp_payload), file=sys.stderr)

    if not resp_payload:
        return jsonify()

    return jsonify(
        requestId=req['requestId'],
        payload=resp_payload,
    )


devices: dict[str, AnyDevice] = {}
devices_data_for_query: list[dict[str, Any]] = []


def init_fulfillment(app: Flask, fulfillment_endpoint_rule: str = '/api/fulfillment/') -> None:
    app.add_url_rule(fulfillment_endpoint_rule, 'fulfillment_endpoint', fulfillment_endpoint, methods=['POST'])

    for device in generate_devices_from_config():
        devices[device.id] = device
        devices_data_for_query.append(device.description)
