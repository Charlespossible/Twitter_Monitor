from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class Mention(BaseModel):
    id: int
    tweet_id: str
    handle: str
    author: str
    text: str
    timestamp: datetime
    url: str
    notified: bool

class HandleStatus(BaseModel):
    handle: str
    last_checked: Optional[datetime]
    mention_count: int

class SystemStatus(BaseModel):
    status: str
    last_check: Optional[datetime]
    handles: List[HandleStatus]
    total_mentions: int

class NotificationRequest(BaseModel):
    message: str = Field(..., description="Message to send")
    use_telegram: bool = Field(True, description="Send via Telegram")
    use_email: bool = Field(True, description="Send via email")

class ReportRequest(BaseModel):
    start_date: Optional[datetime] = Field(None, description="Start date for report (defaults to 7 days ago)")
    end_date: Optional[datetime] = Field(None, description="End date for report (defaults to now)")