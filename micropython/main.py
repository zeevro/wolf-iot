import math
import uasyncio
import ujson
from machine import Pin, PWM, sleep

import picoweb


#presets = [0, 60, 380, 1024]
presets = [18, 50, 100]

button = Pin(13, Pin.IN, Pin.PULL_UP)

led_pwm = PWM(Pin(5))
led_pwm.freq(2000)


state = {
    'on': False,
    'brightness': 100,
}


def percent_to_duty(percent):
    b = 0.023
    a = 1024 / (math.exp(b * 100) - 1)
    return int(a * (math.exp(b * percent) - 1))


async def handle_button():
    while 1:
        while button():
            await uasyncio.sleep_ms(20)

        print('click: old state:', state)

        if not state['on']:
            percent = presets[0]
        else:
            for percent in presets:
                if percent > state['brightness']:
                    break
            else:
                percent = 0

        duty = percent and percent_to_duty(percent)
        led_pwm.duty(duty)

        state['on'] = bool(percent)
        state['brightness'] = percent

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

        if 'on' not in data:
            state['on'] = bool(data.get('brightness', 0))
        elif data['on'] and not state['brightness']:
            state['brightness'] = 100

        duty = percent_to_duty(state['brightness']) if state['on'] else 0

        led_pwm.duty(duty)

        print('HTTP: new state:', state)

        yield from picoweb.jsonify(resp, state)
    except Exception as e:
        print('ERROR! {}: {}'.format(e.__class__.__name__, e))


app.run('0.0.0.0', 80, debug=-1)
