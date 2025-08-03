from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum
import uuid
from collections import defaultdict

app = FastAPI(title="Event Receiver API", version="1.0.0")
templates = Jinja2Templates(directory="app/templates")

class FighterColor(str, Enum):
    RED = "RED"
    BLUE = "BLUE"

class SystemState(str, Enum):
    STOPPED = "stopped"
    STARTED = "started"

# Global state
event_counts = defaultdict(int)
system_state = SystemState.STOPPED

class Event(BaseModel):
    fighter_color: FighterColor = Field(..., alias="fighterColor")
    id: Optional[str] = Field(default=None)
    timestamp: Optional[datetime] = Field(default=None)
    score: int = Field(default=0)
    send_by: str = Field(default="", alias="sendBy")

    def __init__(self, **data):
        super().__init__(**data)
        # Set defaults after initialization
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now()

class EventResponse(BaseModel):
    id: str
    timestamp: str
    fighter_color: str

class HealthResponse(BaseModel):
    status: str
    timestamp: str

class StatsResponse(BaseModel):
    red_count: int
    blue_count: int
    total_count: int
    system_state: str

class StateResponse(BaseModel):
    system_state: str
    message: str

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="healthy", timestamp=datetime.now().isoformat())

@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    return StatsResponse(
        red_count=event_counts[FighterColor.RED],
        blue_count=event_counts[FighterColor.BLUE],
        total_count=sum(event_counts.values()),
        system_state=system_state.value
    )

@app.post("/event", response_model=EventResponse)
async def receive_event(event: Event):
    try:
        # Only count events if system is started
        if system_state == SystemState.STOPPED:
            raise HTTPException(
                status_code=400,
                detail="System is stopped. Events are not being counted. Please start the system first."
            )

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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing event: {str(e)}")

@app.post("/start", response_model=StateResponse)
async def start_system():
    global system_state
    if system_state == SystemState.STARTED:
        return StateResponse(
            system_state=system_state.value,
            message="System is already started"
        )

    system_state = SystemState.STARTED
    print("System started - Events will now be counted")
    return StateResponse(
        system_state=system_state.value,
        message="System started successfully"
    )

@app.post("/stop", response_model=StateResponse)
async def stop_system():
    global system_state
    if system_state == SystemState.STOPPED:
        return StateResponse(
            system_state=system_state.value,
            message="System is already stopped"
        )

    system_state = SystemState.STOPPED
    print("System stopped - Events will not be counted")
    return StateResponse(
        system_state=system_state.value,
        message="System stopped successfully"
    )

@app.post("/reset", response_model=StateResponse)
async def reset_system():
    global event_counts

    if system_state != SystemState.STOPPED:
        raise HTTPException(
            status_code=400,
            detail="Cannot reset while system is running. Please stop the system first."
        )

    event_counts.clear()
    print("Event counters reset")
    return StateResponse(
        system_state=system_state.value,
        message="Event counters reset successfully"
    )
