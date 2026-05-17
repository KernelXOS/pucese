@echo off
setlocal enabledelayedexpansion

echo.
echo ========================================
echo EVALUACION DOCENTE IA - LOCAL START
echo ========================================
echo.

cd /d "C:\Users\grego\Desktop\TI\TI-  PROYECTOS\EVALUACION DOCENTE\evaluacion-docente-ia"

echo [0] Checking out latest branch (claude)...
git fetch --all
git checkout claude
git pull origin claude

echo.
echo [1] Installing dependencies...
cd backend
pip install -q -r requirements.txt
cd ..\frontend
call npm install --silent
cd ..

echo.
echo [2] Building frontend...
cd frontend
call npm run build
cd ..

echo.
echo [3] Starting Backend (FastAPI on port 8000)...
start "Backend - FastAPI" cmd /k "cd backend && python main.py"

timeout /t 5 /nobreak

echo [4] Starting Frontend (React/Vite on port 5173)...
start "Frontend - Vite" cmd /k "cd frontend && npm run preview"

echo.
echo ========================================
echo Services starting...
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo API Docs: http://localhost:8000/docs
echo ========================================
echo.

timeout /t 10
