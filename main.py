from gmail_tools import search_emails, summarize_emails, create_calendar_event, get_upcoming_events, parse_meeting_request
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, ToolMessage
from pydantic import BaseModel
from typing import List
from langchain_core.messages import BaseMessage
from gemini_model import llm


class AgentState(BaseModel):
    messages: List[BaseMessage]

# Step 1: Define tools
tools = [search_emails, summarize_emails, create_calendar_event, get_upcoming_events, parse_meeting_request]

# Step 2: Setup Gemini model with tools
llm = llm.bind_tools(tools)


TOOLS = {
    "search_emails": (search_emails, ["query"]),
    "summarize_emails": (summarize_emails, ["emails"]),
    "get_upcoming_events": (get_upcoming_events, ["days_ahead"]),
    "create_calendar_event": (create_calendar_event, ["event_details"]),
    "parse_meeting_request": (parse_meeting_request, ["prompt"])
}

# Step 3: LLM node
def agent_node(state):
   
    messages =  state.messages
    response = llm.invoke(messages)
    return {"messages": messages + [response]}

# Tool execution node
def tool_node(state):
   
    last_message =  state.messages[-1]
   
    tool_call = last_message.tool_calls[0]
  
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

    return {"messages": new_messages}
    #return {"messages": state.messages + [ToolMessage(content=str(result), tool_call_id="tool-1")]}

# Routing logic
def should_use_tool(state):
  
    last =  state.messages[-1]
    return "tools" if hasattr(last, "tool_calls") and last.tool_calls else "end"

# Build LangGraph
graph = StateGraph(AgentState)
graph.add_node("agent", agent_node)
graph.add_node("tools", tool_node)
graph.set_entry_point("agent")
graph.add_conditional_edges("agent", should_use_tool)
graph.add_edge("tools", "agent")
app = graph.compile()

# Test
if __name__ == "__main__":
    result = app.invoke({"messages": [HumanMessage(content="Create a meeting titled Project Kickoff with the john on 14 july 2025 at 10 AM for 1 hour.")]})
    for msg in result["messages"]:
        print(msg.content)