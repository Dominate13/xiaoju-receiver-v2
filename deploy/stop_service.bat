@echo off
chcp 65001 >nul
title 停止服务

echo.
echo ==============================================
echo     小桔充电数据集成服务 - 停止脚本
echo ==============================================
echo.

echo 正在查找并停止服务...
netstat -ano | findstr ":8100" >nul
if %errorlevel% equ 0 (
    echo 找到占用端口 8100 的进程，正在终止...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8100"') do (
        echo 终止进程 PID: %%a
        taskkill /f /pid %%a
    )
    echo.
    echo ✓ 服务已停止
) else (
    echo 没有找到运行中的服务
)

echo.
pause