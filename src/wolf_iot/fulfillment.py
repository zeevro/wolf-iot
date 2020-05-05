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
    pass


@intent_handler('action.devices.QUERY')
def handle_query_intent(payload):
    pass


@intent_handler('action.devices.EXECUTE')
def handle_execute_intent(payload):
    pass


@intent_handler('action.devices.DISCONNECT')
def handle_disconnect_intent(payload):
    pass
