from fastapi import Depends
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from kaptive_web.models.database import get_db, User
from typing import Optional

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def get_current_user(api_key: Optional[str] = Depends(api_key_header), db: Session = Depends(get_db)) -> Optional[User]:
    if not api_key:
        return None
    user = db.query(User).filter(User.api_key == api_key).first()
    return user
