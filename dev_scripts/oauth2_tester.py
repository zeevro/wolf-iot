from requests_oauthlib import OAuth2Session

from flask import Flask, request, redirect, session
from flask.json import jsonify


BASE_URL = 'https://localhost:3459/'
AUTH_URL = BASE_URL + 'oauth/authorize'
TOKEN_URL = BASE_URL + 'oauth/token'

CLIENT_ID = 'asdfqwer'
CLIENT_SECRET = 'asdfqwer'


app = Flask(__name__)
app.secret_key = b'P\x86\xecGV&\xbdm\x08z\xf2h}\xf6\x1dt\xc3vM\x06\x0b\xe6\x88\x9c.\xab\xa4\xbb\x84\x85\xbd\xc0'


@app.route("/")
def login():
    sess = OAuth2Session(CLIENT_ID, redirect_uri='https://localhost:8080/callback')
    authorization_url, state = sess.authorization_url(AUTH_URL)

    # State is used to prevent CSRF, keep this for later.
    session['oauth_state'] = state
    return f'<a href="{authorization_url}">GO!</a>'


@app.route("/callback")
def callback():
    sess = OAuth2Session(CLIENT_ID, state=session['oauth_state'])
    sess.verify = False
    token = sess.fetch_token(TOKEN_URL, client_secret=CLIENT_SECRET, authorization_response=request.url)

    return jsonify(token)


def main():
    app.run(
        '127.0.0.1',
        8080,
        ssl_context=(
            r'C:\Users\zeevr\Documents\home.zeevro.com-cert-and-chain.pem',
            r'C:\Users\zeevr\Documents\home.zeevro.com-key.pem'
        ),
        debug=True,
    )


if __name__ == "__main__":
    main()
