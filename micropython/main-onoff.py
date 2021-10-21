import uasyncio
import ujson
from machine import Pin

import picoweb


button = Pin(13, Pin.IN, Pin.PULL_UP)

out = Pin(5, Pin.OUT)


state = {
    'on': False,
}


async def handle_button():
    while 1:
        while button():
            await uasyncio.sleep_ms(20)

        print('click: old state:', state)

        state['on'] = not state['on']
        out(state['on'])

        print('click: new state:', state)

        while not button():
            await uasyncio.sleep_ms(20)


uasyncio.get_event_loop().create_task(handle_button())


app = picoweb.WebApp(__name__)

@app.route("/")
def index(req, resp):
    try:
        if req.method == 'GET':
            yield from picoweb.jsonify(resp, state)
            return

        if req.method != 'POST':
            yield from picoweb.start_response(resp, status='406')
            yield from resp.awrite('Method not allowed')
            return

        if req.headers[b'Content-Type'] != b'application/json':
            yield from picoweb.start_response(resp, status='400')
            yield from resp.awrite('Bad request')
            return

        size = int(req.headers[b'Content-Length'])
        raw_data = yield from req.reader.readexactly(size)
        data = ujson.loads(raw_data)

        print('HTTP: request:', data)
        print('HTTP: old state:', state)

        state.update(data)

        out(state['on'])

        print('HTTP: new state:', state)

        yield from picoweb.jsonify(resp, state)
    except Exception as e:
        print('ERROR! {}: {}'.format(e.__class__.__name__, e))


app.run('0.0.0.0', 80, debug=-1)
