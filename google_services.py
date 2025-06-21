from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import streamlit as st
import json

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar"
]


CREDENTIALS_PATH = "/tmp/credentials.json"

def get_credentials_from_code(code: str) -> Credentials:
    credentials_dict = json.loads(st.secrets["google"]["credentials_json"])
    flow = Flow.from_client_secrets_file(
        credentials_dict,
        scopes=SCOPES,
        redirect_uri="https://langgraph-gmail-assistant-y54mh3d6ckwdwya7gfeu2b.streamlit.app/"
    )
    flow.fetch_token(code=code)
    return flow.credentials

def get_auth_url():
    credentials_dict = json.loads(st.secrets["google"]["credentials_json"])
    flow = Flow.from_client_secrets_file(
        credentials_dict,
        scopes=SCOPES,
        redirect_uri="https://langgraph-gmail-assistant-y54mh3d6ckwdwya7gfeu2b.streamlit.app/"
    )
    auth_url, _ = flow.authorization_url(prompt='consent')
    return auth_url

def get_service(service_name: str, creds: Credentials):
    return build(service_name, 'v1' if service_name == 'gmail' else 'v3', credentials=creds)
