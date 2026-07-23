@echo off
cd /d D:\demo\完整版订单管理系统\backend
echo Starting backend server...
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
