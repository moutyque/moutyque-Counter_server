from fastapi import FastAPI, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi import Request
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid
from collections import defaultdict

# Enum for fighter color
class FighterColor(str, Enum):
    RED = "RED"
    BLUE = "BLUE"

# Event model matching your Kotlin data class
class Event(BaseModel):
    fighter_color: FighterColor = Field(..., alias="fighterColor")
    id: Optional[str] = None
    timestamp: Optional[datetime] = None
    score: int = 1
    send_by: Optional[str] = Field(None, alias="sendBy")

    class Config:
        allow_population_by_field_name = True

    def model_post_init(self, __context) -> None:
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.now()

# Response model for the event
class EventResponse(BaseModel):
    id: str
    timestamp: str
    fighter_color: str

# Stats response model
class StatsResponse(BaseModel):
    red_count: int
    blue_count: int
    total_count: int

app = FastAPI(title="Event Receiver API", version="1.0.0")
templates = Jinja2Templates(directory="app/templates")

# In-memory storage for event counts (in production, use a database)
event_counts = defaultdict(int)

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    return StatsResponse(
        red_count=event_counts[FighterColor.RED],
        blue_count=event_counts[FighterColor.BLUE],
        total_count=sum(event_counts.values())
    )

@app.post("/event", response_model=EventResponse)
async def receive_event(event: Event):
    try:
        # Increment the counter for this fighter color
        event_counts[event.fighter_color] += 1

        # Process the event here
        print(f"Received event: {event} (Total {event.fighter_color.value}: {event_counts[event.fighter_color]})")

        # Return the event in the expected format
        return EventResponse(
            id=event.id,
            timestamp=event.timestamp.isoformat(),
            fighter_color=event.fighter_color.value
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing event: {str(e)}")
