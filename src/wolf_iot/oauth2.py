import hmac
import functools
import json
import secrets
import time
from base64 import b64decode, b64encode

from flask import abort, current_app, jsonify, request


__all__ = [
    'TOKEN_EXPIRE_DURATION',
    'CLIENT_ID',
    'CLIENT_SECRET',
    'AUTHORIZATION_CODE',
    'AUTH_HTML_TEMPLATE',
    'AuthError',
    'json_error',
    'get_token_provider',
    'authenticate_request',
    'auth_required',
]


TOKEN_EXPIRE_DURATION = 3 * 24 * 60 * 60  # 3 days
CLIENT_ID = 'asdfqwer'
CLIENT_SECRET = 'asdfqwer'
AUTHORIZATION_CODE = 'very-very-long-authorization-code'


AUTH_HTML_TEMPLATE = '''<html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{% if 'error' in redirect_query %}Authorization Error{% else %}Authorize Access{% endif %}</title>
        <style>
            .center {
                text-align: center;
            }
        </style>
    </head>
    <body>
        <div class="center">
            {% if 'error' in redirect_query %}
                <h1>An error has occured.</h1>
                {{ redirect_query.error|replace('_', ' ')|capitalize }}
                <h3>Direct</h3>
                <a href="{{ redirect_url }}">OK</a>
                <h3>Redirection</h3>
                <a href="/oauth/auth-callback?action=error">OK</a>
            {% else %}
                <h1>Would you like to authorize access?</h1>
                <h3>Direct</h3>
                <a href="{{ redirect_url }}{{ redirect_query_joiner }}code={{ response_code }}">YES</a>
                <a href="{{ redirect_url }}{{ redirect_query_joiner }}error=access_denied">NO</a>
                <h3>Redirection</h3>
                <a href="/oauth/auth-callback?action=grant">YES</a>
                <a href="/oauth/auth-callback?action=deny">NO</a>
            {% endif %}
        </div>
    </body>
</html>'''


class AuthError(Exception):
    pass


class TokenProvider:
    def __init__(self, secret, digest='sha256'):
        self._secret = secret
        self._digest = digest

    def _hmac(self, data):
        return hmac.digest(self._secret, data, self._digest)

    @staticmethod
    def generate_token(**kw):
        return dict(
            nonce=secrets.token_urlsafe(),
            refresh_token=secrets.token_urlsafe(),
            expires_at=int(time.time()) + TOKEN_EXPIRE_DURATION,
            **kw,
        )

    def encode_token(self, token):
        token = json.dumps(token, separators=(',', ':')).encode()
        return b'.'.join(map(b64encode, [token, self._hmac(token)])).decode()

    def decode_token(self, data, verify=True):
        token, signature = map(b64decode, data.split('.', 1))
        if verify and signature != self._hmac(token):
            raise AuthError('Invalid token')
        token = json.loads(token)
        if verify and time.time() >= token['expires_at']:
            raise AuthError('Token expired')
        return token


def json_error(error, status_code=400):
    print('JSON ERROR!', error, status_code)
    resp = jsonify(error=error)
    resp.status_code = status_code
    return resp


def get_token_provider():
    return TokenProvider(current_app.secret_key)


def authenticate_request():
    # print(request.headers)

    auth_hdr = request.headers.get('Authorization', '')
    # print('auth_hdr', auth_hdr)
    if not auth_hdr:
        return

    auth_type, auth_data = auth_hdr.split(None, 1)
    # print('auth', auth_type, auth_data)

    if auth_type != 'Bearer':
        return

    return get_token_provider().decode_token(auth_data)


def auth_required(f):
    @functools.wraps(f)
    def wrapper(*a, **kw):
        if not authenticate_request:
            return abort(401)
        return f(*a, **kw)
    return wrapper


def create_token_response():
    token_provider = get_token_provider()

    token = token_provider.generate_token()

    return jsonify(
        access_token=token_provider.encode_token(token),
        token_type='Bearer',
        expires_in=TOKEN_EXPIRE_DURATION,
        refresh_token=token['refresh_token'],
    )
