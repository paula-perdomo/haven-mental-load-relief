import os
import datetime
import jwt
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv

import backend.database as db
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool

load_dotenv()
db.init_db()

app = FastAPI(title="Haven Cloud Backend")

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev_secret_key_change_me")
ALGORITHM = "HS256"
HARDCODED_USERNAME = os.environ.get("HAVEN_USERNAME", "admin")
HARDCODED_PASSWORD = os.environ.get("HAVEN_PASSWORD", "secret")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")

# --- BACKGROUND NOTIFICATION SCHEDULER ---
import asyncio
import socket
import os
import time
from fastapi.staticfiles import StaticFiles

# Setup static files for Google Hub to access the TTS MP3s
os.makedirs("backend/static/announcements", exist_ok=True)
app.mount("/static", StaticFiles(directory="backend/static"), name="static")

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'
    finally:
        s.close()

LOCAL_IP = get_local_ip()
NOTIFIED_ACTIVITIES = set()

def cast_announcement(activity_id, title, time_str):
    if activity_id in NOTIFIED_ACTIVITIES:
        return
        
    try:
        from gtts import gTTS
        import pychromecast
        
        print(f"Generating TTS for {title}...")
        text = f"Haven Reminder. {title} is coming up at {time_str}. Please get everything ready."
        filename = f"act_{activity_id}.mp3"
        filepath = os.path.join("backend/static/announcements", filename)
        
        tts = gTTS(text=text, lang='en')
        tts.save(filepath)
        
        audio_url = f"http://{LOCAL_IP}:8000/static/announcements/{filename}"
        print(f"Looking for Google Hubs to cast {audio_url}...")
        
        chromecasts, browser = pychromecast.get_chromecasts()
        browser.stop_discovery()
        
        if not chromecasts:
            print("No Chromecast devices found on network.")
            return
            
        cast = chromecasts[0] # Grab the first available Google Hub/Home
        cast.wait()
        mc = cast.media_controller
        mc.play_media(audio_url, 'audio/mp3')
        mc.block_until_active()
        print(f"Successfully broadcasted to {cast.name}")
        
        NOTIFIED_ACTIVITIES.add(activity_id)
            
    except Exception as e:
        print(f"Error casting announcement: {e}")

async def notification_worker():
    while True:
        try:
            print(f"[{datetime.datetime.now().isoformat()}] Checking schedule for upcoming activities...")
            import backend.database as db
            acts = db.get_activities(HARDCODED_USERNAME)
            
            # For demonstration, broadcast the first un-notified activity
            for a in acts:
                act_id = a['id']
                if act_id not in NOTIFIED_ACTIVITIES:
                    await asyncio.to_thread(cast_announcement, act_id, a["title"], a["time_str"])
                    break
                    
        except Exception as e:
            print(f"Scheduler Background Error: {e}")
        await asyncio.sleep(60)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(notification_worker())

# --- AUTH UTILS ---
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

@app.post("/api/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # Support basic Username/Password or in the future: Google ID Tokens
    if form_data.username != HARDCODED_USERNAME or form_data.password != HARDCODED_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}

# --- MODELS ---
class ChatRequest(BaseModel):
    text: str
    image_b64: Optional[str] = None
    mime_type: Optional[str] = "image/jpeg"

class Activity(BaseModel):
    id: Optional[int] = None
    title: str
    day_of_week: str
    time_str: str

class PrepItem(BaseModel):
    id: int
    item_name: str
    is_packed: bool

class SharedList(BaseModel):
    id: int
    title: str
    
class ListItem(BaseModel):
    id: int
    item_name: str
    is_done: bool

class Member(BaseModel):
    id: Optional[int] = None
    name: str
    role: str

class ChatResponse(BaseModel):
    reply: str
    activities: List[dict]  # Simplified out_activities

class CreateListRequest(BaseModel):
    title: str

class CreateItemRequest(BaseModel):
    item_name: str

