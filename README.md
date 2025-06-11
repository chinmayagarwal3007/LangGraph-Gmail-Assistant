<!-- Project Scope:
Gmail Executive Assistant will be able to:

✅ Read and summarize emails.

📅 Detect meetings or deadlines and suggest calendar events.

📥 Find emails matching user prompts (e.g., “find the email with flight tickets”).

🧠 Use LangGraph tools to process results (summarize, reason, etc).

🗃 Optionally maintain memory/history to support longer workflows. -->

<!-- 🚧 NEXT TO BUILD
🗓 Detect Meetings/Deadlines → Suggest Calendar Events

Add a calendar_extractor tool

LLM detects time-sensitive info: “Meeting at 4PM”, “Your flight is at 10AM”

Output can be: date, time, event title

Later: Connect to Google Calendar API

🧠 Maintain memory / history (LangGraph stateful)

Track last_x_messages, past tool results, etc. in state

Let LLM access prior context like:
“Find all flight emails you told me about earlier” -->