# 🚀 How to Run the Application

## Prerequisites

1. **Python 3.11+** (already installed in venv)
2. **Node.js 18+** (check with `node --version`)
3. **AWS Credentials** configured in `.env` file
4. **Knowledge Base ID** set in `.env` file

## Quick Start

### Step 1: Start the Backend API

```bash
# Navigate to backend directory
cd backend

# Activate virtual environment
source ../venv/bin/activate

# Install backend dependencies (if not already installed)
pip install -r requirements.txt

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```

The backend will be available at:
- **API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/api/docs
- **API Docs (ReDoc)**: http://localhost:8000/api/redoc

### Step 2: Start the Frontend (in a new terminal)

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies (first time only)
npm install

# Start development server
npm run dev
```

The frontend will be available at:
- **React App**: http://localhost:3000

## Running Tests

### Backend Tests

```bash
cd backend
source ../venv/bin/activate

# Run all tests
pytest tests/unit/ -v

# Run specific test file
pytest tests/unit/test_health.py -v

# Run with coverage
pytest tests/unit/ --cov=app --cov-report=html
```

### Frontend Tests

```bash
cd frontend

# Run tests
npm test

# Run tests with UI
npm run test:ui

# Run tests with coverage
npm run test:coverage
```

## Environment Setup

### Backend Environment

The backend uses the existing `.env` file in the project root. Make sure it contains:

```env
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_DEFAULT_REGION=us-east-1
BEDROCK_KNOWLEDGE_BASE_ID=your_kb_id
```

### Frontend Environment

Create `frontend/.env` file (optional, defaults to localhost:8000):

```env
VITE_API_URL=http://localhost:8000
```

## Troubleshooting

### Backend Issues

**Issue**: `ModuleNotFoundError` for app modules
```bash
# Make sure you're in the backend directory
cd backend
# And virtual environment is activated
source ../venv/bin/activate
```

**Issue**: AWS connection errors
```bash
# Verify AWS credentials
python -c "import boto3; print(boto3.client('sts').get_caller_identity())"
```

**Issue**: Port 8000 already in use
```bash
# Use a different port
uvicorn app.main:app --reload --port 8001
# Then update frontend/.env with new port
```

### Frontend Issues

**Issue**: `npm: command not found`
```bash
# Install Node.js from https://nodejs.org/
# Or use nvm: nvm install 18
```

**Issue**: Dependencies not installing
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

**Issue**: API connection errors
```bash
# Check backend is running on port 8000
curl http://localhost:8000/api/v1/health

# Check CORS settings in backend/app/main.py
```

## Development Workflow

1. **Start Backend** (Terminal 1)
   ```bash
   cd backend && source ../venv/bin/activate && uvicorn app.main:app --reload
   ```

2. **Start Frontend** (Terminal 2)
   ```bash
   cd frontend && npm run dev
   ```

3. **Make Changes**
   - Backend: Changes auto-reload with `--reload` flag
   - Frontend: Changes hot-reload automatically

4. **Test Changes**
   - Backend: Run `pytest tests/unit/ -v`
   - Frontend: Run `npm test`

## Production Build

### Backend

```bash
cd backend
source ../venv/bin/activate
pip install -r requirements.txt

# Run with production server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm run build

# Built files in dist/
# Serve with any static file server
# Example: npx serve dist
```

## API Endpoints

Once backend is running, test these endpoints:

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Config status
curl http://localhost:8000/api/v1/config/status

# Send chat message
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Adobe Analytics?", "user_id": "test"}'

# Validate query
curl -X POST http://localhost:8000/api/v1/chat/validate \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Adobe Analytics?"}'
```

## Access Points

- **Frontend UI**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/api/docs
- **ReDoc Documentation**: http://localhost:8000/api/redoc

## Next Steps

1. Open http://localhost:3000 in your browser
2. Try asking a question about Adobe Analytics
3. Check the API docs at http://localhost:8000/api/docs
4. Review test results to ensure everything works

