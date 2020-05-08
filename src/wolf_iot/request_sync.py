from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account


def request_sync(agent_user_id):
    credentials = service_account.Credentials.from_service_account_file(r'C:\Users\zeevr\Downloads\lights-eb1e6-86da7b63115f.json')
    scoped_credentials = credentials.with_scopes(['https://www.googleapis.com/auth/homegraph'])
    sess = AuthorizedSession(scoped_credentials)
    return sess.post('https://homegraph.googleapis.com/v1/devices:requestSync', json={'agentUserId': str(agent_user_id)}).json()
