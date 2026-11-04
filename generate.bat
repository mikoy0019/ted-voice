@echo off
REM Offline narration. Usage:
REM   generate.bat --voice voice_1 --input script.txt --output narration.mp3
REM   generate.bat --voice voice_2 --text "Here are five amazing facts." --output reel.mp3
REM Prints the absolute output path on success. Relative paths are relative to the current folder.
setlocal
set "OV_HOME=%~dp0"
set "VPY=%OV_HOME%.venv\Scripts\python.exe"
if not exist "%VPY%" (
  echo ERROR: OfflineVoice is not installed. Run "%OV_HOME%setup.bat" first. 1>&2
  exit /b 3
)
"%VPY%" "%OV_HOME%scripts\generate_voice.py" %*
exit /b %errorlevel%
