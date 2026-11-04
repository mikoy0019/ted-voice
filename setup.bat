@echo off
REM OfflineVoice one-time setup: venv, PyTorch, Kokoro, model download, voice build, validation.
REM Needs internet ONLY while this script runs. Narration afterwards is fully offline.
setlocal EnableExtensions
set "OV_HOME=%~dp0"
if "%OV_HOME:~-1%"=="\" set "OV_HOME=%OV_HOME:~0,-1%"
cd /d "%OV_HOME%"

echo === OfflineVoice setup in "%OV_HOME%" ===

REM ---- 1. Find Python 3.10-3.12 (Kokoro supports these) ----
set "PY="
for %%V in (3.11 3.12 3.10) do if not defined PY py -%%V -c "import sys" >nul 2>&1 && set "PY=py -%%V"
if not defined PY python -c "import sys; sys.exit(0 if (3,10)<=sys.version_info[:2]<=(3,12) else 1)" >nul 2>&1 && set "PY=python"
if not defined PY (
  echo ERROR: Python 3.10, 3.11 or 3.12 is required. Install from https://www.python.org/downloads/
  exit /b 1
)
echo [1/7] Using %PY%

REM ---- 2. Virtual environment ----
if not exist ".venv\Scripts\python.exe" (
  %PY% -m venv .venv
  if errorlevel 1 ( echo ERROR: could not create .venv & exit /b 1 )
)
set "VPY=%OV_HOME%\.venv\Scripts\python.exe"
"%VPY%" -m pip install --upgrade pip >nul
echo [2/7] Virtual environment ready

REM ---- 3. PyTorch: CUDA build when an NVIDIA GPU is present, otherwise CPU build ----
set "TORCH_INDEX=https://download.pytorch.org/whl/cpu"
nvidia-smi >nul 2>&1
if not errorlevel 1 set "TORCH_INDEX=https://download.pytorch.org/whl/cu126"
"%VPY%" -c "import torch" >nul 2>&1
if errorlevel 1 (
  echo [3/7] Installing PyTorch from %TORCH_INDEX% ^(large download^)
  "%VPY%" -m pip install torch --index-url %TORCH_INDEX%
  if errorlevel 1 ( echo ERROR: PyTorch install failed & exit /b 1 )
) else (
  echo [3/7] PyTorch already installed
)

REM ---- 4. Python dependencies ----
echo [4/7] Installing dependencies
"%VPY%" -m pip install -r "%OV_HOME%\requirements.txt"
if errorlevel 1 ( echo ERROR: dependency install failed & exit /b 1 )

REM ---- 5. Download model checkpoints + English text model ----
echo [5/7] Downloading Kokoro-82M and English voicepacks
"%VPY%" "%OV_HOME%\scripts\download_models.py"
if errorlevel 1 ( echo ERROR: model download failed & exit /b 1 )

REM ---- 6. Build the two voices and check the machine ----
echo [6/7] Building voice_1 and voice_2
"%VPY%" "%OV_HOME%\scripts\configure_voice.py" --build
if errorlevel 1 ( echo ERROR: voice build failed & exit /b 1 )
"%VPY%" "%OV_HOME%\scripts\hardware_check.py" --save

REM ---- 7. Validate both voices offline and register OFFLINE_VOICE_HOME ----
echo [7/7] Validating both voices offline
"%VPY%" "%OV_HOME%\scripts\validate_voice.py"
set "VALID=%errorlevel%"
setx OFFLINE_VOICE_HOME "%OV_HOME%" >nul
echo.
echo OFFLINE_VOICE_HOME set to "%OV_HOME%" (open a new terminal to pick it up)
if not "%VALID%"=="0" ( echo Setup finished WITH VALIDATION ERRORS - see above. & exit /b 1 )
echo Setup complete. Try:  generate.bat --voice voice_1 --text "Hello from my offline voice." --output hello.mp3
exit /b 0
