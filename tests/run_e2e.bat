@echo off
setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..

set PYTHON=python
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH
    exit /b 1
)

%PYTHON% -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo Installing requests...
    %PYTHON% -m pip install requests --quiet
)

echo ============================================
echo  PHM System E2E Test Launcher (Windows)
echo ============================================
echo  Project : %PROJECT_ROOT%
echo  Python  : %PYTHON%
echo  Args    : %*
echo ============================================
echo.

cd /d "%PROJECT_ROOT%"
%PYTHON% "%SCRIPT_DIR%e2e_test.py" %*

exit /b %errorlevel%