class ToggleItemRequest(BaseModel):
    is_done: bool

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

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, current_user: str = Depends(get_current_user)):
    llm = get_llm()
    if not llm:
        raise HTTPException(status_code=500, detail="LLM not configured on server")

    # Fetch household members to give context to the AI
    members = db.get_members(current_user)
    members_str = ", ".join([f"{m['name']} ({m['role']})" for m in members]) if members else "None yet."

    system_prompt = f"""You are Haven, a Family Logistics Copilot.
Your job is to parse schedules from images/text and securely track the household load to assist busy parents.
CURRENT HOUSEHOLD MEMBERS: {members_str}

If the user uploads an image/schedule, extract the activities and packing lists (like goggles, towel) 
and use the `create_activity` tool to save them into the family schedule database!
Assign members if explicitly requested or obvious (e.g., Mom's yoga).
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
                    # Persist automatically to cloud DB on behalf of user
                    act_id = db.add_activity(
                        user_id=current_user,
                        title=args.get("title", "Unknown"),
                        day_of_week=args.get("day_of_week", "Unknown"),
                        time_str=args.get("time_str", "Unknown")
                    )
                    packing_list = args.get("packing_list", [])
                    for p_item in packing_list:
                        db.add_prep_item(act_id, p_item)
                        
                    out_activities.append({
                        "id": act_id,
                        "title": args.get("title", "Unknown"),
                        "day_of_week": args.get("day_of_week", "Unknown"),
                        "time_str": args.get("time_str", "Unknown"),
                        "packing_list": packing_list
                    })
        
        return ChatResponse(reply=str(reply_text), activities=out_activities)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- CRUD ENDPOINTS FOR CLOUD DB ---

@app.get("/api/members", response_model=List[Member])
def get_user_members(current_user: str = Depends(get_current_user)):
    mems = db.get_members(current_user)
    return [Member(**m) for m in mems]

@app.post("/api/members")
def create_user_member(req: Member, current_user: str = Depends(get_current_user)):
    m_id = db.add_member(current_user, req.name, req.role)
    return {"id": m_id}

@app.delete("/api/members/{member_id}")
def delete_user_member(member_id: int, current_user: str = Depends(get_current_user)):
    db.delete_member(member_id)
    return {"status": "ok"}

@app.put("/api/members/{member_id}")
def update_user_member(member_id: int, req: Member, current_user: str = Depends(get_current_user)):
    db.update_member(member_id, req.name, req.role)
    return {"status": "ok"}

@app.get("/api/activities", response_model=List[Activity])
def get_user_activities(current_user: str = Depends(get_current_user)):
    acts = db.get_activities(current_user)
    return [Activity(**a) for a in acts]

@app.get("/api/activities/{act_id}/items", response_model=List[PrepItem])
def get_activity_prep_items(act_id: int, current_user: str = Depends(get_current_user)):
    items = db.get_prep_items(act_id)
    return [PrepItem(**i) for i in items]

@app.get("/api/lists", response_model=List[SharedList])
def get_shared_lists(current_user: str = Depends(get_current_user)):
    lists = db.get_lists(current_user)
    return [SharedList(**l) for l in lists]

@app.post("/api/lists")
def create_list(req: CreateListRequest, current_user: str = Depends(get_current_user)):
    l_id = db.add_list(current_user, req.title)
    return {"id": l_id}

@app.get("/api/lists/{list_id}/items", response_model=List[ListItem])
def get_list_items(list_id: int, current_user: str = Depends(get_current_user)):
    items = db.get_list_items(list_id)
    return [ListItem(**i) for i in items]

@app.post("/api/lists/{list_id}/items")
def create_list_item(list_id: int, req: CreateItemRequest, current_user: str = Depends(get_current_user)):
    db.add_list_item(list_id, req.item_name)
    return {"status": "ok"}

@app.put("/api/list_items/{item_id}")
def toggle_item(item_id: int, req: ToggleItemRequest, current_user: str = Depends(get_current_user)):
    db.toggle_item_status(item_id, req.is_done)
    return {"status": "ok"}
