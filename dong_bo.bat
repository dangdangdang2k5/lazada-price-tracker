@echo off
chcp 65001 > nul
echo ========================================================
echo   ĐANG ĐỒNG BỘ SẢN PHẨM TỪ WEB LÊN GITHUB ACTIONS...
echo ========================================================
.\backend\venv\Scripts\python.exe scripts\sync_db_to_json.py
pause
