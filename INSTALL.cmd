@echo off
setlocal
set "ROOT=%~dp0"
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py -3 "%ROOT%install.py" %*
  exit /b %ERRORLEVEL%
)
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  python "%ROOT%install.py" %*
  exit /b %ERRORLEVEL%
)
echo ERROR: Python 3.11 or later is required. 1>&2
exit /b 2
