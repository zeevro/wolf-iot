
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from flask import Flask, render_template_string, request

from wolf_iot.oauth2 import AUTH_HTML_TEMPLATE, AUTHORIZATION_CODE, CLIENT_ID, CLIENT_SECRET, auth_required, authenticate_request, create_token_response, json_error


app = Flask(__name__)
app.url_map.strict_slashes = False
app.secret_key = b'\x15\xe3\xdcsi\x1a\x9f\x13\xa1Y\xf4}z\t\xb4R\xf6~\xac\xf1E\x92\xdfC\x05\xca\xe5\x14j=\x8a&'


@app.route('/')
def hello():
    return f'Hello, world!\nAuth token: {authenticate_request()}'

temp_redirect_url = ''

@app.route('/oauth/authorize/')
def oauth_authorize():
    global temp_redirect_url
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

    temp_redirect_url = redirect_url

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

        current_token = authenticate_request()
        if current_token is None:
            return json_error('invalid_grant')

        if request.form['refresh_token'] != current_token['refresh_token']:
            return json_error('invalid_grant')
    else:
        return json_error('unsupported_grant_type')

    return create_token_response()


@app.route('/api/fulfillment/', methods=['POST'])
@auth_required
def api_fulfullment():
    req = request.json



    return 'ok'


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
