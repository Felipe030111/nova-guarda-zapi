@echo off
cd /d "C:\Users\felip\OneDrive - 77 Consultoria e Indicadores\Todas\Documentos\PROJETOS\nova-guarda-zapi"
set LOCAL_ONLY=1
set PUBLIC_BASE_URL=http://127.0.0.1:3000
".\.venv\Scripts\python.exe" app.py
pause
