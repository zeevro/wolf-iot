import json


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

        ret[device_id] = dict(
            online=True,
            status='SUCCESS',
            **my_devices[device_id],
        )

    return {'devices': ret}


@intent_handler('action.devices.EXECUTE')
def handle_execute_intent(payload):
    # print(json.dumps(payload, indent=2))
    ret = []
    for command in payload['commands']:
        device_ids = [device['id'] for device in command['devices']]
        device_states = {}
        for execution in command['execution']:
            device_states.update(execution['params'])
            for device_id in device_ids:
                my_devices[device_id].update(execution['params'])

        ret.append({
            'ids': device_ids,
            'status': 'SUCCESS',
            'states' : device_states,
        })

    print(json.dumps(my_devices, indent=2))

    return {'commands': ret}


@intent_handler('action.devices.DISCONNECT')
def handle_disconnect_intent(payload):
    pass


my_devices = {
    '1': {
        'on': False,
        'brightness': 100,
    },
}
