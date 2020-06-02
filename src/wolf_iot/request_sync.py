import argparse

from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account


def request_sync(key_file_name, agent_user_id='1'):
    credentials = service_account.Credentials.from_service_account_file(key_file_name)
    scoped_credentials = credentials.with_scopes(['https://www.googleapis.com/auth/homegraph'])
    sess = AuthorizedSession(scoped_credentials)
    resp = sess.post('https://homegraph.googleapis.com/v1/devices:requestSync', json={'agentUserId': str(agent_user_id)})

    resp.raise_for_status()

    return resp.json()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('-k', '--key-path', help='Path to JSON file containing Google secret key')
    args = p.parse_args()

    print(request_sync(args.key_path))


if __name__ == "__main__":
    main()
