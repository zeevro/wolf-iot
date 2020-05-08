import argparse

import requests


def main():
    p = argparse.ArgumentParser(conflict_handler='resolve')
    p.add_argument('-h', '--host')
    p.add_argument('-o', '--on', type=lambda s: s.lower() == 'on')
    p.add_argument('-b', '--brightness', type=int)
    args = p.parse_args()

    data = {}
    if args.on is not None:
        data['on'] = args.on
    if args.brightness is not None:
        data['brightness'] = args.brightness

    url = f'http://{args.host}/'

    try:
        print(requests.request('POST' if data else 'GET', url, json=data or None).json())
    except Exception as e:
        print('ERROR! {}: {}'.format(e.__class__.__name__, e))


if __name__ == "__main__":
    main()
