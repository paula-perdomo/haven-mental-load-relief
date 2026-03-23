import os
import datetime
import jwt
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool

load_dotenv()

app = FastAPI(title="Haven Backend Proxy")

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev_secret_key_change_me")
ALGORITHM = "HS256"
# In a real app, this should be a proper user database!
HARDCODED_USERNAME = os.environ.get("HAVEN_USERNAME", "admin")
HARDCODED_PASSWORD = os.environ.get("HAVEN_PASSWORD", "secret")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")

# Models
class ChatRequest(BaseModel):
    text: str
    image_b64: Optional[str] = None
    mime_type: Optional[str] = "image/jpeg"

class Activity(BaseModel):
    title: str
    day_of_week: str
    time_str: str
    packing_list: List[str]

class ChatResponse(BaseModel):
    reply: str
    activities: List[Activity]

# Auth Utils
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(days=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return username
    except jwt.PyJWTError:
        raise credentials_exception

# --- LANGCHAIN LOGIC ---
@tool
def create_activity(title: str, day_of_week: str, time_str: str, packing_list: list[str]) -> str:
    """Creates a new household activity and its required packing/prep items."""
    return "Scheduled"

def get_llm():
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return None
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.3,
            google_api_key=api_key
        )
        return llm.bind_tools([create_activity])
    except Exception as e:
        print(f"Error initializing LLM: {e}")
        return None

# --- ROUTES ---
@app.post("/api/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username != HARDCODED_USERNAME or form_data.password != HARDCODED_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, current_user: str = Depends(get_current_user)):
    llm = get_llm()
    if not llm:
        raise HTTPException(status_code=500, detail="LLM not configured on server")

    system_prompt = """You are Haven, a Family Logistics Copilot.
Your job is to parse schedules from images/text and securely track the household load to assist busy parents.

If the user uploads an image/schedule, extract the activities and packing lists (like goggles, towel) 
and use the `create_activity` tool to save them into the family schedule database!
If they just ask a question, answer it. But prioritize creating structured schedules using the tool.
"""
    messages = [SystemMessage(content=system_prompt)]

    if request.image_b64:
        content_items = []
        if request.text:
            content_items.append({"type": "text", "text": request.text})
        else:
            content_items.append({"type": "text", "text": "Please parse this schedule."})
            
        content_items.append({"type": "image_url", "image_url": {"url": f"data:{request.mime_type};base64,{request.image_b64}"}})
        messages.append(HumanMessage(content=content_items))
    else:
        messages.append(HumanMessage(content=request.text))

    try:
        response = llm.invoke(messages)
        
        reply_text = response.content
        if isinstance(reply_text, list):
            reply_text = " ".join([str(i.get("text", "")) for i in reply_text if isinstance(i, dict) and "text" in i])
        if not reply_text:
            reply_text = ""

        out_activities = []
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tc in response.tool_calls:
                if tc['name'] == 'create_activity':
                    args = tc['args']
                    out_activities.append(Activity(
                        title=args.get("title", "Unknown"),
                        day_of_week=args.get("day_of_week", "Unknown"),
                        time_str=args.get("time_str", "Unknown"),
                        packing_list=args.get("packing_list", [])
                    ))
        
        return ChatResponse(reply=str(reply_text), activities=out_activities)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
