import json

from requests_oauthlib import OAuth2Session

from flask import Flask, request, render_template_string, session, url_for

from wolf_iot.app import app as wolf_iot_app


BASE_URL = 'https://localhost:3459/'
AUTH_URL = BASE_URL + 'oauth/authorize'
TOKEN_URL = BASE_URL + 'oauth/token'

CLIENT_ID = wolf_iot_app.config['CLIENT_ID']
CLIENT_SECRET = wolf_iot_app.config['CLIENT_SECRET']

HTML_TEMPLATE = '''<html>
    <head>
        <title>Oauth2 response</title>
        <link href="https://unpkg.com/prismjs@v1.x/themes/prism.css" rel="stylesheet" />
        <script src="https://unpkg.com/prismjs@1.x/components/prism-core.min.js"></script>
        <script src="https://unpkg.com/prismjs@v1.x/plugins/autoloader/prism-autoloader.min.js"></script>
    </head>
    <body>
        <h3>Token</h3>
        <pre><code class="language-json">{{ token|pretty_json|safe }}</code></pre>
        <h3>Sync response</h3>
        <pre><code class="language-json">{{ sync_resp|pretty_json|safe }}</code></pre>
        <a href="/">Go again</a>
    </body>
</html>'''


app = Flask(__name__)
app.secret_key = b'P\x86\xecGV&\xbdm\x08z\xf2h}\xf6\x1dt\xc3vM\x06\x0b\xe6\x88\x9c.\xab\xa4\xbb\x84\x85\xbd\xc0'


def pretty_json(o):
    return json.dumps(
        o,
        indent=4,
        sort_keys=True,
        separators=(',', ': '),
    )
app.add_template_filter(pretty_json)


@app.route("/")
def login():
    sess = OAuth2Session(CLIENT_ID, redirect_uri=url_for('callback', _external=True))
    authorization_url, state = sess.authorization_url(AUTH_URL)

    # State is used to prevent CSRF, keep this for later.
    session['oauth_state'] = state
    return f'<a href="{authorization_url}">GO!</a>'


@app.route("/callback")
def callback():
    sess = OAuth2Session(CLIENT_ID, state=session['oauth_state'])
    sess.verify = False
    token = sess.fetch_token(
        TOKEN_URL,
        include_client_id=True,
        client_secret=CLIENT_SECRET,
        authorization_response=request.url,
    )

    sync_data = {
        "requestId": "ff36a3cc-ec34-11e6-b1a0-64510650abcf",
        "inputs": [{
            "intent": "action.devices.SYNC"
        }]
    }

    print(token)

    sync_resp = sess.post(BASE_URL + 'api/fulfillment', json=sync_data).json()

    return render_template_string(HTML_TEMPLATE, token=token, sync_resp=sync_resp)


def main():
    app.run(
        '127.0.0.1',
        8080,
        ssl_context='adhoc',
        debug=True,
    )


if __name__ == "__main__":
    main()
