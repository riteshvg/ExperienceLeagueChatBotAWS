# Railway Deployment - FastAPI Configuration

## Critical Configuration Files

### 1. `nixpacks.toml`
- **Purpose**: Explicitly tells Railway/Nixpacks to use FastAPI, not Streamlit
- **Key**: `[start] cmd = "./start.sh"` - This prevents Streamlit auto-detection

### 2. `start.sh`
- **Purpose**: Starts FastAPI backend with uvicorn
- **Location**: Root directory
- **Command**: `./start.sh` (executable)

### 3. `backend/requirements.txt`
- **Purpose**: Backend dependencies (NO Streamlit)
- **Used by**: Railway build process
- **Note**: Root `requirements-railway.txt` is NOT used

### 4. `.railwayignore`
- **Purpose**: Prevents Railway from detecting Streamlit files
- **Excludes**: `app_streamlit.py`, root requirements files

## How Railway Detects Applications

Railway/Nixpacks uses the following detection order:
1. **Explicit start command** (in `nixpacks.toml` or `railway.toml`) - **HIGHEST PRIORITY**
2. **Procfile** - If present
3. **Auto-detection** - Looks for `app.py`, `requirements.txt` with `streamlit`

## Our Configuration

✅ **We use explicit start command** (`./start.sh`)
✅ **No `app.py`** (renamed to `app_streamlit.py`)
✅ **No streamlit in `backend/requirements.txt`**
✅ **Procfile points to `./start.sh`**

## Forcing a Rebuild

1. **Automatic**: Push to GitHub (Railway auto-deploys)
2. **Manual**: 
   - Go to Railway dashboard
   - Click "Redeploy" on your service
   - Or use Railway CLI: `railway redeploy`

## Verification

After deployment, check:
- ✅ Health endpoint: `https://your-domain.railway.app/api/v1/health`
- ✅ API docs: `https://your-domain.railway.app/api/docs`
- ✅ Frontend: `https://your-domain.railway.app/` (should show React app, not Streamlit)

## Troubleshooting

If Streamlit still appears:
1. Check Railway logs for what command is being executed
2. Verify `start.sh` is executable: `chmod +x start.sh`
3. Check that `nixpacks.toml` has `[start] cmd = "./start.sh"`
4. Verify `app.py` is renamed to `app_streamlit.py`
5. Check that `backend/requirements.txt` doesn't have streamlit

