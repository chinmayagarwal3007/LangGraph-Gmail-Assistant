from gmail_tools import search_emails, summarize_emails, create_calendar_event, get_upcoming_events, parse_meeting_request, draft_email_from_prompt, send_email
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage
from pydantic import BaseModel
from typing import List
from langchain_core.messages import BaseMessage
from gemini_model import llm
import json

class AgentState(BaseModel):
    messages: List[BaseMessage]

# Step 1: Define tools
tools = [search_emails, summarize_emails, create_calendar_event, get_upcoming_events, parse_meeting_request, draft_email_from_prompt, send_email]

# Step 2: Setup Gemini model with tools
llm = llm.bind_tools(tools)


TOOLS = {
    "search_emails": (search_emails, ["query", "gmail_service"]),
    "summarize_emails": (summarize_emails, ["emails"]),
    "get_upcoming_events": (get_upcoming_events, ["upcoming_event", "calendar_service"]),
    "create_calendar_event": (create_calendar_event, ["event_details","calendar_service"]),
    "parse_meeting_request": (parse_meeting_request, ["prompt"]),
    "send_email": (send_email, ["email_draft", "gmail_service"]),
    "draft_email_from_prompt": (draft_email_from_prompt, ["prompt"]),
}

# Step 3: LLM node
def agent_node(state):
    messages =  state.messages
    response = llm.invoke(messages)
    return {"messages": messages + [response]}

# Tool execution node
def get_tool_node(gmail_service, calendar_service):
    def tool_node(state):
        last_message = state.messages[-1]
        tool_calls = last_message.tool_calls
        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            args = tool_call["args"]
            for tool in tools:
                if tool.name == tool_name:
                    if tool_name not in TOOLS:
                        raise ValueError(f"Unknown tool: {tool_name}")
                    tool_func, arg_keys = TOOLS[tool_name]

                    # 🛠 Inject services dynamically here
                    kwargs = {}
                    if "gmail_service" in arg_keys:
                        kwargs["gmail_service"] = gmail_service
                    if "calendar_service" in arg_keys:
                        kwargs["calendar_service"] = calendar_service
                    try:
                        if len(args) != 0:
                            result = tool.invoke({arg_keys[0]:args[arg_keys[0]], **kwargs})
                        else:
                            result =  tool.invoke({})
                    
                    except Exception as e:
                        new_messages = state.messages + [AIMessage(content="Can you please provide more details?")]
                        return {"messages": new_messages}
                    break

            new_messages = state.messages + [
                ToolMessage(
                    tool_call_id=tool_call["id"],
                    content=str(result)
                )
            ]
            state.messages = new_messages
        return {"messages": state.messages}
    return tool_node


#Routing logic
def should_use_tool(state):
    last =  state.messages[-1]
    try:
        if last.tool_calls[0]['name'] == "draft_email_from_prompt":
            return "email_draft"
    except:
        pass
    return "tools" if hasattr(last, "tool_calls") and last.tool_calls else "end"


def email_draft_node(state):
    last = state.messages[-1].tool_calls[0]["args"]["prompt"]
    llm_result = draft_email_from_prompt.invoke({"prompt": last})
    raw_email = json.loads(llm_result.content[7:-3].strip())
    email_draft = f"subject: {raw_email["subject"]}\n\nbody:\n{raw_email["body"]}"
    final_message = f"Preparing to send email with \n\n{email_draft}\n\nDo you want to send this email or edit it?\n"
    new_messages = state.messages + [AIMessage(content=final_message)]
    return {"messages": new_messages}


# Build LangGraph
def build_graph(tool_node):
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    #graph.add_node("should_send", should_send)
    graph.add_node("email_draft", email_draft_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_use_tool)
    graph.add_edge("tools", "agent")
    #graph.add_edge("should_send", END)
    graph.add_edge("email_draft", END)
    return graph.compile()

#Test
if __name__ == "__main__":
    app = build_graph()
    result = app.invoke({"messages": [HumanMessage(content="set up a remainder in my calendar for tomorrow 3 pm for doctor appointment")]})
    for msg in result["messages"]:
        print(msg.content)
