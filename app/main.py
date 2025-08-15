import json
import logging
import platform
import socket
import subprocess
import time
from typing import Optional, Dict, Set, List

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum
import uuid
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)



app = FastAPI(title="Event Receiver API", version="1.0.0",debug=True)
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
registered_sources: Dict[str, Set[str]] = defaultdict(set)  # color -> set of IPs
# Global state
response_time_ms = 1000  # Default 1 second
pending_events: Dict[str, List[tuple]] = defaultdict(list)  # color -> [(ip, timestamp, event)]

class Event(BaseModel):
    color: FighterColor = Field(..., alias="color")
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
    color: str

class HealthResponse(BaseModel):
    status: str
    timestamp: str

class StatsResponse(BaseModel):
    red_count: int
    blue_count: int
    total_count: int
    system_state: str
    registered_data: Dict


class StateResponse(BaseModel):
    system_state: str
    message: str

network_info = None  # Will be set on startup
def get_private_ip():
    """Get the private IP address of the current machine"""
    try:
        # Method 1: Connect to a remote address to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # Connect to Google DNS - doesn't actually send data
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            print(f"Local addr {ip}")
            return ip
    except Exception:
        try:
            # Method 2: Get hostname and resolve it
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            if ip.startswith("127."):
                raise Exception("Got localhost")
            return ip
        except Exception:
            try:
                # Method 3: Platform-specific commands
                if platform.system() == "Darwin":  # macOS
                    result = subprocess.run(
                        ["ifconfig", "en0"],
                        capture_output=True,
                        text=True
                    )
                    for line in result.stdout.split('\n'):
                        if 'inet ' in line and 'broadcast' in line:
                            return line.split()[1]
                elif platform.system() == "Linux":
                    result = subprocess.run(
                        ["hostname", "-I"],
                        capture_output=True,
                        text=True
                    )
                    return result.stdout.strip().split()[0]
                elif platform.system() == "Windows":
                    result = subprocess.run(
                        ["ipconfig"],
                        capture_output=True,
                        text=True
                    )
                    lines = result.stdout.split('\n')
                    for i, line in enumerate(lines):
                        if 'IPv4 Address' in line or 'IP Address' in line:
                            return line.split(':')[-1].strip()
            except Exception:
                pass
            return "Unable to determine IP"

# Initialize network info once at startup
@app.on_event("startup")
async def startup_event():
    global network_info
    network_info = NetworkInfo(
        private_ip=get_private_ip(),
        hostname=socket.gethostname(),
        port=8000
    )
    print(f"🚀 Server starting up...")
    print(f"🌐 Private IP: {network_info.private_ip}")
    print(f"🏠 Hostname: {network_info.hostname}")
    print(f"🔗 Event endpoint: http://{network_info.private_ip}:8000/event")
    print(f"📊 Dashboard: http://{network_info.private_ip}:8000/")

class NetworkInfo(BaseModel):
    private_ip: str
    hostname: str
    port: int = 8000


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="healthy", timestamp=datetime.now().isoformat())

@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    global registered_sources
    # Convert registered_sources sets to lists for JSON serialization
    registered_data = {}
    for color, ips in registered_sources.items():
        registered_data[color] = list(ips)

    logger.info(f"Current registered sources: {dict(registered_data)}")
    return StatsResponse(
        red_count=event_counts[FighterColor.RED],
        blue_count=event_counts[FighterColor.BLUE],
        total_count=sum(event_counts.values()),
        system_state=system_state.value,
        registered_data=registered_data  # Add this line
    )

# Add middleware to log all requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url}")
    logger.info(f"Headers: {dict(request.headers)}")

    # Log request body for POST requests
    if request.method == "POST":
        body = await request.body()
        logger.info(f"Request body: {body}")
        # Need to replace the body for downstream processing
        from starlette.requests import Request as StarletteRequest
        import io
        request._body = body

    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response

class ResponseTimeConfig(BaseModel):
    response_time_ms: int

@app.post("/config/response-time")
async def set_response_time(config: ResponseTimeConfig):
    global response_time_ms
    if config.response_time_ms < 100:
        raise HTTPException(status_code=400, detail="Response time must be at least 100ms")

    response_time_ms = config.response_time_ms
    logger.info(f"Response time set to {response_time_ms}ms")
    return {"response_time_ms": response_time_ms, "message": "Response time updated"}

@app.get("/config/response-time")
async def get_response_time():
    return {"response_time_ms": response_time_ms}
@app.post("/event")
async def receive_event(request: Request):
    global system_state, registered_sources
    try:
        # Get client IP
        client_ip = request.client.host
        logger.info(f"Request from IP: {client_ip}")

        # Parse the event
        body = await request.body()
        json_data = json.loads(body)
        event = Event(**json_data)

        color = event.color.value  # Get string value of enum

        # If server not started, register the source
        if system_state == SystemState.STOPPED:
            registered_sources[color].add(client_ip)
            logger.info(f"🔒 Server not started. Registered {client_ip} for color {color}")
            logger.info(f"Current registered sources: {dict(registered_sources)}")
            return {"status": "registered", "message": f"Source {client_ip} registered for {color}"}

        # Server is started - check if source is registered
        if client_ip not in registered_sources[color]:
            logger.warning(f"❌ Unauthorized source {client_ip} for color {color}")
            raise HTTPException(
                status_code=403,
                detail=f"Source {client_ip} not registered for color {color}"
            )

        logger.info(f"✅ Authorized event from {client_ip}: {event}")

        # Increment the counter for this fighter color
        handle_event(event,client_ip)

        # Process the event here
        print(f"Received event: {event} (Total {event.color.value}: {event_counts[event.color]})")

        # Return the event in the expected format
        return EventResponse(
            id=event.id,
            timestamp=event.timestamp.isoformat(),
            color=event.color.value
        )
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        raise

def handle_event(event: Event, client_ip: str):
    global event_counts, registered_sources, pending_events, response_time_ms

    color = event.color.value
    current_time = time.time() * 1000  # Convert to milliseconds

    # Get all registered sources for this color
    required_sources = registered_sources.get(color, set())

    if not required_sources:
        logger.warning(f"No registered sources for color {color}")
        return False

    # Add this event to pending events
    pending_events[color].append((client_ip, current_time, event))
    logger.info(f"Added event from {client_ip} for {color}. Pending: {len(pending_events[color])}")

    # Clean up old pending events (outside response time window)
    cutoff_time = current_time - response_time_ms
    pending_events[color] = [
        (ip, timestamp, evt) for ip, timestamp, evt in pending_events[color]
        if timestamp > cutoff_time
    ]

    # Check if we have events from all required sources within the time window
    recent_sources = set()
    for ip, timestamp, evt in pending_events[color]:
        if timestamp > cutoff_time:
            recent_sources.add(ip)

    logger.info(f"Recent sources for {color}: {recent_sources}")
    logger.info(f"Required sources for {color}: {required_sources}")

    # If all required sources have sent events within response time
    if required_sources.issubset(recent_sources):
        # Increment counter
        event_counts[event.color] += 1
        logger.info(f"🎉 All sources responded for {color}! Count incremented to {event_counts[event.color]}")

        # Clear pending events for this color (reset the window)
        pending_events[color].clear()
        return True
    else:
        missing_sources = required_sources - recent_sources
        logger.info(f"⏳ Waiting for sources {missing_sources} for {color} (Response window: {response_time_ms}ms)")
        return False


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

@app.get("/network-info", response_model=NetworkInfo)
async def get_network_info():
    return network_info
