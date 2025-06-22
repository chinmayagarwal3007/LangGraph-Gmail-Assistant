from datetime import datetime, timedelta
from email.mime.text import MIMEText
import pickle
from typing import List, Dict, Optional, TypedDict
from langchain.tools import tool
from pydantic import BaseModel, Field
from gemini_model import llm
import base64
from langchain_core.messages import HumanMessage
from langchain.prompts import PromptTemplate
import dateparser
from langchain.output_parsers import PydanticOutputParser



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

def load_access_token_from_pickle(pickle_file='token_calendar.pickle'):
    with open(pickle_file, 'rb') as token:
        creds = pickle.load(token)
    return creds.token  # This is your access token

class EventDetails(TypedDict):
    title: str
    start_datetime: str
    attendees: List[str]
    end_datetime: str
    description: Optional[str]

class EmailDraft(TypedDict):
    to: str
    subject: str 
    body: str

class UpcomingEvent(TypedDict):
    days_ahead: Optional[int] = 7
    filter_term: Optional[str] = None

class MeetingRequest(BaseModel):
    """Data model for a meeting request."""
    title: str = Field(..., description="The subject or title of the meeting")
    datetime_text: str = Field(..., description="The natural language representation of the date and time, e.g., 'tomorrow at 3pm' or 'next Tuesday morning'")
    participants: List[str] = Field(..., description="A list of participant email addresses mentioned in the request")


# Tool 1: Search Emails
@tool
def search_emails(query: str, gmail_service) -> List[Dict]:
    """Searches Gmail for messages matching the query and fetches full body content."""
    service = gmail_service
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
def summarize_emails(emails: List[Dict]) -> Dict:
    """Summarizes emails and extracts potential calendar events (title, date, time, etc.)."""
    prompt = """Summarize these emails. Also, extract any meeting or deadline information as structured events.
Return a JSON with two keys:
1. summary: plain summary of emails
2. events: list of events with keys [title, date, time, description]

Emails:\n
"""
    for email in emails:
        prompt += f"Subject: {email['subject']}\nSender: {email['sender']}\nSnippet: {email.get('body', email.get('snippet'))}\n\n"

    response = llm.invoke([HumanMessage(content=prompt)])
    return response


@tool
def create_calendar_event(event_details: EventDetails, calendar_service) -> str:
    """Creates a Google Calendar event from structured details."""
    
    service = calendar_service
    parsed_datetime_start = dateparser.parse(event_details['start_datetime'], settings={'PREFER_DATES_FROM': 'future'})
    iso_datetime_start = parsed_datetime_start.isoformat() if parsed_datetime_start else None
    parsed_datetime_end = dateparser.parse(event_details['end_datetime'], settings={'PREFER_DATES_FROM': 'future'})
    iso_datetime_end = parsed_datetime_end.isoformat() if parsed_datetime_end else None

    event_payload = {
        'summary': event_details['title'],
        'description': event_details['description'],
        'start': {
            'dateTime': iso_datetime_start,
            'timeZone': 'Asia/Kolkata'
        },
        'end': {
            'dateTime': iso_datetime_end,
            'timeZone': 'Asia/Kolkata'
        },
        'attendees': [{'email': email.strip()} for email in event_details.get('attendees', [])]
    }

    event = service.events().insert(calendarId='primary', body=event_payload).execute()
    return f"📅 Event created: {event.get('htmlLink')}"

@tool
def get_upcoming_events(upcoming_event: UpcomingEvent, calendar_service) -> List[Dict]:
    """Fetches upcoming calendar events in the next N days."""
    service = calendar_service
    now = datetime.utcnow().isoformat() + 'Z'
    future = (datetime.utcnow() + timedelta(days=upcoming_event["days_ahead"])).isoformat() + 'Z'
    events_result = service.events().list(
        calendarId='primary',
        timeMin=now,
        timeMax=future,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])
    filtered_events = []
    for e in events:
        summary = e.get('summary', '').lower()
        description = e.get('description', '').lower()
        attendees = ', '.join([a.get('email', '') for a in e.get('attendees', [])]).lower()
        
        if upcoming_event["filter_term"]:
            term = upcoming_event["filter_term"].lower()
            if term in summary or term in description or term in attendees:
                filtered_events.append(e)
        else:
            filtered_events.append(e)

    return [{
        'summary': e.get('summary'),
        'start': e.get('start', {}).get('dateTime'),
        'end': e.get('end', {}).get('dateTime'),
        'description': e.get('description')
    } for e in filtered_events] 




@tool
def parse_meeting_request(prompt: str) -> Dict:
    """Parses a meeting request from user input into structured data."""

    # Use PydanticOutputParser and connect it to your model
    parser = PydanticOutputParser(pydantic_object=MeetingRequest)

    format_instructions = parser.get_format_instructions()

    prompt_template = PromptTemplate.from_template("""
You are an expert assistant that extracts meeting details from user input.

Extract the following information:
- title: The subject of the meeting.
- datetime_text: The verbatim natural language for the date and time (e.g., "tomorrow at 3pm").
- participants: A list of all email addresses mentioned.

If any information is missing, use a sensible placeholder. For example, if no title is mentioned, use "Meeting". If no participants are mentioned, use an empty list [].

Respond only with the JSON object as specified by the format instructions below.

FORMAT INSTRUCTIONS:
{format_instructions}

USER INPUT:
{user_input}
""")

    full_prompt = prompt_template.format(
        user_input=prompt,
        format_instructions=format_instructions
    )

    # The LLM call remains the same
    llm_response = llm.invoke([HumanMessage(content=full_prompt)])
    
    # The parser now directly returns an instance of your MeetingRequest class
    parsed_request: MeetingRequest = parser.parse(llm_response.content)

    # Parse the natural language date into a standardized format
    # Set the 'PREFER_DATES_FROM' setting to 'future' to avoid ambiguity
    # e.g., "Wednesday" will be next Wednesday, not last Wednesday.
    parsed_datetime = dateparser.parse(parsed_request.datetime_text, settings={'PREFER_DATES_FROM': 'future'})
    iso_datetime = parsed_datetime.isoformat() if parsed_datetime else None

    # Return the final, structured dictionary
    return {
        "title": parsed_request.title,
        "datetime": iso_datetime,
        "participants": parsed_request.participants
    }

@tool
def send_email(email_draft: EmailDraft, gmail_service) -> str:
    """Sends an email using Gmail API."""
    service = gmail_service
    message = MIMEText(email_draft['body'])
    message['to'] = email_draft['to']
    message['subject'] = email_draft['subject']

    raw_message = {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}
    try:
        service.users().messages().send(userId="me", body=raw_message).execute()
        return f"Email sent to {email_draft['to']} with subject '{email_draft['subject']}'"   
    except Exception as e:
        return f"Failed to send email: {str(e)}"
    
@tool
def draft_email_from_prompt(prompt: str) -> Dict[str, str]:
    """Generates a draft email (subject and body) from user intent."""
    template = PromptTemplate.from_template("""
    You are an AI writing assistant. Based on this instruction, write a professional email.

    Instruction: {prompt}

    Respond in this JSON format:
    {{
      "subject": "...",
      "body": "..."
    }}
    """)

    prompt = template.format(prompt=prompt)
    return llm.invoke([HumanMessage(content=prompt)])