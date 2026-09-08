@echo off
REM Télécharge le dataset de balle Roboflow dans backend\datasets\ball\
REM Usage : double-cliquer, ou lancer depuis un terminal

REM --- A REMPLIR ---
set ROBOFLOW_API_KEY=ILek6ZgNMUQIqbcqRQF6
set ROBOFLOW_DATASET=swiftxponse/table-tennis-ball-detection-lehe0
set ROBOFLOW_VERSION=2
REM ----------------

cd /d "%~dp0"

backend\venv\Scripts\python.exe -m pip install roboflow -q
backend\venv\Scripts\python.exe backend\tools\export_ball_model.py --download-roboflow "%ROBOFLOW_DATASET%" --version %ROBOFLOW_VERSION%

pause
