from gmail_tools import search_emails, summarize_emails, create_calendar_event, get_upcoming_events, parse_meeting_request, draft_email_from_prompt, send_email
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage
from pydantic import BaseModel
from typing import List
from langchain_core.messages import BaseMessage
from gemini_model import llm
from langchain.prompts import PromptTemplate
import uuid


class AgentState(BaseModel):
    messages: List[BaseMessage]

# Step 1: Define tools
tools = [search_emails, summarize_emails, create_calendar_event, get_upcoming_events, parse_meeting_request, draft_email_from_prompt, send_email]
# Step 2: Setup Gemini model with tools
llm = llm.bind_tools(tools)


TOOLS = {
    "search_emails": (search_emails, ["query"]),
    "summarize_emails": (summarize_emails, ["emails"]),
    "get_upcoming_events": (get_upcoming_events, ["upcoming_event"]),
    "create_calendar_event": (create_calendar_event, ["event_details"]),
    "parse_meeting_request": (parse_meeting_request, ["prompt"]),
    "send_email": (send_email, ["email_draft"]),
    "draft_email_from_prompt": (draft_email_from_prompt, ["prompt"]),
}

# Step 3: LLM node
def agent_node(state):
    messages =  state.messages
    response = llm.invoke(messages)
    return {"messages": messages + [response]}

# Tool execution node
def tool_node(state):
    last_message =  state.messages[-1]
    tool_calls = last_message.tool_calls
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        print(f"Tool call: {tool_name}, args: {tool_call['args']}")
        args = tool_call["args"]
        for tool in tools:
            if tool.name == tool_name:
                # result = tool.invoke(args['query'])
                if tool_name not in TOOLS:
                    raise ValueError(f"Unknown tool: {tool_name}")
                tool_func, arg_keys = TOOLS[tool_name]
                if len(args) != 0:
                    result = tool.invoke({arg_keys[0]:args[arg_keys[0]]})
                else:
                    result = tool.invoke({})
                break

        new_messages = state.messages + [
        ToolMessage(
            tool_call_id=tool_call["id"],  # must match what Gemini gave
            content=str(result)
            )
        ]
        state.messages = new_messages
    return {"messages": state.messages}


#Routing logic
def should_use_tool(state):
    last =  state.messages[-1]
    try:
        if last.tool_calls[0]['name'] == "send_email":
            return "should_send"
    except:
        pass
    return "tools" if hasattr(last, "tool_calls") and last.tool_calls else "end"

def should_send(state):
    last = state.messages[-1].tool_calls[0]["args"]["email_draft"]
    print("\n -------------------------------------------------------------\n")
    print(last)
    print("\n -------------------------------------------------------------\n")

    subject = last["subject"]
    body = last["body"]
    to = last["to"]

    email_draft = f"subject: {subject}\n\nbody:\n{body}"
    # user_input = input(
    #     f"Preparing to send email with \n\n{email_draft}\n\nDo you want to send this email or edit it?\n\nUser: "
    # )
    final_message = f"Preparing to send email with \n\n{email_draft}\n\nDo you want to send this email or edit it?\n"
    new_messages = state.messages + [AIMessage(content=final_message)]
    return {"messages": new_messages}
#     email_review_prompt = PromptTemplate.from_template(
#         """
# Here is the email draft:
# {email_draft}
# I asked the user if it's okay to send this email.

# User's response:
# {user_input}

# Based on the user's response, do one of the following:

# 1. If the user has agreed to send the email as is, respond with:
# **Yes**

# 2. If the user has suggested changes, respond with a string in the following format:
# **"Make the following changes -> [summary of changes suggested by the user] to the following email:\n{email_draft}"**
# """
#     )
#     full_prompt = email_review_prompt.format(
#         email_draft=email_draft, user_input=user_input
#     )
#     response = llm.invoke([HumanMessage(content=full_prompt)])
#     random_id = uuid.uuid4()

#     if response.content.strip().lower() == "**yes**":
#         print("--------------------------------------------Sending email...")
#         result = send_email.invoke({"email_draft": {
#             "to": to,
#             "subject": subject,
#             "body": body
#         }})    
#     else:
#         result = draft_email_from_prompt.invoke({"prompt": response.content})
#     new_messages = state.messages + [
#         ToolMessage(
#             tool_call_id=random_id, # Use a random ID for the tool call
#             content=str(result)
#             )
#         ]

#     return {"messages": new_messages}



# Build LangGraph
def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.add_node("should_send", should_send)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_use_tool)
    graph.add_edge("tools", "agent")
    graph.add_edge("should_send", END)
    return graph.compile()

#Test
if __name__ == "__main__":
    app = build_graph()
    result = app.invoke({"messages": [HumanMessage(content="Schedule a meeting with Chinmay(agarwalchinmay3007@gmail.com) to discuss ongoing updates of the project for tomorrow 3 pm.")]})
    for msg in result["messages"]:
        print(msg.content)


#Set up a meeting with Alex on Tuesday, June 18th 2025 at 3 pm to discuss the Q3 planning.
#what are my upcoming meetings?
#summarize emails from postman
#Send an email to Chinmay(agarwalchinmay3007@gmail.com) about the Q3 planning meeting on June 18th 2025 at 3 pm. Also my name is John
#Set up a meeting with Chinmay(agarwalchinmay3007@gmail.com) on Wednesday, June 18th 2025 at 3 pm to discuss the Q3 planning.Also please send an email to Chinmay about the meeting. My name is John.