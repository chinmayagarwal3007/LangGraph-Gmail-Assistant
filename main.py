import os
from gmail_tools import search_emails, summarize_emails
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, ToolMessage
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List
from langchain_core.messages import BaseMessage

class AgentState(BaseModel):
    messages: List[BaseMessage]

load_dotenv()



# Step 2: Setup Gemini model with tools
tools = [search_emails, summarize_emails]
os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0).bind_tools(tools)


TOOLS = {
    "search_emails": (search_emails, ["query"]),
    "summarize_emails": (summarize_emails, ["emails"]),
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
    
    args = tool_call["args"]
    
    for tool in tools:
        if tool.name == tool_name:
           
            # result = tool.invoke(args['query'])
            if tool_name not in TOOLS:
                raise ValueError(f"Unknown tool: {tool_name}")

            tool_func, arg_keys = TOOLS[tool_name]
           
            result = tool.invoke({arg_keys[0]:args[arg_keys[0]]})

           
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
    result = app.invoke({"messages": [HumanMessage(content="Summarize emails from google")]})
    for msg in result["messages"]:
        print(msg.content)