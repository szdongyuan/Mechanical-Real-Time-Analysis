@echo off
setlocal
cd /d "%~dp0"

echo [1/3] Installing dependencies...
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 exit /b 1

echo [2/3] Building with PyInstaller...
python -m PyInstaller --noconfirm --clean MechanicalRealTimeAnalysis.spec
if errorlevel 1 exit /b 1

echo [3/3] Preparing distribution folder...
set "OUT=dist\MechanicalRealTimeAnalysis"
rem PyInstaller 6 puts datas under _internal; the app reads paths beside the exe
if exist "%OUT%\_internal\ui\ui_pic" xcopy /E /I /Y "%OUT%\_internal\ui\ui_pic" "%OUT%\ui\ui_pic\" >nul
if exist "%OUT%\_internal\ui\ui_config" xcopy /E /I /Y "%OUT%\_internal\ui\ui_config" "%OUT%\ui\ui_config\" >nul
if exist "%OUT%\_internal\configs" xcopy /E /I /Y "%OUT%\_internal\configs" "%OUT%\configs\" >nul
if not exist "%OUT%\ui" mkdir "%OUT%\ui"
if exist "%OUT%\_internal\ui\R87-Y160M.stp" copy /Y "%OUT%\_internal\ui\R87-Y160M.stp" "%OUT%\ui\" >nul
if not exist "%OUT%\log" mkdir "%OUT%\log"
if not exist "%OUT%\database" mkdir "%OUT%\database"
if not exist "%OUT%\wav" mkdir "%OUT%\wav"
if not exist "%OUT%\audio_data\stored_sample" mkdir "%OUT%\audio_data\stored_sample"
if not exist "%OUT%\audio_data\stored_data\OK" mkdir "%OUT%\audio_data\stored_data\OK"
if not exist "%OUT%\audio_data\stored_data\NG" mkdir "%OUT%\audio_data\stored_data\NG"
if not exist "%OUT%\audio_data\stimulus" mkdir "%OUT%\audio_data\stimulus"
if not exist "%OUT%\reports" mkdir "%OUT%\reports"

echo.
echo Build complete: %OUT%\MechanicalRealTimeAnalysis.exe
endlocal
