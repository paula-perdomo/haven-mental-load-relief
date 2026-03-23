import os
import base64
import httpx
from app.database import get_config, add_activity, add_prep_item

def process_user_input(user_text: str, file_path: str = None) -> str:
    # Get the JWT token from config
    token = get_config("JWT_TOKEN")
    if not token:
        return "Please connect to the server in the Settings tab first."
    
    server_url = get_config("SERVER_URL")
    if not server_url:
        # Default to local dev
        server_url = "http://localhost:8000"

    # Read image
    image_b64 = None
    mime = "image/jpeg"
    if file_path and os.path.exists(file_path):
        with open(file_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")
        if file_path.lower().endswith(".png"): 
            mime = "image/png"
        elif file_path.lower().endswith(".pdf"): 
            mime = "application/pdf"

    payload = {"text": user_text}
    if image_b64:
        payload["image_b64"] = image_b64
        payload["mime_type"] = mime
        
    try:
        response = httpx.post(
            f"{server_url}/api/chat",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0
        )
        if response.status_code == 401:
            return "Authentication failed. Please check your credentials in Settings."
        response.raise_for_status()
        
        data = response.json()
        reply_text = data.get("reply", "No text response.")
        activities = data.get("activities", [])
        
        # Save activities to Local DB
        for act in activities:
            act_id = add_activity(
                title=act["title"],
                day_of_week=act["day_of_week"],
                time_str=act["time_str"]
            )
            for item in act.get("packing_list", []):
                add_prep_item(act_id, item)
                
        if activities:
            return f"Added {len(activities)} activities to your schedule.\n\n{reply_text}"
        return reply_text

    except Exception as e:
        return f"Error contacting Haven server: {str(e)}"
