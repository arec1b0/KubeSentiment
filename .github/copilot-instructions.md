# Copilot Instructions for MLOps Sentiment Analysis Microservice

## Project Overview
- **Purpose:** Production-ready FastAPI microservice for real-time sentiment analysis using DistilBERT (Hugging Face), containerized with Docker.
- **Key Components:**
  - `app/main.py`: FastAPI app factory, middleware, and entrypoint
  - `app/api.py`: All API endpoints (`/predict`, `/health`, `/metrics`), Pydantic schemas
  - `app/ml/sentiment.py`: Model loading, inference, and error handling
  - `app/config.py`: Centralized config via Pydantic, supports env vars (prefix `MLOPS_`)
- **API Endpoints:** `/predict`, `/health`, `/metrics` (see `README.md` for details)

## Architecture & Patterns
- **Service Structure:** Modular FastAPI app with clear separation:
  - API logic (`api.py`) imports model logic (`ml/sentiment.py`) and config (`config.py`)
  - Model is loaded at startup and cached for all requests
  - All endpoints use dependency injection for config and model
- **Error Handling:**
  - Global exception handler in `main.py` returns JSON with error_id
  - Model loading failures degrade gracefully (mock responses, clear status)
- **Monitoring:**
  - `/metrics` endpoint exposes system and model metrics (PyTorch, CUDA, memory)
  - All responses include `X-Process-Time-MS` header (middleware in `main.py`)
- **Configuration:**
  - All settings can be overridden via env vars (see `app/config.py`)
  - Example: `MLOPS_MODEL_NAME`, `MLOPS_DEBUG`, etc.

## Developer Workflows
- **Local Dev:**
  - Install: `pip install -r requirements.txt`
  - Run: `uvicorn app.main:app --reload`
- **Docker:**
  - Build: `docker build -t sentiment-service:0.1 .`
  - Run: `docker run -d -p 8000:8000 sentiment-service:0.1`
- **Testing:**
  - (If present) Run `pytest` or see `test_service.py` for test entrypoints
- **Debugging:**
  - Enable debug logs: set `MLOPS_DEBUG=true` or `MLOPS_LOG_LEVEL=DEBUG`
  - Logs output to stdout (see `logging` config in `main.py`)

## Project-Specific Conventions
- **API versioning:**
  - In production, endpoints are prefixed with `/api/v1` (see `main.py`)
  - In debug mode, endpoints are at root (`/predict`, etc.)
- **Input validation:**
  - All input via Pydantic models; empty/whitespace text is rejected
- **Model management:**
  - Model is loaded once at startup; failures do not crash the service
  - Model cache dir can be set via config

## Integration & Extensibility
- **Model:** Uses Hugging Face `transformers` pipeline; model name/configurable
- **Metrics:** Uses PyTorch for system info; works with/without CUDA
- **Extending:** Add new endpoints to `api.py`, new models to `ml/`

## References
- See `README.md` for API usage, deployment, and troubleshooting
- See `app/config.py` for all configurable settings
- Example API usage and responses are in `README.md`

---
For AI agents: Follow these conventions and reference the above files for implementation details. When adding features, maintain modularity and update config and error handling as shown.
