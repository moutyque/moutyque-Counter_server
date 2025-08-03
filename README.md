# Run

~~~shell
# Install dependencies
poetry install

# Run the application
poetry run python run.py

# Or use uvicorn directly
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

~~~

~~~shell
curl -X POST "http://localhost:8000/event" \
  -H "Content-Type: application/json" \
  -d '{
    "fighterColor": "RED",
    "score": 5,
    "sendBy": "referee1"
  }'
~~~

~~~shell
curl -X POST "http://localhost:8000/event" \
  -H "Content-Type: application/json" \
  -d '{
    "fighterColor": "BLUE",
    "score": 3,
    "sendBy": "judge2"
  }'
~~~

~~~shell
curl -X POST "http://localhost:8000/event" \
  -H "Content-Type: application/json" \
  -d '{
    "fighterColor": "RED",
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "timestamp": "2024-01-15T10:30:00",
    "score": 10,
    "sendBy": "system"
  }'
~~~
