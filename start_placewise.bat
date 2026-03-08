@echo off
echo Starting PlaceWise...

:: Terminal 1 - FastAPI Backend
start "FastAPI Backend" cmd /k "cd /d C:\Users\New\trail\placewise\backend && C:\Users\New\trail\venv\Scripts\activate.bat && uvicorn main:app --reload --port 8000"

:: Terminal 2 - Node AI Backend
start "Node AI Backend" cmd /k "cd /d C:\Users\New\trail\placewise\ai_placement\server && node server.js"

:: Terminal 3 - React Frontend
start "React Frontend" cmd /k "cd /d C:\Users\New\trail\placewise\frontend && npm run dev"

echo All 3 servers starting in separate windows...