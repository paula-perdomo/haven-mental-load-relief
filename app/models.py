from pydantic import BaseModel
from typing import List, Optional

class FamilyMember(BaseModel):
    id: Optional[int] = None
    name: str
    role: str # e.g. "Parent", "Child"

class PrepItem(BaseModel):
    id: Optional[int] = None
    activity_id: Optional[int] = None
    item_name: str
    is_packed: bool = False

class Activity(BaseModel):
    id: Optional[int] = None
    title: str
    assigned_member_id: Optional[int] = None
    day_of_week: str # e.g. "Wednesday"
    time_str: str # e.g. "19:30"
    prep_items: List[PrepItem] = []
