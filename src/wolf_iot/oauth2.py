import base64
import hmac
import functools
import json
import secrets
import time
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from flask import abort, current_app, jsonify, request, render_template_string


AUTH_HTML_TEMPLATE = '''<html>
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
        </div>
    </body>
</html>'''


class AuthError(Exception):
    pass


class TokenProvider:
    def __init__(self, secret, digest='sha256'):
        self._secret = secret
        if not isinstance(self._secret, bytes):
            self._secret = str(self._secret).encode()
        self._digest = digest

    def _hmac(self, data):
        return hmac.digest(self._secret, data, self._digest)

    @staticmethod
    def b64encode(data):
        return base64.b64encode(data, altchars=b'-_').decode().rstrip('=')

    @staticmethod
    def b64decode(data):
        return base64.b64decode(data + (b'===' if isinstance(data, bytes) else '==='), altchars=b'-_')

    @staticmethod
    def generate_token(**kw):
        return dict(
            nonce=secrets.token_urlsafe(),
            expires_at=int(time.time()) + current_app.config['TOKEN_EXPIRE_DURATION'],
            **kw,
        )

    def encode_token(self, token):
        token = json.dumps(token, separators=(',', ':')).encode()
        return '.'.join(map(self.b64encode, [token, self._hmac(token)]))

    def decode_token(self, data, verify=True):
        token, signature = map(self.b64decode, data.split('.', 1))
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
    auth_hdr = request.headers.get('Authorization', '')
    if not auth_hdr:
        return

    auth_type, auth_data = auth_hdr.split(None, 1)

    if auth_type != 'Bearer':
        return

    return get_token_provider().decode_token(auth_data)


def auth_required(f):
    @functools.wraps(f)
    def wrapper(*a, **kw):
        if not authenticate_request():
            return abort(401)
        return f(*a, **kw)
    return wrapper


def create_token_response():
    token_provider = get_token_provider()

    token = token_provider.generate_token()

    return jsonify(
        access_token=token_provider.encode_token(token),
        token_type='Bearer',
        expires_in=current_app.config['TOKEN_EXPIRE_DURATION'],
        refresh_token=current_app.config['REFRESH_TOKEN'],
    )


def add_url_args(url, **args):
    parts = list(urlparse(url))
    query = dict(parse_qsl(parts[4]))
    query.update(args)
    parts[4] = urlencode(query)
    return urlunparse(parts)


def authorize_endpoint():
    redirect_url = request.args['redirect_uri']
    if 'state' in request.args:
        redirect_url = add_url_args(redirect_url, state=request.args['state'])

    error = None
    if request.args['client_id'] != current_app.config['CLIENT_ID']:
        error = 'unauthorized_client'
    elif request.args['response_type'] != 'code':
        error = 'unsupported_response_type'

    response_code = current_app.config['AUTHORIZATION_CODE']

    return render_template_string(AUTH_HTML_TEMPLATE, **locals())


def token_endpoint():
    print(request.headers)
    print(request.form)
    # TODO: (As per https://tools.ietf.org/html/rfc6749#section-4.1.3)
    #   o Ensure "redirect_uri" is present and identical to one in authorization request

    if {'grant_type', 'client_id', 'client_secret'}.difference(request.form):
        return json_error('invalid_request')

    if (request.form['client_id'] != current_app.config['CLIENT_ID']) or (request.form['client_secret'] != current_app.config['CLIENT_SECRET']):
        return json_error('invalid_client', 401)

    grant_type = request.form['grant_type']

    if grant_type == 'authorization_code':
        if 'code' not in request.form:
            return json_error('invalid_request')
        if request.form['code'] != current_app.config['AUTHORIZATION_CODE']:
            return json_error('invalid_grant')
    elif grant_type == 'refresh_token':
        if 'refresh_token' not in request.form:
            return json_error('invalid_request')
        if request.form['refresh_token'] != current_app.config['REFRESH_TOKEN']:
            return json_error('invalid_grant')
    else:
        return json_error('unsupported_grant_type')

    return create_token_response()


def init_oauth2(app, authorize_endpoint_rule='/oauth/authorize/', token_endpoint_rule='/oauth/token/'):
    app.add_url_rule(authorize_endpoint_rule, 'authorize_endpoint', authorize_endpoint)
    app.add_url_rule(token_endpoint_rule, 'token_endpoint', token_endpoint, methods=['POST'])
    app.add_template_filter(add_url_args, 'add_url_args')
