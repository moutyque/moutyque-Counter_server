# Run

~~~shell
# Install dependencies
poetry install

# Run the application
poetry run python run.py

# Or use uvicorn directly
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

~~~
