# The-Curator

Basic Python serverless API scaffold for Google Cloud Run.

## Tech Stack

- Python 3.12
- FastAPI (HTTP API)
- Gunicorn + Uvicorn worker (production process)
- Hatch (`pyproject.toml`) for environment and task management
- Ruff, MyPy, Pytest for quality checks

## Project Structure

```text
.
├── Dockerfile
├── pyproject.toml
├── src/
│   └── the_curator/
│       ├── __init__.py
│       └── main.py
└── tests/
	 └── test_health.py
```

## Local Development

1. Install Hatch:

	```bash
	pipx install hatch
	```

2. Run the API locally:

	```bash
	hatch run start
	```

3. Run checks:

	```bash
	hatch run check
	```

## Run with Docker

```bash
docker build -t the-curator .
docker run --rm -p 8080:8080 the-curator
```

## Deploy to Cloud Run

```bash
gcloud run deploy the-curator \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated
```

Health endpoint: `/healthz`
