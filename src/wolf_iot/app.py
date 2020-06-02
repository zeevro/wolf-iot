from flask import Flask

from wolf_iot.config import init_config
from wolf_iot.fulfillment import init_fulfillment
from wolf_iot.oauth2 import init_oauth2


app = Flask(__name__)
app.url_map.strict_slashes = False

init_config(app)
init_fulfillment(app)
init_oauth2(app)


def main():
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument('-D', '--debug', action='store_true')
    p.add_argument('-c', '--cert-path')
    p.add_argument('-k', '--key-path')
    p.add_argument('-p', '--port', type=int, default=443)
    p.add_argument('-i', '--info', action='store_true')
    args = p.parse_args()

    if args.info:
        print('Client ID:     {}'.format(app.config['CLIENT_ID']))
        print('Client secret: {}'.format(app.config['CLIENT_SECRET']))
        return

    if None in (args.cert_path, args.key_path):
        p.error('the following arguments are required: -c/--cert-path, -k/--key-path')

    app.run(
        '0.0.0.0',
        args.port,
        ssl_context=(args.cert_path, args.key_path),
        debug=args.debug,
        use_reloader=True,
    )


if __name__ == '__main__':
    main()
