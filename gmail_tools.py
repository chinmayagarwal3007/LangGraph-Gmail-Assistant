import os
from typing import List, Dict, Optional
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from langchain.tools import tool
from gemini_model import llm
import base64
from langchain_core.messages import HumanMessage, ToolMessage

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

def extract_email_body(payload):
    """Recursively extracts plain text email body from Gmail payload."""
    if 'parts' in payload:
        for part in payload['parts']:
            body = extract_email_body(part)
            if body:
                return body
    else:
        mime_type = payload.get('mimeType', '')
        body_data = payload.get('body', {}).get('data', '')

        if mime_type == 'text/plain' and body_data:
            decoded_bytes = base64.urlsafe_b64decode(body_data.encode('UTF-8'))
            return decoded_bytes.decode('utf-8', errors='ignore')

    return None


# Tool 1: Search Emails
@tool
def search_emails(query: str) -> List[Dict]:
    """Searches Gmail for messages matching the query and fetches full body content."""
    service = get_gmail_service()
    response = service.users().messages().list(userId='me', q=query, maxResults=5).execute()
    messages = response.get('messages', [])
    results = []

    for msg in messages:
        msg_detail = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        payload = msg_detail.get('payload', {})
        headers = payload.get('headers', [])
        parts = payload.get('parts', [])

        # Extract metadata
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')

        # Fallback to snippet
        snippet = msg_detail.get('snippet', '')

        # Extract plain text body
        body = extract_email_body(payload) or snippet

        results.append({
            'id': msg['id'],
            'subject': subject,
            'sender': sender,
            'body': body,
            'internalDate': int(msg_detail.get('internalDate', 0))
        })

    sorted_msgs = sorted(results, key=lambda m: m['internalDate'], reverse=True)

    # Return only top 2 with selected fields
    return [
        {
            'id': msg['id'],
            'subject': msg['subject'],
            'sender': msg['sender'],
            'body': msg['body']
        }
        for msg in sorted_msgs[:2]
    ]

# Tool 2: Summarize Emails
@tool
def summarize_emails(emails: List[Dict]) -> str:
    """Summarizes a list of emails using the LLM. Only considers top 2 emails for brevity."""
    if not emails:
        return "No emails to summarize."

    # Limit to 2 emails to control tokens
    top_emails = emails[:2]

    # Prepare formatted text
    email_text = "\n\n".join(
        f"Subject: {email.get('subject', '')}\nBody: {email.get('body', '')}" 
        for email in top_emails
    )

    # Ask LLM to summarize
    summary_prompt = f"Summarize the following emails:\n\n{email_text}"
    response = llm.invoke([HumanMessage(content=summary_prompt)])

    return response.content.strip()