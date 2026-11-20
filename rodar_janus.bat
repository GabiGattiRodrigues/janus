@echo off
cd /d "%~dp0"
echo Instalando dependencias (so demora na primeira vez)...
python -m pip install -r requirements.txt --quiet
echo Abrindo o Janus no navegador (http://localhost:8501)...
start "" cmd /c "timeout /t 6 >nul & start http://localhost:8501"
python -m streamlit run app.py --server.headless true --server.port 8501
pause
