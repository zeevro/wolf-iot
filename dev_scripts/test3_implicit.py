import hmac
import json
import secrets
import time
from base64 import b64decode, b64encode
from urllib.parse import parse_qsl, urlparse, urlunparse, urlencode

from flask import Flask, request, jsonify, render_template_string


app = Flask(__name__)
app.url_map.strict_slashes = False
app.secret_key = b'\x15\xe3\xdcsi\x1a\x9f\x13\xa1Y\xf4}z\t\xb4R\xf6~\xac\xf1E\x92\xdfC\x05\xca\xe5\x14j=\x8a&'


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
                <br>
                <a href="{{ redirect_url }}">OK</a>
            {% else %}
                <h1>Would you like to authorize access?</h1>
                <a href="{{ redirect_url }}{{ redirect_query_joiner }}code={{ response_code }}">YES</a>
                <a href="{{ redirect_url }}{{ redirect_query_joiner }}error=access_denied">NO</a>
            {% endif %}
        </div>
    </body>
</html>'''


class TokenProvider:
    def __init__(self, secret, digest='sha256'):
        self._secret = secret
        self._digest = digest

    def _sign(self, data):
        return b64encode(hmac.digest(self._secret, data, self._digest))

    def generate_token(self):
        data = secrets.token_urlsafe()
        return f'{data}.{self._sign(data)}'

    def is_token_valid(self, token):
        data, signature = token.split('.', 1)
        return signature == self._sign(data)


token_provider = TokenProvider(app.secret_key)


def json_error(error, status_code=400):
    print('JSON ERROR!', error, status_code)
    resp = jsonify(error=error)
    resp.status_code = status_code
    return resp


@app.route('/')
def hello():
    return 'Hello, world!'


@app.route('/oauth/authorize/')
def oauth_authorize():
    redirect_url_parts = list(urlparse(request.args['redirect_uri']))
    redirect_query = dict(parse_qsl(redirect_url_parts[4]))
    if 'state' in request.args:
        redirect_query['state'] = request.args['state']

    if request.args['client_id'] != CLIENT_ID:
        redirect_query['error'] = 'unauthorized_client'
    elif request.args['response_type'] != 'code':
        redirect_query['error'] = 'unsupported_response_type'
    else:
        # No errors
        response_code = AUTHORIZATION_CODE

    redirect_url_parts[4] = urlencode(redirect_query)
    redirect_url = urlunparse(redirect_url_parts)
    redirect_query_joiner = '&' if redirect_query else '?'

    return render_template_string(AUTH_HTML_TEMPLATE, **locals())


@app.route('/oauth/token/', methods=['POST'])
def oauth_token():
    print(request.headers)
    print(request.form)
    # TODO: (As per https://tools.ietf.org/html/rfc6749#section-4.1.3)
    #   o Ensure "redirect_uri" is present and identical to one in authorization request

    if {'grant_type', 'code', 'client_id', 'client_secret', 'redirect_uri'}.difference(request.form):
        return json_error('invalid_request')

    if (request.form['client_id'] != CLIENT_ID) or (request.form['client_secret'] != CLIENT_SECRET):
        return json_error('invalid_client', 401)

    grant_type = request.form['grant_type']

    if grant_type == 'authorization_code':
        pass
    elif grant_type == 'refresh_token':
        if 'refresh_token' not in request.form:
            return json_error('invalid_request')

        try:
            current_token = token_provider.decode_token(request.headers['Bearer'])
        except AuthError:
            return json_error('invalid_grant')

        if request.form['refresh_token'] != current_token['refresh_token']:
            return json_error('invalid_grant')
    else:
        return json_error('unsupported_grant_type')

    token = token_provider.generate_token()

    return jsonify(
        access_token=token_provider.encode_token(token),
        token_type='Bearer',
        expires_in=TOKEN_EXPIRE_DURATION,
        refresh_token=token['refresh_token'],
    )


@app.route('/api/fulfillment/', methods=['POST'])
def api_fulfullment():
    print(request.headers)
    print(request.args)
    print(request.data)
    return 'ok'


def main():
    app.run(
        '0.0.0.0',
        3459,
        ssl_context=(
            r'C:\Users\zeevr\Documents\home.zeevro.com-cert-and-chain.pem',
            r'C:\Users\zeevr\Documents\home.zeevro.com-key.pem'
        ),
        debug=True,
        use_reloader=True,
    )


if __name__ == '__main__':
    main()
