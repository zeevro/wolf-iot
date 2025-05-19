from dataclasses import dataclass, field
import pathlib
import secrets
from typing import TYPE_CHECKING

import appdirs
import msgspec


if TYPE_CHECKING:
    from flask import Flask


# CONFIG_PATH = pathlib.Path(appdirs.site_config_dir('wolf_iot', False), 'config.toml')
# CONFIG_PATH = pathlib.Path(appdirs.user_config_dir('wolf_iot', False), 'config.toml')
CONFIG_PATH = pathlib.Path(__file__).parents[2] / 'tests' / 'config.toml'


# @dataclass(kw_only=True)
class Config(msgspec.Struct, kw_only=True, rename='lower'):
    SECRET_KEY: str = msgspec.field(default_factory=secrets.token_urlsafe)
    TOKEN_EXPIRE_DURATION: int = 24 * 60 * 60
    CLIENT_ID: str = msgspec.field(default_factory=secrets.token_urlsafe)
    CLIENT_SECRET: str = msgspec.field(default_factory=secrets.token_urlsafe)
    AUTHORIZATION_CODE: str = msgspec.field(default_factory=secrets.token_urlsafe)
    REFRESH_TOKEN: str = msgspec.field(default_factory=secrets.token_urlsafe)


def init_config(app: 'Flask') -> None:
    if CONFIG_PATH.exists():
        conf = msgspec.toml.decode(CONFIG_PATH.read_bytes(), type=Config)
    else:
        conf = Config()
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_bytes(msgspec.toml.encode(conf))

    app.config.from_object(conf)
