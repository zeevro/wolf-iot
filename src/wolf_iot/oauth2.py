import base64
from collections.abc import Callable
import functools
import hmac
import json
import secrets
import sys
import time
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from flask import Flask, Response, abort, current_app, jsonify, render_template_string, request


AUTH_HTML_TEMPLATE = """<html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/purecss@2.0.1/build/pure-min.css">
        <title>{% if 'error' in redirect_query %}Authorization Error{% else %}Authorize Access{% endif %}</title>
        <style>
            .center {
                text-align: center;
            }
        </style>
    </head>
    <body>
        <div class="center">
            {% if error %}
                <h1>An error has occured.</h1>
                {{ error|replace('_', ' ')|capitalize }}
                <br>
                <a href="{{ redirect_url|add_url_args(error=error)|safe }}" class="pure-button pure-button-primary">OK</a>
            {% else %}
                <h1>Would you like to authorize access?</h1>
                <a href="{{ redirect_url|add_url_args(code=response_code)|safe }}" class="pure-button pure-button-primary">YES</a>
                <a href="{{ redirect_url|add_url_args(error='access_denied')|safe }}" class="pure-button">NO</a>
            {% endif %}
            <br><br>
            <small>
                Redirect URL:
                <code>{{ redirect_url }}</code>
            </small>
        </div>
    </body>
</html>"""


class AuthError(Exception):
    pass


# TODO: Maybe use PyJWT instead?
class TokenProvider:
    def __init__(self, secret: bytes | str, digest: str = 'sha256') -> None:  # TODO: Literal for digest?
        self._secret = secret if isinstance(secret, bytes) else secret.encode()
        self._digest = digest

    def _hmac(self, data: bytes) -> bytes:
        return hmac.digest(self._secret, data, self._digest)

    @staticmethod
    def b64encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b'=').decode()

    @staticmethod
    def b64decode(data: str) -> bytes:
        return base64.urlsafe_b64decode(f'{data}===')

    @staticmethod
    def generate_token(**kw: Any) -> dict[str, Any]:
        return {
            'nonce': secrets.token_urlsafe(),
            'expires_at': int(time.time()) + current_app.config['token_expire_duration'],
            **kw,
        }

    def encode_token(self, token: dict[str, Any]) -> str:
        token_json = json.dumps(token, separators=(',', ':')).encode()
        return f'{self.b64encode(token_json)}.{self.b64encode(self._hmac(token_json))}'

    def decode_token(self, data: str, verify: bool = True) -> dict[str, Any]:
        token_raw, signature = map(self.b64decode, data.split('.', 1))
        if verify and signature != self._hmac(token_raw):
            raise AuthError('Invalid token')
        token = json.loads(token_raw)
        if verify and time.time() >= token['expires_at']:
            raise AuthError('Token expired')
        return token


def json_error(error: str, status_code: int = 400) -> Response:
    print('JSON ERROR!', error, status_code, file=sys.stderr)
    return jsonify(status=status_code, error=error)


def get_token_provider() -> TokenProvider:
    return TokenProvider(current_app.secret_key)


def authenticate_request() -> dict[str, Any] | None:
    auth_hdr = request.headers.get('Authorization', '')
    if not auth_hdr:
        return None

    auth_type, auth_data = auth_hdr.split(None, 1)

    if auth_type != 'Bearer':
        return None

    return get_token_provider().decode_token(auth_data)


def auth_required[**P, R](f: Callable[P, R]) -> Callable[P, R]:
    @functools.wraps(f)
    def require_auth(*a: P.args, **kw: P.kwargs) -> R:
        if not authenticate_request():
            return abort(401)
        return f(*a, **kw)

    return require_auth


def create_token_response() -> Response:
    token_provider = get_token_provider()

    token = token_provider.generate_token()

    return jsonify(
        access_token=token_provider.encode_token(token),
        token_type='Bearer',  # noqa: S106
        expires_in=current_app.config['token_expire_duration'],
        refresh_token=current_app.config['refresh_token'],
    )


def add_url_args(url: str, **kwargs: str) -> str:
    parts = list(urlparse(url))
    query = dict(parse_qsl(parts[4]))
    query.update(kwargs)
    parts[4] = urlencode(query)
    return urlunparse(parts)


def authorize_endpoint() -> str:
    redirect_url = request.args['redirect_uri']
    if 'state' in request.args:
        redirect_url = add_url_args(redirect_url, state=request.args['state'])

    if request.args['client_id'] != current_app.config['client_id']:
        error = 'unauthorized_client'
    elif request.args['response_type'] != 'code':
        error = 'unsupported_response_type'
    else:
        error = ''

    response_code = '' if error else current_app.config['authorization_code']

    return render_template_string(AUTH_HTML_TEMPLATE, redirect_url=redirect_url, error=error, response_code=response_code)


def token_endpoint() -> Response:
    print(request.headers, file=sys.stderr)
    print(request.form, file=sys.stderr)
    # TODO: (As per https://tools.ietf.org/html/rfc6749#section-4.1.3)
    #   o Ensure "redirect_uri" is present and identical to one in authorization request

    if {'grant_type', 'client_id', 'client_secret'}.difference(request.form):
        return json_error('invalid_request')

    if (request.form['client_id'] != current_app.config['client_id']) or (request.form['client_secret'] != current_app.config['client_secret']):
        return json_error('invalid_client', 401)

    grant_type = request.form['grant_type']

    if grant_type == 'authorization_code':
        if 'code' not in request.form:
            return json_error('invalid_request')
        if request.form['code'] != current_app.config['authorization_code']:
            return json_error('invalid_grant')
    elif grant_type == 'refresh_token':
        if 'refresh_token' not in request.form:
            return json_error('invalid_request')
        if request.form['refresh_token'] != current_app.config['refresh_token']:
            return json_error('invalid_grant')
    else:
        return json_error('unsupported_grant_type')

    return create_token_response()


def init_oauth2(app: Flask, authorize_endpoint_rule: str = '/oauth/authorize/', token_endpoint_rule: str = '/oauth/token/') -> None:  # noqa: S107
    app.add_url_rule(authorize_endpoint_rule, 'authorize_endpoint', authorize_endpoint)
    app.add_url_rule(token_endpoint_rule, 'token_endpoint', token_endpoint, methods=['POST'])
    app.add_template_filter(add_url_args, 'add_url_args')
