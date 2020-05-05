import secrets
import time

from authlib.oauth2.rfc6749 import ClientMixin, TokenMixin
from authlib.integrations.flask_oauth2 import AuthorizationServer
from flask import Flask, request, render_template_string


TOKEN_EXPIRE_DURATION = 3 * 24 * 60 * 60  # 3 days


class DummyUser:
    @staticmethod
    def get_user_id():
        return 1


class DummyClient(ClientMixin):
    def __init__(self, cliend_id, client_secret=None, redirect_uri=None):
        self._cliend_id = cliend_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri

    def get_client_id(self):
        return self._cliend_id

    def get_default_redirect_uri(self):
        return self._redirect_uri

    def get_allowed_scope(self, scope):
        return scope or ''

    def check_redirect_uri(self, redirect_uri):
        return redirect_uri == self._redirect_uri

    def has_client_secret(self):
        return bool(self._client_secret)

    def check_client_secret(self, client_secret):
        return client_secret == self._client_secret

    def check_token_endpoint_auth_method(self, method):
        # TODO: Which to choose?
        return method in {'client_secret_basic', 'client_secret_post'}

    def check_response_type(self, response_type):
        return response_type == 'code'  # and not 'token'

    def check_grant_type(self, grant_type):
        return grant_type == 'authorization_code'


class SelfEncodedToken(TokenMixin):
    def __init__(self):
        self._nonce = secrets.token_urlsafe()
        self._refresh_token = secrets.token_urlsafe()
        self._client_id = ''
        self._scope = ''
        self._created = int(time.time())
        self._expires_in = TOKEN_EXPIRE_DURATION

    def get_client_id(self):
        return self._client_id

    def get_scope(self):
        return self._scope

    def get_expires_in(self):
        return self._expires_in

    def get_expires_at(self):
        return self._created + self._expires_in


def create_query_client_func(clients):
    def query_client(client_id):
        return clients.get(client_id, None)
    return query_client


def create_save_token_func():
    def save_token(token_data, request):
        # tokens.append(token_data)
        pass
    return save_token


CLIENTS = {'asdfqwer': DummyClient('asdfqwer', 'asdfqwer')}


app = Flask(__name__)
query_client = create_query_client_func(CLIENTS)
save_token = create_save_token_func()
server = AuthorizationServer(app, query_client, save_token)


@app.route('/oauth/authorize', methods=['GET', 'POST'])
def authorize():
    # Login is required since we need to know the current resource owner.
    # It can be done with a redirection to the login page, or a login
    # form on this authorization page.
    current_user = DummyUser()
    if request.method == 'GET':
        grant = server.validate_consent_request(end_user=current_user)
        return render_template_string(
            'authorize.html',
            grant=grant,
            user=current_user,
        )
    confirmed = request.form['confirm']
    if confirmed:
        # granted by resource owner
        return server.create_authorization_response(grant_user=current_user)
    # denied by resource owner
    return server.create_authorization_response(grant_user=None)


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
