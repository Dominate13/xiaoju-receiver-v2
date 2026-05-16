@echo off
chcp 65001 >nul
title 小桔充电数据集成服务

echo.
echo ==============================================
echo     小桔充电数据集成服务 - 启动脚本
echo ==============================================
echo.

cd /d "%~dp0.."

echo 1. 检查端口 8100 是否被占用...
netstat -ano | findstr ":8100" >nul
if %errorlevel% equ 0 (
    echo 警告: 端口 8100 已被占用，尝试释放...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8100"') do (
        taskkill /f /pid %%a >nul 2>&1
    )
    timeout /t 1 /nobreak >nul
)

echo.
echo 2. 启动服务...
call venv\Scripts\activate.bat
python -m uvicorn app.main:app --host 0.0.0.0 --port 8100 --reload

echo.
echo 服务已停止
pause