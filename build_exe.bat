@echo off
setlocal

echo [1/3] Instalando/atualizando PyInstaller...
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 -m pip install --upgrade pyinstaller
    if errorlevel 1 goto :error

    echo [2/3] Gerando executavel...
    py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name AIVideoEditor --distpath dist --workpath build video_editor_gui.py
    if errorlevel 1 goto :error
) else (
    python -m pip install --upgrade pyinstaller
    if errorlevel 1 goto :error

    echo [2/3] Gerando executavel...
    python -m PyInstaller --noconfirm --clean --onefile --windowed --name AIVideoEditor --distpath dist --workpath build video_editor_gui.py
    if errorlevel 1 goto :error
)

echo [3/3] Build finalizado.
echo Executavel: dist\AIVideoEditor.exe
exit /b 0

:error
echo Build falhou.
exit /b 1
