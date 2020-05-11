import json
import os
import secrets


CONFIG_PATH = 'config.json'


def init_config(app):
    try:
        app.config.from_json(CONFIG_PATH)
    except FileNotFoundError:
        config = {
            'SECRET_KEY': secrets.token_urlsafe(),
            'TOKEN_EXPIRE_DURATION': 24 * 60 * 60,
            'CLIENT_ID': secrets.token_urlsafe(),
            'CLIENT_SECRET': secrets.token_urlsafe(),
            'AUTHORIZATION_CODE': secrets.token_urlsafe(),
            'REFRESH_TOKEN': secrets.token_urlsafe(),
        }
        with open(os.path.join(app.config.root_path, CONFIG_PATH), 'w') as f:
            json.dump(config, f, indent=4)
        app.config.from_mapping(config)
