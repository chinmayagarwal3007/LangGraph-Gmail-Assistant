from typing import Dict
from gemini_model import llm
from langchain_core.messages import HumanMessage
from langchain.prompts import PromptTemplate
from fastapi import FastAPI
import uvicorn
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

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
    print(f"📩 Received prompt: {prompt}")  # Add this
    prompt = template.format(prompt=prompt)
    response = llm.invoke([HumanMessage(content=prompt)])
    print(f"📤 Response from LLM: {response.content}") 
    try:
        # The actual content is a JSON string, so we parse it
        email_dict = json.loads(response.content[7:-3].strip())
        return email_dict
    except (json.JSONDecodeError, TypeError) as e:
        print(f"Error parsing LLM response: {e}")
        # Return a structured error
        return {"error": "Failed to generate a valid email format.", "details": str(response.content)}

app = FastAPI(
    title="Email Drafting Agent API",
    description="An API to draft professional emails from a prompt.",
    version="1.0.0"
)
class EmailRequest(BaseModel):
    prompt: str

# Define the root endpoint for a simple health check
@app.get("/")
def read_root():
    return {"status": "Email Drafting Agent is running"}

# Define the main endpoint to draft an email
@app.post("/draft_email")
async def handle_draft_email(request: EmailRequest):
    """
    Receives a prompt and returns a drafted email in JSON format.
    """
    try:
        result = draft_email_from_prompt(request.prompt)
        if "error" in result:
            raise HTTPException(status_code=500, detail=result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
