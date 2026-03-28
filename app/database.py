import sqlite3
import httpx

DB_PATH = "haven.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS app_config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def set_config(key: str, value: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO app_config (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def get_config(key: str) -> str:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM app_config WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else ""

# --- API CLIENT LAYER ---
def _get_headers():
    token = get_config("JWT_TOKEN")
    return {"Authorization": f"Bearer {token}"} if token else {}

def _get_base_url():
    url = get_config("SERVER_URL")
    return url if url else "http://127.0.0.1:8000"

def get_members():
    try:
        r = httpx.get(f"{_get_base_url()}/api/members", headers=_get_headers())
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return []

def add_member(name: str, role: str):
    try:
        r = httpx.post(f"{_get_base_url()}/api/members", json={"name":name, "role":role}, headers=_get_headers())
        if r.status_code == 200:
            return r.json().get("id")
    except:
        pass
    return -1

def delete_member(member_id: int):
    try:
        httpx.delete(f"{_get_base_url()}/api/members/{member_id}", headers=_get_headers())
    except:
        pass

def update_member(member_id: int, name: str, role: str):
    try:
        httpx.put(f"{_get_base_url()}/api/members/{member_id}", json={"name":name, "role":role}, headers=_get_headers())
    except:
        pass

def get_activities():
    try:
        r = httpx.get(f"{_get_base_url()}/api/activities", headers=_get_headers())
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return []

def get_prep_items(activity_id: int):
    try:
        r = httpx.get(f"{_get_base_url()}/api/activities/{activity_id}/items", headers=_get_headers())
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return []

def add_list(title: str):
    try:
        r = httpx.post(f"{_get_base_url()}/api/lists", json={"title": title}, headers=_get_headers())
        if r.status_code == 200:
            return r.json().get("id")
    except:
        pass
    return -1

def get_lists():
    try:
        r = httpx.get(f"{_get_base_url()}/api/lists", headers=_get_headers())
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return []

def add_list_item(list_id: int, item_name: str):
    try:
        httpx.post(f"{_get_base_url()}/api/lists/{list_id}/items", json={"item_name": item_name}, headers=_get_headers())
    except:
        pass

def get_list_items(list_id: int):
    try:
        r = httpx.get(f"{_get_base_url()}/api/lists/{list_id}/items", headers=_get_headers())
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return []

def toggle_item_status(item_id: int, is_done: bool):
    try:
        httpx.put(f"{_get_base_url()}/api/list_items/{item_id}", json={"is_done": is_done}, headers=_get_headers())
    except:
        pass
