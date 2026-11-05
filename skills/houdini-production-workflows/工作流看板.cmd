@echo off
setlocal
for %%I in ("%~dp0.") do set "dashboard_root=%%~fI"

:find_root
if exist "%dashboard_root%\open-dashboard.cmd" if exist "%dashboard_root%\skills\houdini-production-workflows\scripts\experience_cli.py" goto :open_dashboard
for %%I in ("%dashboard_root%\..") do set "dashboard_parent=%%~fI"
if /i "%dashboard_root%"=="%dashboard_parent%" goto :not_found
set "dashboard_root=%dashboard_parent%"
goto :find_root

:open_dashboard
call "%dashboard_root%\open-dashboard.cmd"
exit /b %errorlevel%

:not_found
echo Cannot find houdini-mcp. Keep this launcher inside the houdini-mcp project folder.
pause
exit /b 1
