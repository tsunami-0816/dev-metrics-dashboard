@echo off
setlocal
cd /d "%~dp0"
echo ============================================
echo  dev-metrics-dashboard - collect run
echo  source : repo_root\projects\*
echo  target : data\metrics.db (idempotent rebuild)
echo ============================================
echo.
if not exist ".venv\Scripts\python.exe" goto noenv
".venv\Scripts\python.exe" collect.py
if errorlevel 1 goto fail
echo.
echo [OK] collect finished. Refresh the dashboard with F5.
echo      Sidebar "Data as of" time now equals this run.
pause
exit /b 0
:noenv
echo [FAIL] .venv not found. Create it:
echo        python -m venv .venv
echo        .venv\Scripts\pip install -r ..\..\requirements.txt
pause
exit /b 1
:fail
echo.
echo [FAIL] collect.py returned non-zero. See output above.
pause
exit /b 1
