@echo off
REM One-command start for Windows: serves everything on http://localhost:8000
cd /d "%~dp0"
if not exist .venv (
  python -m venv .venv
  .venv\Scripts\pip install -r backend\requirements.txt
  .venv\Scripts\python -m playwright install chromium
)
if not exist frontend\dist (
  pushd frontend
  call npm install
  call npm run build
  popd
)
cd backend
..\.venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000
