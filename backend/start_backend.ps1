# 智慧大屏后端服务启动脚本
Write-Host "正在启动后端服务..." -ForegroundColor Green
Set-Location -Path "D:\demo\完整版订单管理系统\backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
