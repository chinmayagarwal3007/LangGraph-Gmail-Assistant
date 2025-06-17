# 📧 Gmail Executive Assistant (LLM + LangGraph)

An intelligent assistant powered by LangGraph and Gemini that helps you manage your Gmail and Google Calendar using natural language.

---

## 🚀 Features Implemented

### ✅ 1. **Email Summarization**
- Search and fetch emails by user prompt.
- Summarize top matching emails using LLM.
- Limits to 2 recent messages to avoid token overload.

### ✅ 2. **Smart Email Search**
- Understands user intent to find emails by subject, sender, or keyword.
- Returns top matching emails with subject, snippet, and sender info.
- Can be reused by other tools (e.g., for calendar parsing or replying).

### ✅ 3. **Meeting Detection & Calendar Integration**
- Extracts meeting details (title, date, time, attendees) from user query.
- Uses `dateparser` to handle flexible date/time formats.
- Adds events to Google Calendar.

### ✅ 4. **Check Calendar for Upcoming Meetings**
- Lists upcoming events in the next N days.
- If a person/team is mentioned (e.g., "Do I have a meeting with John?"), filters only those events.
- Falls back to all upcoming meetings if no filter term is found.

### ✅ 5. **Email Composition + Human-in-the-Loop Approval**
- Constructs email draft from user prompt (recipient, subject, content).
- Shows draft and asks user to confirm or edit.
- Supports iterative loop until user approves final version.
- Sends email after user confirmation.

---

## 🧠 Powered by LangGraph

LangGraph is used to model the assistant's logic as a dynamic state graph with branching for:
- Tool selection (e.g., search, summarize, calendar)
- Human-in-the-loop flow (e.g., confirm/edit draft emails)
- Future extension points (e.g., memory, vector DB)

---

## 🧰 Tools Used

| Tool Name                 | Description                                                       |
|---------------------------|-------------------------------------------------------------------|
| `search_emails`           | Search Gmail messages by user prompt.                             |
| `summarize_emails`        | Summarize a list of emails using Gemini.                          |
| `parse_meeting_request`   | Extract structured info (title, date, attendees) from user query. |
| `create_calendar_event`   | Adds confirmed meeting to calendar.                               |
| `get_upcoming_events`     | Returns upcoming events, filtered if name provided.               |
| `draft_email_from_prompt` | Generates an email based on natural prompt.                       |
| `send_email`              | Sends a drafted email after approval.                             |

---

## 🏗 Architecture

```plaintext
[Human Prompt] ──▶ [Agent Node (LLM)] ──▶ [Tool Node / Draft / Confirm]
                      ▲                     │
                      └───── Loop ──────────┘
```

- Agent decides tool to call or whether to branch.
- For email sending, agent drafts → asks confirmation → sends.
- Graph transitions via conditions and state tracking.

---

## 🔐 Auth & Setup

- Gmail and Calendar API via OAuth 2.0.
- Tokens are cached using pickle (`token_gmail.pickle`, `token_calendar.pickle`).
- Uses `credentials.json` from Google Cloud Console.

---

## ✅ Completed
- ✅ LLM-based tool orchestration via LangGraph
- ✅ Gmail read, summarize, search
- ✅ Google Calendar event creation
- ✅ Human-in-the-loop for email send approval
- ✅ Conditional filtering for calendar events
- ✅ Date parsing using `dateparser`

---

## 🔜 Up Next

- ⏳ Frontend UI using Streamlit

---

## 🧑‍💻 Run It

```bash
# Activate environment
source venv/bin/activate

# Run app
python main.py
```

Prompt examples:
- "Summarize emails about flight bookings"
- "Add a meeting with Alice on Monday 3pm"
- "Do I have any meeting with marketing team?"
- "Send email to Chinmay about the Q3 report"