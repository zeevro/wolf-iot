import argparse

from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account


def request_sync(key_file_name):
    credentials = service_account.Credentials.from_service_account_file(key_file_name)
    scoped_credentials = credentials.with_scopes(['https://www.googleapis.com/auth/homegraph'])
    sess = AuthorizedSession(scoped_credentials)
    resp = sess.post('https://homegraph.googleapis.com/v1/devices:requestSync', json={'agentUserId': '1'})

    resp.raise_for_status()

    return resp.json()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('-a', '--account-path', help='Path to JSON file containing Google account details')
    args = p.parse_args()

    print(request_sync(args.account_path))


if __name__ == "__main__":
    main()
