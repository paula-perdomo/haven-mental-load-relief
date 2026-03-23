import sqlite3
import os

DB_PATH = "haven.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            assigned_member_id INTEGER,
            day_of_week TEXT NOT NULL,
            time_str TEXT NOT NULL,
            FOREIGN KEY(assigned_member_id) REFERENCES members(id)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS prep_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            is_packed INTEGER DEFAULT 0,
            FOREIGN KEY(activity_id) REFERENCES activities(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS app_config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS shared_lists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS list_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            list_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            is_done INTEGER DEFAULT 0,
            FOREIGN KEY(list_id) REFERENCES shared_lists(id)
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

def add_member(name: str, role: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO members (name, role) VALUES (?, ?)", (name, role))
    conn.commit()
    member_id = c.lastrowid
    conn.close()
    return member_id

def get_members():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, name, role FROM members")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "role": r[2]} for r in rows]

def add_activity(title: str, day_of_week: str, time_str: str, assigned_member_id: int = None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO activities (title, assigned_member_id, day_of_week, time_str) VALUES (?, ?, ?, ?)",
              (title, assigned_member_id, day_of_week, time_str))
    conn.commit()
    act_id = c.lastrowid
    conn.close()
    return act_id

def add_prep_item(activity_id: int, item_name: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO prep_items (activity_id, item_name) VALUES (?, ?)",
              (activity_id, item_name))
    conn.commit()
    conn.close()

def get_activities():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, title, assigned_member_id, day_of_week, time_str FROM activities ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "assigned_member_id": r[2], "day_of_week": r[3], "time_str": r[4]} for r in rows]

def get_prep_items(activity_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, item_name, is_packed FROM prep_items WHERE activity_id = ?", (activity_id,))
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "item_name": r[1], "is_packed": bool(r[2])} for r in rows]

def add_list(title: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO shared_lists (title) VALUES (?)", (title,))
    conn.commit()
    list_id = c.lastrowid
    conn.close()
    return list_id

def get_lists():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, title FROM shared_lists ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1]} for r in rows]

def add_list_item(list_id: int, item_name: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO list_items (list_id, item_name) VALUES (?, ?)", (list_id, item_name))
    conn.commit()
    conn.close()

def get_list_items(list_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, item_name, is_done FROM list_items WHERE list_id = ? ORDER BY item_name ASC", (list_id,))
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "item_name": r[1], "is_done": bool(r[2])} for r in rows]

def toggle_item_status(item_id: int, is_done: bool):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE list_items SET is_done = ? WHERE id = ?", (int(is_done), item_id))
    conn.commit()
    conn.close()

