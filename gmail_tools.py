import os
from typing import List, Dict, Optional
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from langchain.tools import tool

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
TOKEN_PATH = 'token.json'
CREDENTIALS_PATH = 'credentials.json'

def get_gmail_service():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_console()
        with open(TOKEN_PATH, 'w') as token_file:
            token_file.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

# Tool 1: Search Emails
@tool
def search_emails(query: str) -> List[Dict]:
    """Searches Gmail for messages matching the query."""
    service = get_gmail_service()
    response = service.users().messages().list(userId='me', q=query, maxResults=10).execute()
    messages = response.get('messages', [])
    results = []
    for msg in messages:
        msg_detail = service.users().messages().get(userId='me', id=msg['id']).execute()
        snippet = msg_detail.get('snippet', '')
        headers = msg_detail.get('payload', {}).get('headers', [])
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
        results.append({
            'id': msg['id'],
            'subject': subject,
            'sender': sender,
            'snippet': snippet
        })
    return results

# Tool 2: Summarize Emails
@tool
def summarize_emails(emails: List[Dict]) -> str:
    """Summarizes the content of a list of emails."""
    if not emails:
        return "No emails to summarize."
    summary = "Here are the email summaries:\n"
    for i, email in enumerate(emails, 1):
        summary += f"\n{i}. From: {email['sender']}\nSubject: {email['subject']}\nSnippet: {email['snippet']}\n"
    return summary
