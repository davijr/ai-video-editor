@echo off
setlocal

where py >nul 2>nul
if %errorlevel%==0 (
    py video_editor_gui.py
) else (
    python video_editor_gui.py
)

endlocal
