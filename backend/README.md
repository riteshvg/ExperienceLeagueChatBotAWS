# FastAPI Backend

Backend API for Adobe Experience League Chatbot, migrated from Streamlit.

## Setup

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Environment Variables

Copy `.env` from project root (already configured).

### 3. Run Development Server

```bash
uvicorn app.main:app --reload --port 8000
```

### 4. Run Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit

# With coverage
pytest --cov=app --cov-report=html
```

## API Documentation

Once the server is running:
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## Project Structure

```
backend/
├── app/
│   ├── api/v1/          # API endpoints
│   ├── core/            # Configuration and dependencies
│   ├── models/           # Pydantic schemas
│   ├── services/         # Business logic
│   └── main.py           # FastAPI app
└── tests/
    ├── unit/             # Unit tests
    └── integration/      # Integration tests
```

## Development

### Code Quality

```bash
# Format code
black app tests

# Lint
flake8 app tests

# Type check
mypy app
```

