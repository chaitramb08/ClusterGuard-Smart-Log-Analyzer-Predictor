@echo off
REM ============================================================
REM etl/run.bat
REM One-click automation for the Smart Log Analyzer pipeline:
REM   1. create/activate a virtual environment
REM   2. install dependencies
REM   3. run the ETL (extract/transform/load the dataset into SQLite)
REM   4. run Phase 2 analysis + chart generation
REM   5. train the Phase 3 model
REM   6. launch the FastAPI dashboard
REM
REM Run this from anywhere — it resolves the project root itself.
REM Usage:  etl\run.bat
REM ============================================================

setlocal
set "PROJECT_ROOT=%~dp0.."
cd /d "%PROJECT_ROOT%"

echo.
echo === [1/6] Checking virtual environment ===
if not exist ".venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv .venv
)
call .venv\Scripts\activate.bat

echo.
echo === [2/6] Installing dependencies ===
pip install -q -r requirements.txt

echo.
echo === [3/6] Running ETL ^(extract, transform, load^) ===
python etl\etl.py
if errorlevel 1 goto :error

echo.
echo === [4/6] Running Phase 2 analysis + charts ===
python data_analysis\analyze_logs.py
python data_analysis\visualize_logs.py
if errorlevel 1 goto :error

echo.
echo === [5/6] Training Phase 3 model ===
python model\train_model.py
if errorlevel 1 goto :error

echo.
echo === [6/6] Launching dashboard ===
echo Dashboard will be available at http://127.0.0.1:8000
echo Press Ctrl+C to stop the server.
python main.py

goto :eof

:error
echo.
echo Pipeline failed — see the error above.
exit /b 1
