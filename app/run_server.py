
import uvicorn
import sys
import os
from pathlib import Path

from app.main import app

# Add the app directory to Python path
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    bundle_dir = Path(sys._MEIPASS)
    app_dir = bundle_dir / 'app'
else:
    # Running as normal Python script
    app_dir = Path(__file__).parent

sys.path.insert(0, str(app_dir))

if __name__ == "__main__":
    # Get the directory where the executable is located
    if getattr(sys, 'frozen', False):
        # Running as executable
        base_dir = Path(sys._MEIPASS)
    else:
        # Running as script
        base_dir = Path(__file__).parent

    print(f"Starting server...")
    print(f"Dashboard: http://localhost:8000")
    print(f"API docs: http://localhost:8000/docs")
    print("Press Ctrl+C to stop")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
