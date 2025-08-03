from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid

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

app = FastAPI(title="Event Receiver API", version="1.0.0")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/event", response_model=EventResponse)
async def receive_event(event: Event):
    try:
        # Process the event here
        print(f"Received event: {event}")

        # Return the event in the expected format
        return EventResponse(
            id=event.id,
            timestamp=event.timestamp.isoformat(),
            fighter_color=event.fighter_color.value
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing event: {str(e)}")
