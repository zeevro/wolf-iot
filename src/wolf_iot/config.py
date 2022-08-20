import json
import os
import secrets

import appdirs


CONFIG_PATH = os.path.join(appdirs.site_config_dir('wolf_iot', False), 'config.json')


def init_config(app):
    try:
        app.config.from_file(CONFIG_PATH, load=json.load)
    except FileNotFoundError:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        config = {
            'SECRET_KEY': secrets.token_urlsafe(),
            'TOKEN_EXPIRE_DURATION': 24 * 60 * 60,
            'CLIENT_ID': secrets.token_urlsafe(),
            'CLIENT_SECRET': secrets.token_urlsafe(),
            'AUTHORIZATION_CODE': secrets.token_urlsafe(),
            'REFRESH_TOKEN': secrets.token_urlsafe(),
        }
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=4)
        app.config.from_mapping(config)
