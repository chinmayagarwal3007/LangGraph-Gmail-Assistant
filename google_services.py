from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar"
]

TOKEN_PATH = "token.json"  # or per-user token
CREDENTIALS_PATH = "/tmp/credentials.json"

def get_credentials_from_code(code: str) -> Credentials:
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_PATH,
        scopes=SCOPES,
        redirect_uri="http://localhost:8501/"
    )
    flow.fetch_token(code=code)
    return flow.credentials

def get_auth_url():
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_PATH,
        scopes=SCOPES,
        redirect_uri="http://localhost:8501/"
    )
    auth_url, _ = flow.authorization_url(prompt='consent')
    return auth_url

def get_service(service_name: str, creds: Credentials):
    return build(service_name, 'v1' if service_name == 'gmail' else 'v3', credentials=creds)