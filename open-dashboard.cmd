@echo off
setlocal
pushd "%~dp0"
if errorlevel 1 exit /b 1
python -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>nul
if not errorlevel 1 (
    python "skills\houdini-production-workflows\scripts\experience_cli.py" dashboard --open
    goto :done
)
py -3 -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>nul
if not errorlevel 1 (
    py -3 "skills\houdini-production-workflows\scripts\experience_cli.py" dashboard --open
    goto :done
)
uv --version >nul 2>nul
if not errorlevel 1 (
    uv run python "skills\houdini-production-workflows\scripts\experience_cli.py" dashboard --open
    goto :done
)
echo Python 3.10+ is required to build the dashboard. Install Python or uv and try again.
popd
pause
exit /b 1

:done
set "dashboard_exit=%errorlevel%"
popd
if not "%dashboard_exit%"=="0" (
    echo Dashboard generation failed. Review the error above.
    pause
)
exit /b %dashboard_exit%
