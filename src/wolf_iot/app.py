import json

from flask import Flask, request, jsonify

from wolf_iot.config import init_config
from wolf_iot.fulfillment import intent_handlers
from wolf_iot.oauth2 import auth_required, init_oauth2


app = Flask(__name__)
app.url_map.strict_slashes = False

init_config(app)

init_oauth2(app)


@app.route('/api/fulfillment/', methods=['POST'])
@auth_required
def api_fulfullment():
    req = request.json
    resp_payload = {}

    print(json.dumps(req, indent=2))

    for input_data in req['inputs']:
        handler = intent_handlers.get(input_data['intent'], None)
        if handler is None:
            continue
        payload = input_data.get('payload', None)
        resp_payload.update(handler(payload))

    print(json.dumps(resp_payload, indent=2))

    if not resp_payload:
        return jsonify()

    return jsonify(
        requestId=req['requestId'],
        payload=resp_payload,
    )


def main():
    app.run(
        '0.0.0.0',
        3459,
        ssl_context=(
            r'C:\Temp\Sec\home.zeevro.com\certificate.crt',
            r'C:\Temp\Sec\home.zeevro.com\private.key',
        ),
        debug=True,
        use_reloader=True,
    )


if __name__ == '__main__':
    main()
